from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db import DBSession, Project, Task, User, get_or_404
from schemas import (
    ID,
    Limit,
    Offset,
    ProjectOut,
    TaskOut,
    TaskStatus,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])

NOT_FOUND = {404: {"description": "User not found"}}


async def commit_unique_email(session: DBSession) -> None:
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "User with this email already exists"
        ) from None


@router.get("", response_model=list[UserOut])
async def list_users(session: DBSession, limit: Limit = 50, offset: Offset = 0):
    result = await session.scalars(
        select(User).order_by(User.id).limit(limit).offset(offset)
    )
    return result.all()


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Email already taken"}},
)
async def create_user(payload: UserCreate, session: DBSession):
    user = User(**payload.model_dump())
    session.add(user)
    await commit_unique_email(session)
    await session.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut, responses=NOT_FOUND)
async def get_user(user_id: ID, session: DBSession):
    return await get_or_404(session, User, user_id, "User")


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    responses={**NOT_FOUND, 409: {"description": "Email already taken"}},
)
async def update_user(user_id: ID, payload: UserUpdate, session: DBSession):
    user = await get_or_404(session, User, user_id, "User")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await commit_unique_email(session)
    await session.refresh(user)
    return user


@router.delete(
    "/{user_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND
)
async def delete_user(user_id: ID, session: DBSession):
    user = await get_or_404(session, User, user_id, "User")
    await session.delete(user)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
