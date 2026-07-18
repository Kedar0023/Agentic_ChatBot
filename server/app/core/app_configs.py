from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to THIS file, not the launch directory
ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class AppConfigs(BaseSettings):
    app_name: str = "Fastapi_chatbot"
    app_env: str = "fast_env"
    database_url: SecretStr 
    jwt_secret_key: SecretStr
    jwt_algorithm: str
    access_exp_mins: int = 30
    refresh_exp_days: int = 5

    chroma_persist_dir: SecretStr
    chroma_collection_name: str = "docs_collection"

    cloudflare_account_id: SecretStr
    cloudflare_access_key_id: SecretStr
    cloudflare_secret_access_key: SecretStr
    cloudflare_bucket_name: SecretStr



    model_config = SettingsConfigDict(env_file=str(ENV_FILE))


@lru_cache
def getAppConfig() -> AppConfigs:
    return AppConfigs()
