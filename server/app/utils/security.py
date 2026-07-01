import hashlib
from datetime import UTC, datetime, timedelta

from jwt import encode

from app.core.app_configs import getAppConfig
from app.schema.authSchema import TokenType

AppConfig = getAppConfig()


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


# --------------------------------------------------------------------------------


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
