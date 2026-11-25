from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from db import DBSession, Profile, Project, Task, User, commit_or_409
from dependencies import AUTH_RESPONSES, CurrentUser
from routers.auth import ensure_unique_identity
from schemas import (
    PasswordChange,
    ProfileOut,
    ProfileUpdate,
    ProfileWrite,
    ProjectOut,
    TaskOut,
    TokenPair,
    UserMe,
    UserReplace,
    UserUpdate,
)
from security import create_token_pair, hash_password, verify_password

router = APIRouter(prefix="/me", tags=["me (current user)"], responses=AUTH_RESPONSES)

CONFLICT = {409: {"description": "Username or email already taken"}}
NO_PROFILE = {404: {"description": "Profile not created yet"}}


async def me_response(session: DBSession, user: User) -> UserMe:
    profile = await session.get(Profile, user.id)
    return UserMe.model_validate(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at,
            "profile": ProfileOut.model_validate(profile) if profile else None,
        }
    )


async def apply_user_changes(session: DBSession, user: User, data: dict) -> UserMe:
    await ensure_unique_identity(
        session,
        data.get("username", user.username),
        data.get("email", user.email),
        exclude_id=user.id,
    )
    for field, value in data.items():
        setattr(user, field, value)
    await commit_or_409(session, "Username or email already exists")
    await session.refresh(user)
    return await me_response(session, user)


async def get_profile_or_404(session: DBSession, user: User) -> Profile:
    profile = await session.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return profile


@router.get("", response_model=UserMe)
async def get_me(user: CurrentUser, session: DBSession):
    return await me_response(session, user)


@router.put("", response_model=UserMe, responses=CONFLICT)
async def replace_me(payload: UserReplace, user: CurrentUser, session: DBSession):
    return await apply_user_changes(session, user, payload.model_dump())


@router.patch("", response_model=UserMe, responses=CONFLICT)
async def update_me(payload: UserUpdate, user: CurrentUser, session: DBSession):
    """Update username / email / name of the current user."""
    return await apply_user_changes(
        session, user, payload.model_dump(exclude_unset=True)
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user: CurrentUser, session: DBSession):
    """Delete own account (owned projects are deleted, assigned tasks unassigned)."""
    await session.delete(user)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/password",
    response_model=TokenPair,
    responses={400: {"description": "Current password is wrong"}},
)
async def change_password(
    payload: PasswordChange, user: CurrentUser, session: DBSession
):
    """Change password. All previously issued tokens are revoked; a fresh pair is returned."""
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Current password is incorrect"
        )
    user.hashed_password = hash_password(payload.new_password)
    user.token_version += 1
    await session.commit()
    return create_token_pair(user.id, user.token_version)


@router.get("/projects", response_model=list[ProjectOut])
async def my_projects(user: CurrentUser, session: DBSession):
    result = await session.scalars(
        select(Project).where(Project.owner_id == user.id).order_by(Project.id)
    )
    return result.all()


@router.get("/tasks", response_model=list[TaskOut])
async def my_tasks(user: CurrentUser, session: DBSession):
    result = await session.scalars(
        select(Task).where(Task.assignee_id == user.id).order_by(Task.id)
    )
    return result.all()


# Profile (one-to-one)
@router.get("/profile", response_model=ProfileOut, responses=NO_PROFILE)
async def get_my_profile(user: CurrentUser, session: DBSession):
    return await get_profile_or_404(session, user)


@router.post(
    "/profile",
    response_model=ProfileOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Profile already exists"}},
)
async def create_my_profile(
    payload: ProfileWrite, user: CurrentUser, session: DBSession
):
    if await session.get(Profile, user.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Profile already exists")
    profile = Profile(user_id=user.id, **payload.model_dump())
    session.add(profile)
    await commit_or_409(session, "Profile already exists")
    await session.refresh(profile)
    return profile


@router.put("/profile", response_model=ProfileOut, responses=NO_PROFILE)
async def replace_my_profile(
    payload: ProfileWrite, user: CurrentUser, session: DBSession
):
    profile = await get_profile_or_404(session, user)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    await session.commit()
    await session.refresh(profile)
    return profile


@router.patch("/profile", response_model=ProfileOut, responses=NO_PROFILE)
async def update_my_profile(
    payload: ProfileUpdate, user: CurrentUser, session: DBSession
):
    profile = await get_profile_or_404(session, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await session.commit()
    await session.refresh(profile)
    return profile


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT, responses=NO_PROFILE)
async def delete_my_profile(user: CurrentUser, session: DBSession):
    profile = await get_profile_or_404(session, user)
    await session.delete(profile)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
