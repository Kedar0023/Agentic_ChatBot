from pydantic import BaseModel, Field,field_validator

class SignupRequest(BaseModel):
    username:str =  Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if any(char.isspace() for char in value):
            raise ValueError("Username cannot contain whitespace")
        return value


class LoginRequest(SignupRequest):
    pass