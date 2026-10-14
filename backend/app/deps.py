from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import RevokedToken, Role, User
from app.schemas import Message
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False, description="Paste the JWT from /api/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
) -> dict:
    if credentials is None:
        raise _unauthorized()
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("Invalid token") from exc

    if await session.get(RevokedToken, payload["jti"]) is not None:
        raise _unauthorized("Token has been revoked")
    return payload


async def get_current_user(
    payload: Annotated[dict, Depends(get_token_payload)], session: SessionDep
) -> User:
    user = await session.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
TokenPayload = Annotated[dict, Depends(get_token_payload)]

# Reusable OpenAPI error responses
UNAUTHORIZED = {
    401: {"model": Message, "description": "Missing, invalid, expired or revoked token"}
}
FORBIDDEN = {403: {"model": Message, "description": "Admin role required"}}
