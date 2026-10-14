from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from app.deps import UNAUTHORIZED, CurrentUser, SessionDep, TokenPayload
from app.models import RevokedToken, User
from app.schemas import LoginRequest, Message, RegisterRequest, TokenResponse, UserRead
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    responses={409: {"model": Message, "description": "Email already registered"}},
)
async def register(data: RegisterRequest, session: SessionDep) -> User:
    """Create a new account with the `user` role. The email is stored in lower case.
    The password is hashed with bcrypt and never returned."""
    email = data.email.lower()
    if await session.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=email, full_name=data.full_name, hashed_password=hash_password(data.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT access token",
    responses={
        401: {"model": Message, "description": "Invalid credentials"},
        403: {"model": Message, "description": "Account disabled"},
    },
)
async def login(data: LoginRequest, session: SessionDep) -> TokenResponse:
    """Check credentials and return a signed JWT (HS256). The token contains the user id
    (`sub`), role, unique id (`jti`) and expiry (`exp`). Pass it in the
    `Authorization: Bearer <token>` header."""
    user = await session.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    token, expires_in = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post(
    "/logout",
    response_model=Message,
    summary="Log out (revoke the current access token)",
    responses=UNAUTHORIZED,
)
async def logout(payload: TokenPayload, session: SessionDep) -> Message:
    """JWTs are stateless, so logout stores the token's `jti` in a revocation list.
    Any later request with this token gets `401 Token has been revoked`."""
    now = datetime.now(UTC)
    await session.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
    session.add(
        RevokedToken(jti=payload["jti"], expires_at=datetime.fromtimestamp(payload["exp"], UTC))
    )
    await session.commit()
    return Message(detail="Logged out")


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the currently authenticated user",
    responses=UNAUTHORIZED,
)
async def me(user: CurrentUser) -> User:
    """Profile of the user that owns the token. The frontend uses it to restore a session."""
    return user
