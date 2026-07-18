from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schema.authSchema import LoginRequest, LoginResponse, SignupRequest, SignupResponse
from app.controllers import auth

router = APIRouter(prefix="/auth")

# --------------------------------------------------------------------------------


@router.post("/register", status_code=201, response_model=SignupResponse)
async def register(req: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    return await auth.register_controller(req, db)


# --------------------------------------------------------------------------------


@router.post("/login", status_code=200, response_model=LoginResponse)
async def login(req: LoginRequest, res: Response, db: Annotated[Session, Depends(get_db)]):
    return await auth.login_controller(req, res, db)


# --------------------------------------------------------------------------------


@router.post("/refresh", status_code=200)
async def token_refresh(req: Request, res: Response, db: Annotated[Session, Depends(get_db)]):
    return await auth.token_refresher_controller(req, res, db)


# --------------------------------------------------------------------------------


@router.post("/logout", status_code=200)
async def logout(req: Request, res: Response, db: Annotated[Session, Depends(get_db)]):
    return await auth.logout_controller(req, res, db)


# --------------------------------------------------------------------------------
