import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session
from app.core.logging import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.langchain.chat_engine import ChatEngine
from app.langchain.llm import DEFAULT_MODEL, AVAILABLE_MODELS, list_models
from app.models.chats import Message, MessageRole, MessageStatus
from app.repositories.message_repo import MessageRepo
from app.repositories.thread_repo import ThreadRepo
from app.schema.authSchema import TokenPayload

CHAT_LIMIT = 20


async def authless_chat_controller(history: list[dict], prompt: str) -> AsyncGenerator[str]:
    if history and len(history) >= CHAT_LIMIT:
        raise ValueError("Free credits limit reached.")

    lc_history = []
    if history:
        for entry in history:
            role = "user" if entry["role"] == "human" else "assistant"
            lc_history.append(ChatEngine.to_lc_message(role, entry["content"]))

    async for chunk in ChatEngine.stream(lc_history, prompt):
        yield f"data: {json.dumps(chunk)}\n\n"


# ---------------------------------------------------------------------------


async def create_chat_thread_controller(access_token: TokenPayload, db: Session):
    thread_id = uuid.uuid4()

    user_id = int(access_token.sub)

    new_thread = ThreadRepo.create(db, thread_id, user_id)
    try:
        db.commit()
        db.refresh(new_thread)
    except Exception as e:
        db.rollback()
        logger.error("Thread creation failed user_id=%s", user_id, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during thread creation.",
                "error": str(e.__cause__),
            },
        )

    logger.info("Thread created thread_id=%s user_id=%s", thread_id, user_id)
    return {"thread_id": str(thread_id)}


# ---------------------------------------------------------------------------
async def get_messages_controller(
    thread_id: str,
    access_token: TokenPayload,
    db: Session,
):
    thread = ThreadRepo.get_by_id_and_user(db, thread_id, access_token.sub)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    messages = MessageRepo.get_ordered_msgs_by_thread_id(db, thread_id)

    return {"messages": messages}


# ---------------------------------------------------------------------------


async def authenticated_chat_controller_2(prompt: str, thread_id: str, access_token: TokenPayload, db: Session):
    thread = ThreadRepo.get_by_id_and_user(db, thread_id, access_token.sub)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Save user message
    human_msg = MessageRepo.create(db, thread_id, MessageRole.USER, prompt, MessageStatus.COMPLETE)

    # Update thread metadata on first message
    ThreadRepo.update_metadata(thread, title=prompt[:100], llm_model=DEFAULT_MODEL)

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
                "error": str(e.__cause__),
            },
        )

    # Create a placeholder AI message
    ai_msg = MessageRepo.create(db, thread_id, MessageRole.ASSISTANT, "", MessageStatus.STREAMING)

    try:
        db.commit()
        db.refresh(ai_msg)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during initiation of message.",
                "error": str(e.__cause__),
            },
        )

    # Resolve which model this thread uses
    curr_model = thread.llm_model or DEFAULT_MODEL

    # build LC history from DBMessage
    history = MessageRepo.get_ordered_msgs_by_thread_id(db, thread_id)
    lc_history = [ChatEngine.to_lc_message(m.role.value, m.content) for m in history]

    return lc_history, ai_msg, curr_model


# ---------------------------------------------------------------------------


async def generator(
    prompt: str,
    lc_history: list[HumanMessage | AIMessage],
    ai_msg: Message,
    async_db_session: async_sessionmaker[AsyncSession],
    thread_id: str,
    llm_model: str | None = None,
) -> AsyncGenerator[str]:
    parts: list[str] = []
    status = MessageStatus.COMPLETE

    # Stream the response
    logger.info("Stream started thread_id=%s model=%s", thread_id, llm_model)
    try:
        async for chunk in ChatEngine.stream(lc_history, prompt, thread_id, llm_model=llm_model):
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
        full_response = "".join(parts)

        async with async_db_session() as db:
            try:
                ai_msg = await db.merge(ai_msg)

                MessageRepo.update_message(
                    ai_msg,
                    status,
                    content=full_response,
                )
                await db.commit()
            except Exception:
                await db.rollback()
                logger.error("Failed to persist AI message msg_id=%s", ai_msg.id, exc_info=True)


# ---------------------------------------------------------------------------


# Return the catalog of available models and the thread's current selection.
async def get_thread_models_controller(thread_id: str, access_token: TokenPayload, db: Session):

    thread = ThreadRepo.get_by_id_and_user(db, thread_id, access_token.sub)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    return {
        "current_model": thread.llm_model or DEFAULT_MODEL,
        "default_model": DEFAULT_MODEL,
        "models": list_models(),
    }

#---------------------------------------------------------------------------------
async def update_thread_model_controller(thread_id: str, llm_model: str, access_token: TokenPayload, db: Session):
    if llm_model not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{llm_model}'. Use GET /models to see available options.",
        )

    thread = ThreadRepo.get_by_id_and_user(db, thread_id, access_token.sub)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    ThreadRepo.update_model(thread, llm_model)
    try:
        db.commit()
        db.refresh(thread)
    except Exception as e:
        db.rollback()
        logger.error("Model update failed thread_id=%s", thread_id, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to update model.",
                "error": str(e.__cause__),
            },
        )

    logger.info("Model updated thread_id=%s model=%s", thread_id, llm_model)
    return {
        "thread_id": str(thread.id),
        "model": thread.llm_model,
    }
