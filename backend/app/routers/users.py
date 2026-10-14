from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status
from sqlalchemy import select

from app.deps import FORBIDDEN, UNAUTHORIZED, AdminUser, SessionDep
from app.models import Role, User
from app.schemas import Message, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users (admin)"], responses=UNAUTHORIZED | FORBIDDEN)

NOT_FOUND = {404: {"model": Message, "description": "User not found"}}

UserId = Annotated[int, Path(description="User ID", examples=[2])]


async def _get_user(session: SessionDep, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.get("", response_model=list[UserRead], summary="List all users")
async def list_users(_: AdminUser, session: SessionDep) -> list[User]:
    """All registered users ordered by ID."""
    return list(await session.scalars(select(User).order_by(User.id)))


@router.get("/{user_id}", response_model=UserRead, summary="Get user by ID", responses=NOT_FOUND)
async def get_user(user_id: UserId, _: AdminUser, session: SessionDep) -> User:
    return await _get_user(session, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update user name, role or active flag",
    responses=NOT_FOUND | {400: {"model": Message, "description": "Admin cannot demote self"}},
)
async def update_user(
    user_id: UserId, data: UserUpdate, admin: AdminUser, session: SessionDep
) -> User:
    """Partial update: send only the fields to change. Disabled users (`is_active=false`)
    cannot log in and their existing tokens stop working."""
    user = await _get_user(session, user_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if user.id == admin.id and (
        changes.get("role", Role.ADMIN) != Role.ADMIN or changes.get("is_active") is False
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot demote or disable yourself")
    for field, value in changes.items():
        setattr(user, field, value)
    await session.commit()
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user and all their expenses",
    responses=NOT_FOUND | {400: {"model": Message, "description": "Admin tried to delete self"}},
)
async def delete_user(user_id: UserId, admin: AdminUser, session: SessionDep) -> Response:
    """Delete a user account. Their expenses are deleted too (`ON DELETE CASCADE`)."""
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete yourself")
    user = await _get_user(session, user_id)
    await session.delete(user)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
