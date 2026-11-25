import jwt
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from db import DBSession, User, commit_or_409
from dependencies import unauthorized
from schemas import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
    UserOut,
)
from security import create_token_pair, decode_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS = {401: {"description": "Invalid credentials or token"}}


async def ensure_unique_identity(
    session: DBSession, username: str, email: str, exclude_id: int | None = None
) -> None:
    """Friendly 409 messages before hitting the DB unique constraints."""
    for column, value, label in (
        (User.username, username, "username"),
        (User.email, email, "email"),
    ):
        query = select(User.id).where(column == value)
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)
        if await session.scalar(query) is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"User with this {label} already exists"
            )


@router.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Username or email already taken"}},
)
async def signup(payload: SignupRequest, session: DBSession):
    await ensure_unique_identity(session, payload.username, payload.email)
    user = User(
        username=payload.username,
        email=payload.email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
    )
    session.add(user)
    await commit_or_409(session, "Username or email already exists")
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenPair, responses=INVALID_CREDENTIALS)
async def login(payload: LoginRequest, session: DBSession):
    user = await session.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise unauthorized("Invalid username or password")
    return create_token_pair(user.id, user.token_version)


@router.post("/refresh", response_model=TokenPair, responses=INVALID_CREDENTIALS)
async def refresh(payload: RefreshRequest, session: DBSession):
    try:
        user_id, token_version = decode_token(payload.refresh_token, "refresh")
    except jwt.ExpiredSignatureError:
        raise unauthorized("Refresh token expired") from None
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid refresh token") from None
    user = await session.get(User, user_id)
    if user is None or user.token_version != token_version:
        raise unauthorized("Invalid refresh token")
    return create_token_pair(user.id, user.token_version)
