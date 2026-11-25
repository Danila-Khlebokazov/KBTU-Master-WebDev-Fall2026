from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from db import DBSession, Profile, Project, Task, User, get_or_404
from schemas import (
    ID,
    Limit,
    Offset,
    ProfileOut,
    ProjectOut,
    TaskOut,
    TaskStatus,
    UserOut,
)

# Users are created via POST /auth/signup and managed by their owner via /me.
router = APIRouter(prefix="/users", tags=["users"])

NOT_FOUND = {404: {"description": "User not found"}}


@router.get("", response_model=list[UserOut])
async def list_users(session: DBSession, limit: Limit = 50, offset: Offset = 0):
    result = await session.scalars(
        select(User).order_by(User.id).limit(limit).offset(offset)
    )
    return result.all()


@router.get("/{user_id}", response_model=UserOut, responses=NOT_FOUND)
async def get_user(user_id: ID, session: DBSession):
    return await get_or_404(session, User, user_id, "User")


@router.get(
    "/{user_id}/profile",
    response_model=ProfileOut,
    responses={404: {"description": "User or profile not found"}},
)
async def get_user_profile(user_id: ID, session: DBSession):
    await get_or_404(session, User, user_id, "User")
    profile = await session.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} has no profile")
    return profile


@router.get("/{user_id}/projects", response_model=list[ProjectOut], responses=NOT_FOUND)
async def list_user_projects(user_id: ID, session: DBSession):
    await get_or_404(session, User, user_id, "User")
    result = await session.scalars(
        select(Project).where(Project.owner_id == user_id).order_by(Project.id)
    )
    return result.all()


@router.get("/{user_id}/tasks", response_model=list[TaskOut], responses=NOT_FOUND)
async def list_user_tasks(
    user_id: ID,
    session: DBSession,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
):
    await get_or_404(session, User, user_id, "User")
    query = select(Task).where(Task.assignee_id == user_id).order_by(Task.id)
    if task_status is not None:
        query = query.where(Task.status == task_status)
    result = await session.scalars(query)
    return result.all()
