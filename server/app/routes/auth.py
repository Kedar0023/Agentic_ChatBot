from typing import Annotated

from fastapi import APIRouter , Depends
from app.schema.authSchema import SignupRequest
from app.database.db import get_db
from sqlalchemy.orm import Session


router = APIRouter(prefix="/auth")

@router.post("/register")
async def register(req:SignupRequest, db:Annotated[Session , Depends(get_db)]):
#   → check duplicate email/username
    already_exits = db.query()
#   → hash password (bcrypt)
#   → save user to DB
#   → generate JWT (access token)
#   → [optionally] generate refresh token
#   → return tokens + user info


    return {"message": req.password}