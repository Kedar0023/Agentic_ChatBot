
import os

from fastapi import  FastAPI
from fastapi.exception_handlers import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.app_configs import getAppConfig
from app.core.exception_handler import validation_exception_handler
from app.core.logging import logger
from app.routes.auth import router as auth_router
from app.routes.chatmodel import router as chat_router
from app.routes.document import router as document_router

app = FastAPI()
origins_env = os.getenv("CORS_ORIGINS", "*")
origins = origins_env.split(",") if origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = getAppConfig()

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(document_router)

logger.info("App started env=%s", config.app_env)
