import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt

# import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.app_configs import getAppConfig
from app.core.logging import logger
from app.database.db import get_db
from app.models.user import RefreshToken, User
from app.store.TokenStore import RfTokenStore
from app.store.UserStore import UserStore
from app.types import LoginRequest, LoginResponse, SignupRequest, SignupResponse, TokenType
from app.utils.security import create_token, hash_token

router = APIRouter(prefix="/v2/auth", tags=["auth"])
AppConfig = getAppConfig()
# --------------------------------------------------------------------------------


@router.post("/register", status_code=201, response_model=SignupResponse)
async def register(req: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    # check user exists
    userExists: bool = UserStore.user_exists(db, req.username)

    if userExists:
        raise HTTPException(status_code=400, detail="Username already exists. Try a different one.")

    # Hash the password
    hashed_pwd = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # save user to DB
    try:
        user: User = UserStore.create_user(db, req.username, hashed_pwd)
        db.commit()
        db.refresh(user)

    except Exception as e:
        db.rollback()
        if isinstance(e, IntegrityError):
            # Guard against race-condition duplicate inserts
            logger.warning("Registration integrity conflict for user=%s", req.username)
            raise HTTPException(status_code=400, detail="Username already exists or invalid data provided.")
        logger.error("Registration failed for user=%s", req.username, exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during registration.")
    logger.info("User registered user_id=%s", user.id)
    return {"message": "User registered successfully", "userId": str(user.id)}


# --------------------------------------------------------------------------------


@router.post("/login", status_code=200, response_model=LoginResponse)
async def login(req: LoginRequest, res: Response, db: Annotated[Session, Depends(get_db)]):
    # Verify user exists
    user: User | None = UserStore.get_user_by_username(db, req.username)
    if not user:
        logger.warning("Login failed — unknown user=%s", req.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    pwd: bool = bcrypt.checkpw(req.password.encode("utf-8"), user.password.encode("utf-8"))
    if not pwd:
        logger.warning("Login failed — bad password user=%s", req.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Build token payload
    payload = {
        "sub": str(user.id),  # sub=user_id
        "username": user.username,
        "jti": str(uuid.uuid4()),
    }

    access_token = create_token(payload, TokenType.ACCESS)
    refresh_token = create_token(payload, TokenType.REFRESH)

    # Store only a SHA-256 hash of the refresh token in the DB.
    token_hash = hash_token(refresh_token)

    RfTokenStore.create(db, user.id, token_hash, datetime.now(UTC) + timedelta(days=AppConfig.refresh_exp_days))

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.error("Failed to store refresh token for user_id=%s", user.id, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while storing the refresh token.",
        )

    logger.info("User logged in user_id=%s", user.id)

    # Set refresh token in cookie
    res.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=AppConfig.refresh_exp_days * 24 * 60 * 60,
    )
    return {
        "message": "User Login successful",
        "userId": str(user.id),
        "username": user.username,
        "access_token": access_token,
    }


@router.post("/logout", status_code=200)
async def logout(req: Request, res: Response, db: Annotated[Session, Depends(get_db)]):
    refresh_token = req.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    res.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="strict")

    hashed_token = hash_token(refresh_token)

    rf_record: RefreshToken | None = RfTokenStore.get_active_token_by_hash(db, hashed_token)
    if not rf_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    rf_record.is_revoked = True
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while revoking the refresh token.",
        )

    logger.info("User logged out user_id=%s", rf_record.user_id)
    return {"message": "User logged out successfully"}
