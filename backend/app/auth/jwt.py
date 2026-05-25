from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.core.config import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        # SECURITY: Use timezone-aware datetime to avoid ambiguity and ensure consistent token expiration
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # SECURITY: Use timezone-aware datetime to avoid ambiguity and ensure consistent token expiration
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None