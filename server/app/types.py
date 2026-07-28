from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if any(char.isspace() for char in value):
            raise ValueError("Username cannot contain whitespace")
        return value


class LoginRequest(SignupRequest):
    pass


class SignupResponse(BaseModel):
    message: str
    userId: str


class LoginResponse(BaseModel):
    message: str
    userId: str
    username: str
    access_token: str


class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    type: TokenType
    username: str
    exp: int
    iat: int
    sub: str
    jti: str


class UserResponse(BaseModel):
    id: str
    userId: str
    username: str
    is_active: bool


from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


class MessageEntry(BaseModel):
    role: Literal["human", "ai"]
    content: str


class ChatRequest(BaseModel):
    history: list[MessageEntry] | None = None
    prompt: str
    llm_model: str | None = None


class UpdateModelRequest(BaseModel):
    model: str


class UpdateTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


@dataclass
class Context:
    thread_id: str
