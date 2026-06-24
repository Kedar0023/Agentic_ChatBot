import uuid
from sqlalchemy.exc import IntegrityError
from app.configs.app_configs import getAppConfig
from datetime import datetime, timedelta, timezone
from typing import Annotated
import bcrypt
from fastapi import APIRouter , Depends, HTTPException ,Response
from app.schema.authSchema import SignupRequest ,LoginRequest
from app.database.db import get_db
from sqlalchemy.orm import Session
from app.models.user import User , RefreshToken
from jwt import encode
from enum import Enum
import hashlib
#--------------------------------------------------------------------------------

AppConfig = getAppConfig()
router = APIRouter(prefix="/auth")

#--------------------------------------------------------------------------------
@router.post("/register",status_code=201)
async def register(req:SignupRequest, db:Annotated[Session , Depends(get_db)]):
    #check user exists
    user: User | None = db.query(User).filter(User.username == req.username).first()

    if user:
        raise HTTPException(status_code=400, detail="Username already exists, Try a different one.")
    
    # Hash the password
    hashed_pwd = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    #save user to DB
    new_user = User(
        username = req.username,
        password = hashed_pwd,
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError :
        # if race condition occurs
        db.rollback()
        raise HTTPException(status_code=400, detail="User already exists or invalid data provided.")
    except Exception :
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred during registration.")

    db.refresh(new_user)
    
    return {"message": "User registered successfully"}
#--------------------------------------------------------------------------------

class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_tokens(payload,type: TokenType)-> str:
    payload = payload.copy()
    if type == TokenType.ACCESS:
        expire = datetime.now(timezone.utc) + timedelta(minutes= AppConfig.access_exp_mins)
        payload.update({"type": "access"})
    elif type == TokenType.REFRESH:
        expire = datetime.now(timezone.utc) + timedelta(days=AppConfig.refresh_exp_days)
        payload.update({"type": "refresh"})
    else:
        raise ValueError("Invalid token type")

    payload.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return encode(payload, AppConfig.jwt_secret_key, algorithm=AppConfig.jwt_algorithm)


@router.post("/login",status_code=200)
async def login(req:LoginRequest,res:Response, db:Annotated[Session , Depends(get_db)],):
    # user exists
    user: User | None = db.query(User).filter(User.username == req.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    pwd: bool = bcrypt.checkpw(req.password.encode("utf-8"),user.password.encode("utf-8"))
    if not pwd:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {"username" : user.username,"jti": str(uuid.uuid4())}

    access_token = create_tokens(payload, TokenType.ACCESS)
    refresh_token = create_tokens(payload, TokenType.REFRESH)

    # hash the refresh token
    token_hash = hashlib.sha256(refresh_token.encode()).digest()
    hashed_refresh_token = bcrypt.hashpw(token_hash, bcrypt.gensalt()).decode("utf-8")

    # Store refresh token in DB
    rf_token = RefreshToken(
        user_id=user.id,
        token=hashed_refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=AppConfig.refresh_exp_days),
    )
    user.refresh_tokens.append(rf_token)

    try:
        db.commit()
    except Exception :
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred while storing the refresh token.")

    res.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age= AppConfig.refresh_exp_days * 24 * 60 * 60,  # Convert days to seconds
    )

    return {"access_token": access_token}