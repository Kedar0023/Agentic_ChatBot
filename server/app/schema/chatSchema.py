from typing import Literal

from pydantic import BaseModel, Field
from dataclasses import dataclass

class MessageEntry(BaseModel):
    role: Literal["human", "ai"]
    content: str


class ChatRequest(BaseModel):
    history: list[MessageEntry] | None = None
    prompt: str


class UpdateModelRequest(BaseModel):
    model: str


class UpdateTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


@dataclass
class Context:
    thread_id: str