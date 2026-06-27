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
    history: list[MessageEntry]
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
        raise HTTPException(status_code=500, detail={
            "message": "An unexpected error occurred during thread creation.",
            "error": str(e.__cause__)
        })

    return {"thread_id": str(thread_id)}  # Let frontend redirect to /chat/{id}


# before this api user should have thread_id in url and auth token
@router.post("/base", status_code=200)
async def chat_(
    req: ChatRequest, access_token: Annotated[TokenPayload, Depends(authenticate_user)]
):
    # extract user id from token
    # extarct thread id from url
    # get thread from db
    # get prompt from request
    # generate response
    # save prompt and response to thread
    # return response

    return {"message": "You have reached the base chat model."}