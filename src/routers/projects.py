from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, select

from db import DBSession, Project, Task, User, ensure_exists, get_or_404
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
BAD_REF = {422: {"description": "Validation error or referenced user missing"}}


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
    responses=BAD_REF,
)
async def create_project(payload: ProjectCreate, session: DBSession):
    await ensure_exists(session, User, payload.owner_id, "Owner")
    project = Project(**payload.model_dump())
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


@router.patch(
    "/{project_id}",
    response_model=ProjectOut,
    responses={**NOT_FOUND, **BAD_REF},
)
async def update_project(project_id: ID, payload: ProjectUpdate, session: DBSession):
    project = await get_or_404(session, Project, project_id, "Project")
    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data:
        await ensure_exists(session, User, data["owner_id"], "Owner")
    for field, value in data.items():
        setattr(project, field, value)
    await session.commit()
    await session.refresh(project)
    return project


@router.delete(
    "/{project_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND
)
async def delete_project(project_id: ID, session: DBSession):
    project = await get_or_404(session, Project, project_id, "Project")
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
    responses={**NOT_FOUND, **BAD_REF},
)
async def create_project_task(project_id: ID, payload: TaskCreate, session: DBSession):
    await get_or_404(session, Project, project_id, "Project")
    if payload.assignee_id is not None:
        await ensure_exists(session, User, payload.assignee_id, "Assignee")
    task = Task(**payload.model_dump(), project_id=project_id)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task
