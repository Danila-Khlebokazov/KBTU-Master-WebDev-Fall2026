from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import DBSession, Project, Task, User, ensure_exists, get_or_404
from dependencies import AUTH_RESPONSES, FORBIDDEN, CurrentUser, forbid
from routers.tags import resolve_tags
from schemas import ID, Limit, Offset, TaskCreate, TaskOut, TaskStatus, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

NOT_FOUND = {404: {"description": "Task not found"}}
WRITE_ERRORS = {**AUTH_RESPONSES, **FORBIDDEN, **NOT_FOUND}


async def project_owner_id(session: AsyncSession, project_id: int) -> int | None:
    return await session.scalar(
        select(Project.owner_id).where(Project.id == project_id)
    )


async def get_editable_task(session: AsyncSession, task_id: int, user: User) -> Task:
    """Project owner or the assignee may edit a task."""
    task = await get_or_404(session, Task, task_id, "Task")
    if user.id not in (
        await project_owner_id(session, task.project_id),
        task.assignee_id,
    ):
        raise forbid("Only the project owner or the assignee can edit this task")
    return task


async def apply_task_changes(
    session: AsyncSession, task: Task, data: dict, user: User
) -> Task:
    if "project_id" in data and data["project_id"] != task.project_id:
        await ensure_exists(session, Project, data["project_id"], "Project")
        owners = {
            await project_owner_id(session, task.project_id),
            await project_owner_id(session, data["project_id"]),
        }
        if owners != {user.id}:
            raise forbid("You must own both projects to move a task")
    if data.get("assignee_id") is not None:
        await ensure_exists(session, User, data["assignee_id"], "Assignee")
    if "tag_ids" in data:
        task.tags = await resolve_tags(session, data.pop("tag_ids"))
    for field, value in data.items():
        setattr(task, field, value)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    session: DBSession,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    project_id: Annotated[int | None, Query(gt=0)] = None,
    assignee_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    query = select(Task).order_by(Task.id).limit(limit).offset(offset)
    if task_status is not None:
        query = query.where(Task.status == task_status)
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    result = await session.scalars(query)
    return result.all()


@router.get("/{task_id}", response_model=TaskOut, responses=NOT_FOUND)
async def get_task(task_id: ID, session: DBSession):
    return await get_or_404(session, Task, task_id, "Task")


@router.put("/{task_id}", response_model=TaskOut, responses=WRITE_ERRORS)
async def replace_task(
    task_id: ID, payload: TaskCreate, user: CurrentUser, session: DBSession
):
    """Replace all editable fields of a task (project stays the same)."""
    task = await get_editable_task(session, task_id, user)
    return await apply_task_changes(session, task, payload.model_dump(), user)


@router.patch("/{task_id}", response_model=TaskOut, responses=WRITE_ERRORS)
async def update_task(
    task_id: ID, payload: TaskUpdate, user: CurrentUser, session: DBSession
):
    task = await get_editable_task(session, task_id, user)
    return await apply_task_changes(
        session, task, payload.model_dump(exclude_unset=True), user
    )


@router.delete(
    "/{task_id}", status_code=status.HTTP_204_NO_CONTENT, responses=WRITE_ERRORS
)
async def delete_task(task_id: ID, user: CurrentUser, session: DBSession):
    task = await get_or_404(session, Task, task_id, "Task")
    if await project_owner_id(session, task.project_id) != user.id:
        raise forbid("Only the project owner can delete tasks")
    await session.delete(task)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
