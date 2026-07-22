from enum import Enum

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------------
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


# --------------------------------------------------------------------------------
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


class SignupResponse(BaseModel):
    message: str
    userId: str


class LoginResponse(BaseModel):
    message: str
    userId: str
    username: str
    access_token: str


class UserResponse(BaseModel):
    id: str
    userId: str
    username: str
    is_active: bool

