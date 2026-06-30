from datetime import datetime, UTC, timedelta
import uuid

import bcrypt
from fastapi import HTTPException, Request, Response
from jwt import ExpiredSignatureError, InvalidTokenError, decode
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import RefreshToken, User
from app.schema.authSchema import LoginRequest, SignupRequest, TokenType
from app.repositories.user_repo import UserRepo
from app.repositories.refresh_token_repo import RefreshTokenRepo
from app.utils.security import create_token, hash_token
from app.configs.app_configs import getAppConfig

AppConfig = getAppConfig()


# ----------------------------------------------------------------------------------
async def register_controller(req: SignupRequest, db: Session):
    # check user exists
    userExists: User | None = UserRepo.user_exists(db, req.username)

    if userExists:
        raise HTTPException(status_code=400, detail="Username already exists. Try a different one.")

    # Hash the password
    hashed_pwd = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # save user to DB
    try:
        user: User = UserRepo.create_user(db, req.username, hashed_pwd)
        db.commit()
        db.refresh(user)

    except Exception as e:
        db.rollback()
        if isinstance(e, IntegrityError):
            # Guard against race-condition duplicate inserts
            raise HTTPException(
                status_code=400, detail="Username already exists or invalid data provided."
            )
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during registration."
        )
    return {"message": "User registered successfully", "userId": str(user.id)}


# ----------------------------------------------------------------------------------


async def login_controller(req: LoginRequest, res: Response, db: Session):
    # Verify user exists
    user: User | None = UserRepo.get_user_by_username(db, req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    pwd: bool = bcrypt.checkpw(req.password.encode("utf-8"), user.password.encode("utf-8"))
    if not pwd:
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

    RefreshTokenRepo.create(
        db, user.id, token_hash, datetime.now(UTC) + timedelta(days=AppConfig.refresh_exp_days)
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while storing the refresh token.",
        )

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


# ----------------------------------------------------------------------------------


async def logout_controller(req: Request, res: Response, db: Session):
    refresh_token = req.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    hashed_token = hash_token(refresh_token)

    rf_record: RefreshToken | None = RefreshTokenRepo.get_active_token_by_hash(db, hashed_token)
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

    res.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="strict")
    return {"message": "User logged out successfully"}


# ----------------------------------------------------------------------------------


async def token_refresher_controller(req: Request, res: Response, db: Session):
    refresh_token = req.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    # Validate JWT signature and expiry
    try:
        payload = decode(
            refresh_token,
            AppConfig.jwt_secret_key,
            algorithms=[AppConfig.jwt_algorithm],
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Confirm it is actually a refresh token
    if payload.get("type") != TokenType.REFRESH.value:
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id: str | None = payload.get("sub")  # sub = user_id
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user: User | None = UserRepo.get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Verify the incoming token against its stored hash
    incoming_hash = hash_token(refresh_token)
    rf_record: RefreshToken | None = RefreshTokenRepo.get_by_user_and_hash(
        db, user.id, incoming_hash
    )

    if not rf_record:
        raise HTTPException(status_code=401, detail="Refresh token not recognised")
    elif rf_record.is_revoked:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    elif rf_record.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Refresh token has expired")

    # Refresh-token rotation — revoke old, issue new
    rf_record.is_revoked = True

    new_payload = {"sub": str(user.id), "username": user.username, "jti": str(uuid.uuid4())}
    new_access_token = create_token(new_payload, TokenType.ACCESS)
    new_refresh_token = create_token(new_payload, TokenType.REFRESH)

    RefreshTokenRepo.create(
        db, user.id, hash_token(new_refresh_token), 
        expires_at= datetime.now(UTC) + timedelta(days=AppConfig.refresh_exp_days)
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException( status_code=500,
            detail="An unexpected error occurred while rotating the refresh token.",
        )

    res.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=AppConfig.refresh_exp_days * 24 * 60 * 60)
    
    return {
        "message": "Token refreshed successfully",
        "userId": str(user.id),
        "username": user.username,
        "access_token": new_access_token,
    }

