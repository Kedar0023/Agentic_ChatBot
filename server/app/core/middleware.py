from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError, decode
from pydantic import ValidationError

from app.core.app_configs import getAppConfig
from app.schema.authSchema import TokenPayload, TokenType

appConfig = getAppConfig()

oauth_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# -------------------------------------------------------------------------------
def decode_access_token(token: str) -> TokenPayload:
    try:
        decoded_token = decode(
            token, appConfig.jwt_secret_key, algorithms=[appConfig.jwt_algorithm]
        )
        return TokenPayload.model_validate(decoded_token)

    except ValidationError:
        raise HTTPException(status_code=401, detail="Malformed token payload")

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")

    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# -------------------------------------------------------------------------------
def authenticate_user(token: Annotated[str, Depends(oauth_scheme)]) -> TokenPayload:
    payload = decode_access_token(token)

    # print(payload)

    if payload.type != TokenType.ACCESS:
        raise HTTPException(status_code=401, detail="Access token required")

    return payload
