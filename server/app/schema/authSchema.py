from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username:str =  Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

class SignupRequest(BaseModel):
    username:str =  Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    confirm_password: str = Field(..., min_length=6, max_length=100)

    