from fastapi import Depends
from typing import Annotated
from app.schema.authSchema import TokenPayload
from fastapi import FastAPI
from fastapi.exception_handlers import RequestValidationError

from app.configs.app_configs import getAppConfig
from app.configs.custom_error import validation_exception_handler
from app.routes.auth import router as auth_router
from app.routes.chatmodel import router as chat_router
from app.configs.middleware import authenticate_user

app = FastAPI()
config = getAppConfig()

app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {"database_url": config.database_url}

@app.get("/health")
async def health(access_token : Annotated[TokenPayload,Depends(authenticate_user)]):
    return {"status": "ok"}
