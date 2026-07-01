from typing import Literal

from pydantic import BaseModel


class MessageEntry(BaseModel):
    role: Literal["human", "ai"]
    content: str


class ChatRequest(BaseModel):
    history: list[MessageEntry] | None = None
    prompt: str
