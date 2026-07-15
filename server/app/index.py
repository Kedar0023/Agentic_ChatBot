
from fastapi import  FastAPI
from fastapi.exception_handlers import RequestValidationError

from app.core.app_configs import getAppConfig
from app.core.exception_handler import validation_exception_handler
from app.routes.auth import router as auth_router
from app.routes.chatmodel import router as chat_router
from app.routes.document import router as document_router

app = FastAPI()
config = getAppConfig()

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(document_router)
