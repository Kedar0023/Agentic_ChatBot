from typing import Literal
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.chat_models import init_chat_model

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