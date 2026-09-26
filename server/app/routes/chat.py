import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.core.app_configs import getAppConfig
from app.core.logging import logger
from app.core.middleware import authenticate_user
from app.database.db import get_async_db_session, get_db
from app.langchain.chat_engine import ChatEngine
from app.langchain.llm import DEFAULT_MODEL, DEFAULT_RAG_STRATEGY
from app.models.chats import Message, MessageRole, MessageStatus
from app.store.MessageStore import MessageStore
from app.store.ThreadStore import ThreadStore
from app.types import (
    ChatRequest,
    TokenPayload,
)

CHAT_LIMIT = 20
router = APIRouter(prefix="/v2/chat", tags=["chat"])
AppConfig = getAppConfig()

active_tasks: dict[str, asyncio.Task] = {}


async def anonymous_chat_generator(
    history: list[dict], prompt: str, rag_strategy: str | None = None
) -> AsyncGenerator[str]:
    if history and len(history) >= CHAT_LIMIT:
        raise ValueError("Free credits limit reached.")

    lc_history = []
    if history:
        for entry in history:
            role = "user" if entry["role"] == "human" else "assistant"
            lc_history.append(ChatEngine.to_lc_message(role, entry["content"]))

    async for chunk in ChatEngine.stream(lc_history, prompt, rag_strategy=rag_strategy):
        yield f"data: {json.dumps(chunk)}\n\n"


# ---------------------------------------------------------------------------


async def generator(
    prompt: str,
    lc_history: list[HumanMessage | AIMessage],
    ai_msg: Message,
    async_db_session: async_sessionmaker[AsyncSession],
    thread_id: str,
    llm_model: str | None = None,
    rag_strategy: str | None = None,
) -> AsyncGenerator[str]:
    parts: list[str] = []
    status = MessageStatus.COMPLETE

    current_task = asyncio.current_task()
    if current_task and thread_id:
        active_tasks[thread_id] = current_task

    # Stream the response
    logger.info("Stream started thread_id=%s model=%s strategy=%s", thread_id, llm_model, rag_strategy)
    try:
        async for chunk in ChatEngine.stream(
            lc_history, prompt, thread_id, llm_model=llm_model, rag_strategy=rag_strategy
        ):
            if chunk["type"] == "ai":
                parts.append(chunk["content"])
            yield f"data: {json.dumps(chunk)}\n\n"

    except asyncio.CancelledError:
        status = MessageStatus.CANCELLED
        logger.info("Stream cancelled thread_id=%s", thread_id)
        raise
    except Exception:
        status = MessageStatus.FAILED
        logger.error("Stream failed thread_id=%s", thread_id, exc_info=True)
        raise

    finally:
        if current_task and active_tasks.get(thread_id) == current_task:
            active_tasks.pop(thread_id, None)

        full_response = "".join(parts)

        async with async_db_session() as db:
            try:
                ai_msg = await db.merge(ai_msg)

                MessageStore.update_message(
                    ai_msg,
                    status,
                    content=full_response,
                )
                await db.commit()
            except Exception:
                await db.rollback()
                logger.error("Failed to persist AI message msg_id=%s", ai_msg.id, exc_info=True)


# ------------------------------------------------------------------------------


@router.post("/anonymous")
async def free_chat(req: ChatRequest):
    history = [entry.model_dump() for entry in req.history] if req.history else []

    if history and len(history) >= 20:
        raise HTTPException(status_code=400, detail="Free credits limit reached.")

    return StreamingResponse(
        anonymous_chat_generator(history, req.prompt, rag_strategy=req.rag_strategy),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # NOTE do we need X-Thread-Id & X-Message-Id
        },
    )


# ------------------------------------------------------------------------------


@router.post("/{thread_id}", status_code=200)
async def chat_(
    req: ChatRequest,
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
    async_db_session: Annotated[async_sessionmaker[AsyncSession], Depends(get_async_db_session)],
):
    try:
        user_id = int(access_token.sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload.")

    thread = ThreadStore.get_for_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Build LC history from past DB messages BEFORE appending current prompt & AI placeholder
    history = MessageStore.get_ordered_msgs_by_thread_id(db, thread_id)
    lc_history = [ChatEngine.to_lc_message(m.role.value, m.content) for m in history]

    # Save user message
    human_msg = MessageStore.create(db, thread_id, MessageRole.USER, req.prompt, MessageStatus.COMPLETE)

    # Update thread metadata on first message
    ThreadStore.update_metadata(
        thread,
        title=req.prompt[:100],
        llm_model=DEFAULT_MODEL,
        rag_strategy=DEFAULT_RAG_STRATEGY,
    )

    try:
        db.commit()
        db.refresh(thread)
        db.refresh(human_msg)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during thread update & message creation.",
                "error": str(e.__cause__ or e),
            },
        )

    # Create a placeholder AI message
    ai_msg = MessageStore.create(db, thread_id, MessageRole.ASSISTANT, "", MessageStatus.STREAMING)

    try:
        db.commit()
        db.refresh(ai_msg)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during initiation of message.",
                "error": str(e.__cause__ or e),
            },
        )

    # Resolve which model and rag strategy this thread uses
    curr_model = req.llm_model or thread.llm_model or DEFAULT_MODEL
    curr_strategy = req.rag_strategy or getattr(thread, "rag_strategy", None) or DEFAULT_RAG_STRATEGY

    # Start streaming response
    db.expunge(ai_msg)  # detach — ai_msg must not stay bound to the sync session

    return StreamingResponse(
        generator(
            req.prompt,
            lc_history,
            ai_msg,
            async_db_session,
            thread_id,
            llm_model=curr_model,
            rag_strategy=curr_strategy,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ------------------------------------------------------------------------------


@router.post("/{thread_id}/stop", status_code=200)
async def stop_chat_stream(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        user_id = int(access_token.sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload.")

    thread = ThreadStore.get_for_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    task = active_tasks.get(thread_id)
    if task and not task.done():
        task.cancel()
        logger.info("Chat stream cancelled thread_id=%s user_id=%s", thread_id, user_id)

    # Clean up any lingering STREAMING messages in DB
    streaming_msgs = (
        db.query(Message)
        .filter(Message.thread_id == thread_id, Message.status == MessageStatus.STREAMING)
        .all()
    )
    if streaming_msgs:
        for msg in streaming_msgs:
            MessageStore.update_message(msg, MessageStatus.CANCELLED)
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.error("Failed to update streaming message status to CANCELLED thread_id=%s", thread_id, exc_info=True)

    return {
        "message": "Chat generation stopped successfully.",
        "thread_id": thread_id,
    }

