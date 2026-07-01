import uuid
from collections.abc import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.langchain.chat_engine import ChatEngine
from app.models.chats import MessageRole, MessageStatus
from app.repositories.message_repo import MessageRepo
from app.repositories.thread_repo import ThreadRepo
from app.schema.authSchema import TokenPayload

_DEFAULT_MODEL = "qwen2.5:1.5b"

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
        yield chunk


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
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during thread creation.",
                "error": str(e.__cause__),
            },
        )

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


async def authenticated_chat_controller_2(
    prompt: str, thread_id: str, access_token: TokenPayload, db: Session
):
    thread = ThreadRepo.get_by_id_and_user(db, thread_id, access_token.sub)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Save user message
    human_msg = MessageRepo.create(db, thread_id, MessageRole.USER, prompt, MessageStatus.COMPLETE)

    # Update thread metadata on first message
    ThreadRepo.update_metadata(thread, title=prompt[:100], llm_model=_DEFAULT_MODEL)

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

    # build LC history from DBMessage
    history = MessageRepo.get_ordered_msgs_by_thread_id(db, thread_id)
    lc_history = [ChatEngine.to_lc_message(m.role.value, m.content) for m in history]

    return lc_history, ai_msg


# ---------------------------------------------------------------------------


async def generator(
    prompt: str,
    lc_history: list[ChatEngine.to_lc_message],
    ai_msg: MessageRepo.create,
    db: Session,
) -> AsyncGenerator[str]:
    # Stream the response
    full_response = ""
    async for chunk in ChatEngine.stream(lc_history, prompt):
        full_response += chunk
        yield chunk

    MessageRepo.update_message(ai_msg, MessageStatus.COMPLETE, content=full_response)
    try:
        db.commit()
    except Exception:
        db.rollback()
