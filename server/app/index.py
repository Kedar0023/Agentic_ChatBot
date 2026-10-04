import os

from fastapi import FastAPI
from fastapi.exception_handlers import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.app_configs import getAppConfig
from app.core.exception_handler import validation_exception_handler
from app.core.logging import logger
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.docs import router as document_router
from app.routes.evaluation import router as evaluation_router
from app.routes.session import router as session_router
from app.routes.thread import router as thread_router

app = FastAPI()
origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")
origins = origins_env.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = getAppConfig()

app.add_exception_handler(RequestValidationError, validation_exception_handler)


# v2 routers
app.include_router(auth_router)
app.include_router(session_router)
app.include_router(thread_router)
app.include_router(chat_router)
app.include_router(document_router)
app.include_router(evaluation_router)

logger.info("App started env=%s", config.app_env)
