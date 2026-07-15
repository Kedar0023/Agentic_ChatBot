from typing import Literal

from pydantic import BaseModel
from dataclasses import dataclass

class MessageEntry(BaseModel):
    role: Literal["human", "ai"]
    content: str


class ChatRequest(BaseModel):
    history: list[MessageEntry] | None = None
    prompt: str


@dataclass
class Context:
    thread_id: str