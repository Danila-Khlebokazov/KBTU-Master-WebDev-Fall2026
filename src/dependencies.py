from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import DBSession, User
from security import decode_token

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    session: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized("Not authenticated")
    try:
        user_id, token_version = decode_token(credentials.credentials, "access")
    except jwt.ExpiredSignatureError:
        raise unauthorized("Token expired") from None
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid token") from None

    user = await session.get(User, user_id)
    if user is None or user.token_version != token_version:
        raise unauthorized("Invalid token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

AUTH_RESPONSES = {401: {"description": "Missing, invalid or expired token"}}
FORBIDDEN = {403: {"description": "Not allowed to modify this resource"}}


def forbid(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail)
