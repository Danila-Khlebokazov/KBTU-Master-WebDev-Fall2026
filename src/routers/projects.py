from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import DBSession, Project, Task, User, ensure_exists, get_or_404
from dependencies import AUTH_RESPONSES, FORBIDDEN, CurrentUser, forbid
from routers.tags import resolve_tags
from schemas import (
    ID,
    Limit,
    Offset,
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectUpdate,
    TaskCreate,
    TaskOut,
    TaskStatus,
)

router = APIRouter(prefix="/projects", tags=["projects"])

NOT_FOUND = {404: {"description": "Project not found"}}
WRITE_ERRORS = {**AUTH_RESPONSES, **FORBIDDEN, **NOT_FOUND}


async def get_owned_project(
    session: AsyncSession, project_id: int, user: User
) -> Project:
    project = await get_or_404(session, Project, project_id, "Project")
    if project.owner_id != user.id:
        raise forbid("Only the project owner can do this")
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    session: DBSession,
    owner_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    query = select(Project).order_by(Project.id).limit(limit).offset(offset)
    if owner_id is not None:
        query = query.where(Project.owner_id == owner_id)
    result = await session.scalars(query)
    return result.all()


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    responses=AUTH_RESPONSES,
)
async def create_project(payload: ProjectCreate, user: CurrentUser, session: DBSession):
    """Create a project owned by the current user."""
    project = Project(**payload.model_dump(), owner_id=user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectDetail, responses=NOT_FOUND)
async def get_project(project_id: ID, session: DBSession):
    project = await get_or_404(session, Project, project_id, "Project")
    owner = await session.get(User, project.owner_id)
    task_count = await session.scalar(
        select(func.count()).select_from(Task).where(Task.project_id == project_id)
    )
    return ProjectDetail.model_validate(
        {
            **ProjectOut.model_validate(project).model_dump(),
            "owner": owner,
            "task_count": task_count,
        }
    )


@router.put("/{project_id}", response_model=ProjectOut, responses=WRITE_ERRORS)
async def replace_project(
    project_id: ID, payload: ProjectCreate, user: CurrentUser, session: DBSession
):
    project = await get_owned_project(session, project_id, user)
    for field, value in payload.model_dump().items():
        setattr(project, field, value)
    await session.commit()
    await session.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectOut, responses=WRITE_ERRORS)
async def update_project(
    project_id: ID, payload: ProjectUpdate, user: CurrentUser, session: DBSession
):
    project = await get_owned_project(session, project_id, user)
    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data:
        await ensure_exists(session, User, data["owner_id"], "Owner")
    for field, value in data.items():
        setattr(project, field, value)
    await session.commit()
    await session.refresh(project)
    return project


@router.delete(
    "/{project_id}", status_code=status.HTTP_204_NO_CONTENT, responses=WRITE_ERRORS
)
async def delete_project(project_id: ID, user: CurrentUser, session: DBSession):
    project = await get_owned_project(session, project_id, user)
    await session.delete(project)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/tasks", response_model=list[TaskOut], responses=NOT_FOUND)
async def list_project_tasks(
    project_id: ID,
    session: DBSession,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
):
    await get_or_404(session, Project, project_id, "Project")
    query = select(Task).where(Task.project_id == project_id).order_by(Task.id)
    if task_status is not None:
        query = query.where(Task.status == task_status)
    result = await session.scalars(query)
    return result.all()


@router.post(
    "/{project_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    responses=WRITE_ERRORS,
)
async def create_project_task(
    project_id: ID, payload: TaskCreate, user: CurrentUser, session: DBSession
):
    await get_owned_project(session, project_id, user)
    if payload.assignee_id is not None:
        await ensure_exists(session, User, payload.assignee_id, "Assignee")
    tags = await resolve_tags(session, payload.tag_ids)
    task = Task(
        **payload.model_dump(exclude={"tag_ids"}), project_id=project_id, tags=tags
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task
