from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from db import DBSession, Project, Task, User, ensure_exists, get_or_404
from schemas import ID, Limit, Offset, TaskOut, TaskStatus, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

NOT_FOUND = {404: {"description": "Task not found"}}


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


@router.patch(
    "/{task_id}",
    response_model=TaskOut,
    responses={**NOT_FOUND, 422: {"description": "Validation error"}},
)
async def update_task(task_id: ID, payload: TaskUpdate, session: DBSession):
    task = await get_or_404(session, Task, task_id, "Task")
    data = payload.model_dump(exclude_unset=True)
    if "project_id" in data:
        await ensure_exists(session, Project, data["project_id"], "Project")
    if data.get("assignee_id") is not None:
        await ensure_exists(session, User, data["assignee_id"], "Assignee")
    for field, value in data.items():
        setattr(task, field, value)
    await session.commit()
    await session.refresh(task)
    return task


@router.delete(
    "/{task_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND
)
async def delete_task(task_id: ID, session: DBSession):
    task = await get_or_404(session, Task, task_id, "Task")
    await session.delete(task)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
