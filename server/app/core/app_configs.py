from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to THIS file, not the launch directory
ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class AppConfigs(BaseSettings):
    app_name: str = "Fastapi_chatbot"
    app_env: str = "fast_env"
    database_url: str = "postgresql://postgres:root@localhost:5432/chatbot"
    jwt_secret_key: str = "some_random_ass_secret_key_Xdsfc78sbcn"
    jwt_algorithm: str = "HS256"
    access_exp_mins: int = 30
    refresh_exp_days: int = 5

    model_config = SettingsConfigDict(env_file=str(ENV_FILE))


@lru_cache
def getAppConfig() -> AppConfigs:
    return AppConfigs()
