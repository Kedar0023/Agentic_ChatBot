import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

# import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jwt import ExpiredSignatureError, InvalidTokenError, decode
from sqlalchemy.orm import Session

from app.core.app_configs import getAppConfig
from app.core.logging import logger
from app.core.middleware import authenticate_user
from app.database.db import get_db
from app.models.user import RefreshToken, User
from app.store.TokenStore import RfTokenStore
from app.store.UserStore import UserStore
from app.types import TokenPayload, TokenType, UserResponse
from app.utils.security import create_token, hash_token

router = APIRouter(prefix="/v2/session", tags=["session"])
AppConfig = getAppConfig()


@router.post("/refresh", status_code=200)
async def token_refresh(req: Request, res: Response, db: Annotated[Session, Depends(get_db)]):
    refresh_token = req.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    # Validate JWT signature and expiry
    try:
        payload = decode(
            refresh_token,
            AppConfig.jwt_secret_key.get_secret_value(),
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

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload")

    user: User | None = UserStore.get_user_by_id(db, user_id_int)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Verify the incoming token against its stored hash
    incoming_hash = hash_token(refresh_token)
    rf_record: RefreshToken | None = RfTokenStore.get_by_user_and_hash(db, user.id, incoming_hash)

    expires_at = rf_record.expires_at if (rf_record and rf_record.expires_at and rf_record.expires_at.tzinfo) else (rf_record.expires_at.replace(tzinfo=UTC) if rf_record and rf_record.expires_at else None)

    if not rf_record:
        raise HTTPException(status_code=401, detail="Refresh token not recognised")
    elif rf_record.is_revoked:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    elif expires_at and expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Refresh token has expired")

    # Refresh-token rotation — revoke old, issue new
    rf_record.is_revoked = True
    logger.info("Token rotation for user_id=%s", user.id)

    new_payload = {"sub": str(user.id), "username": user.username, "jti": str(uuid.uuid4())}
    new_access_token = create_token(new_payload, TokenType.ACCESS)
    new_refresh_token = create_token(new_payload, TokenType.REFRESH)

    RfTokenStore.create(
        db,
        user.id,
        hash_token(new_refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=AppConfig.refresh_exp_days),
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while rotating the refresh token.",
        )

    res.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=AppConfig.refresh_exp_days * 24 * 60 * 60,
    )

    return {
        "message": "Token refreshed successfully",
        "userId": str(user.id),
        "username": user.username,
        "access_token": new_access_token,
    }


@router.get("/me", status_code=200, response_model=UserResponse)
async def get_me(
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    user_id = int(access_token.sub)
    user: User | None = UserStore.get_user_by_id(db, user_id)
    if not user:
        logger.warning("User not found for user_id=%s", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(user.id),
        "userId": str(user.id),
        "username": user.username,
        "is_active": user.is_active,
    }
