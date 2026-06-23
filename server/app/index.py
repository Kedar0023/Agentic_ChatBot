from fastapi import FastAPI
from app.configs.app_configs import getAppConfig
from fastapi.exception_handlers import RequestValidationError
from app.configs.custom_error import validation_exception_handler
from app.routes.auth import router as auth_router
app = FastAPI()
config = getAppConfig()

app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth_router)

@app.get("/")
async def root():
    return {"database_url": config.database_url}

