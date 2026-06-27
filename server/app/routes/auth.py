import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jwt import ExpiredSignatureError, InvalidTokenError, decode, encode
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.configs.app_configs import getAppConfig
from app.database.db import get_db
from app.models.user import RefreshToken, User
from app.schema.authSchema import LoginRequest, SignupRequest, TokenType

# --------------------------------------------------------------------------------

AppConfig = getAppConfig()
router = APIRouter(prefix="/auth")

# --------------------------------------------------------------------------------


def create_token(payload: dict, token_type: TokenType) -> str:
    payload = payload.copy()
    now = datetime.now(UTC)

    if token_type == TokenType.ACCESS:
        expire = now + timedelta(minutes=AppConfig.access_exp_mins)
    elif token_type == TokenType.REFRESH:
        expire = now + timedelta(days=AppConfig.refresh_exp_days)
    else:
        raise ValueError("Invalid token type")

    payload.update({"type": token_type.value, "exp": expire, "iat": now})
    return encode(payload, AppConfig.jwt_secret_key, algorithm=AppConfig.jwt_algorithm)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def set_refresh_cookie(res: Response, token: str) -> None:
    res.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=AppConfig.refresh_exp_days * 24 * 60 * 60,
    )


# --------------------------------------------------------------------------------
@router.post("/register", status_code=201)
async def register(req: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    # check user exists
    user: User | None = db.query(User).filter(User.username == req.username).first()

    if user:
        raise HTTPException(status_code=400, detail="Username already exists. Try a different one.")

    # Hash the password
    hashed_pwd = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # save user to DB
    new_user = User(
        username=req.username,
        password=hashed_pwd,
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        # Guard against race-condition duplicate inserts
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Username already exists or invalid data provided."
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during registration."
        )

    db.refresh(new_user)
    return {"message": "User registered successfully"}


# --------------------------------------------------------------------------------


@router.post("/login", status_code=200)
async def login(
    req: LoginRequest,
    res: Response,
    db: Annotated[Session, Depends(get_db)],
):
    # Verify user exists
    user: User | None = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    pwd: bool = bcrypt.checkpw(req.password.encode("utf-8"), user.password.encode("utf-8"))
    if not pwd:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Build token payload — sub holds the stable numeric user ID (RFC 7519 best practice)
    payload = {"sub": str(user.id), "username": user.username, "jti": str(uuid.uuid4())}

    access_token = create_token(payload, TokenType.ACCESS)
    refresh_token = create_token(payload, TokenType.REFRESH)

    # Store only a SHA-256 hash of the refresh token in the DB.
    # This lets us verify the incoming token on refresh without keeping
    # the raw JWT, and avoids the bcrypt-on-jwt-bytes pitfall.
    token_hash = hash_token(refresh_token)

    rf_record = RefreshToken(
        user_id=user.id,
        token=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=AppConfig.refresh_exp_days),
    )
    db.add(rf_record)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while storing the refresh token.",
        )

    set_refresh_cookie(res, refresh_token)
    return {"access_token": access_token}


# --------------------------------------------------------------------------------


@router.post("/refresh", status_code=200)
async def token_refresh(req: Request, res: Response, db: Annotated[Session, Depends(get_db)]):
    # Extract token from cookie
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

    user_id: str | None = payload.get("sub")  # sub holds the numeric user ID as a string
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Defensively handle legacy tokens where sub was set to the username instead of the user ID.
    # NOTE  in prod remove this check
    try:
        user: User | None = db.query(User).filter(User.id == int(user_id)).first()
    except ValueError:
        # sub is not a numeric string — treat it as a username (backward-compat)
        user = db.query(User).filter(User.username == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Verify the incoming token against its stored hash
    incoming_hash = hash_token(refresh_token)
    rf_record: RefreshToken | None = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user.id,
            RefreshToken.token == incoming_hash,
        )
        .first()
    )

    if not rf_record:
        raise HTTPException(status_code=401, detail="Refresh token not recognised")

    if rf_record.is_revoked:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    if rf_record.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Refresh token has expired")

    # Refresh-token rotation — revoke old, issue new
    rf_record.is_revoked = True

    new_payload = {"sub": str(user.id), "username": user.username, "jti": str(uuid.uuid4())}
    new_access_token = create_token(new_payload, TokenType.ACCESS)
    new_refresh_token = create_token(new_payload, TokenType.REFRESH)

    new_rf_record = RefreshToken(
        user_id=user.id,
        token=hash_token(new_refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=AppConfig.refresh_exp_days),
    )
    db.add(new_rf_record)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while rotating the refresh token.",
        )

    set_refresh_cookie(res, new_refresh_token)
    return {"access_token": new_access_token}


# --------------------------------------------------------------------------------


@router.post("/logout", status_code=200)
async def logout(req: Request, res: Response, db: Annotated[Session, Depends(get_db)]):
    refresh_token = req.cookies.get("refresh_token")

    if refresh_token:
        incoming_hash = hash_token(refresh_token)
        rf_record: RefreshToken | None = (
            db.query(RefreshToken)
            .filter(RefreshToken.token == incoming_hash, not RefreshToken.is_revoked)
            .first()
        )
        if rf_record:
            rf_record.is_revoked = True
            try:
                db.commit()
            except Exception:
                db.rollback()
                # Non-fatal — still clear the cookie so the client is logged out
                pass

    res.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="strict")
    return {"message": "Logged out successfully"}


# --------------------------------------------------------------------------------
