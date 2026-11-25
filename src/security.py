from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt

from settings import get_settings

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed_password.encode())
    except ValueError:
        # Malformed/unusable hash or password longer than 72 bytes
        return False


def create_token(user_id: int, token_version: int, token_type: TokenType) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        if token_type == "access"
        else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "ver": token_version,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_token_pair(user_id: int, token_version: int) -> dict:
    return {
        "access_token": create_token(user_id, token_version, "access"),
        "refresh_token": create_token(user_id, token_version, "refresh"),
        "token_type": "bearer",
        "expires_in": get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def decode_token(token: str, expected_type: TokenType) -> tuple[int, int]:
    """Return (user_id, token_version). Raises jwt.InvalidTokenError on any problem."""
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "exp", "type", "ver"]},
    )
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("Wrong token type")
    try:
        return int(payload["sub"]), int(payload["ver"])
    except (TypeError, ValueError):
        raise jwt.InvalidTokenError("Malformed claims") from None
