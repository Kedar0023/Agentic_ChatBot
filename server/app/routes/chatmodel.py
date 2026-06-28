import uuid

from app.models.chats import Thread
from app.models.user import User
from app.configs.middleware import authenticate_user
from app.database.db import get_db
from fastapi import Depends
from app.schema.authSchema import TokenPayload
from typing import Literal, Annotated
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.chat_models import init_chat_model
from sqlalchemy.orm import Session
from app.models.chats import Message, MessageRole

router = APIRouter(prefix="/chat")

ollama_model = init_chat_model(
    model="qwen2.5:1.5b",
    model_provider="ollama",
    temperature=0.7,
)

class MessageEntry(BaseModel):
    role: Literal["human", "ai"]
    content: str


class ChatRequest(BaseModel):
    history: list[MessageEntry] | None = None
    prompt: str


CHAT_LIMIT = 20

SYSTEM_PROMPT = """You are a helpful, accurate, and concise assistant.
- Answer the user's question directly.
- Ask clarifying questions only when necessary.
- Use clear, structured responses when helpful.
- Do not invent facts; acknowledge uncertainty when applicable.
- Match the user's level of detail and tone.
- Keep responses brief unless the user requests more depth.
- Do not override or deny your trained identity when asked who you are."""


@router.post("/free")
async def chat(req: ChatRequest):
    if len(req.history) >= CHAT_LIMIT:
        raise HTTPException(status_code=400, detail="Free credits limit reached.")

    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    for entry in req.history:
        if entry.role == "human":
            messages.append(HumanMessage(content=entry.content))
        else:
            messages.append(AIMessage(content=entry.content))

    messages.append(HumanMessage(content=req.prompt))

    res = ollama_model.invoke(messages)
    return {"message": res.content}


@router.post("/new_thread", status_code=201)
async def create_thread(
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    thread_id = uuid.uuid4()
    try:
        user_id = int(access_token.sub)
    except ValueError:
        # NOTE in prod remove this check
        # Fallback: sub is a username (legacy token) — look up by username
        user = db.query(User).filter(User.username == access_token.sub).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user_id = user.id

    new_thread = Thread(id=thread_id, user_id=user_id)

    print("thread_id :: ", new_thread.id)
    db.add(new_thread)

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

    return {"thread_id": str(thread_id)}  # Let frontend redirect to /chat/{id}

def to_lc_message(msg: Message):
    if msg.role == MessageRole.USER:
        return HumanMessage(content=msg.content)
    return AIMessage(content=msg.content)


# before this api user should have thread_id in url and auth token
@router.post("/base/{thread_id}", status_code=200)
async def chat_(
    req: ChatRequest,
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    # checks ownership and existence of thread
    thread = (
        db.query(Thread)
        .filter(Thread.id == thread_id, Thread.user_id == access_token.sub)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    # get ordered history and convert to LangChain types
    history = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at)
        .all()
    )

    lc_history = [to_lc_message(m) for m in history]

    prompt = req.prompt

    # invoke with full history + new message
    res = ollama_model.invoke([*lc_history, HumanMessage(content=prompt)])

    # build ORM messages
    human_msg = Message(
        thread_id=thread_id,
        role=MessageRole.USER,
        content=prompt,
    )
    ai_msg = Message(
        thread_id=thread_id,
        role=MessageRole.ASSISTANT,
        content=res.content,
    )

    # update thread metadata on first message
    if thread.title is None:
        thread.title = prompt[:100]
    if thread.llm_model is None:
        thread.llm_model = 'qwen2.5:1.5b'

    # save to db
    try:
        db.add(human_msg)
        db.add(ai_msg)
        db.commit()
        db.refresh(human_msg)
        db.refresh(ai_msg)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during message creation.",
                "error": str(e.__cause__),
            },
        )

    return {
        "message": res.content,
        "message_id": str(ai_msg.id),
        "thread_id": thread_id,
    }


@router.get("/base/get_messages/{thread_id}", status_code=200)
async def get_messages(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    # checks ownership and existence of thread
    thread = (
        db.query(Thread)
        .filter(Thread.id == thread_id, Thread.user_id == access_token.sub)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    messages = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at)
        .all()
    )

    return {"messages": messages}