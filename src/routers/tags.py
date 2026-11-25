from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import DBSession, Tag, Task, commit_or_409, get_or_404, task_tags
from dependencies import AUTH_RESPONSES, CurrentUser
from schemas import ID, TagCreate, TagOut, TagUpdate, TaskOut

router = APIRouter(prefix="/tags", tags=["tags"])

NOT_FOUND = {404: {"description": "Tag not found"}}
CONFLICT = {409: {"description": "Tag with this name already exists"}}
DUPLICATE = "Tag with this name already exists"


async def resolve_tags(session: AsyncSession, tag_ids: list[int]) -> list[Tag]:
    """Load tags by ids for a task; 422 if any id does not exist."""
    if not tag_ids:
        return []
    tags = (await session.scalars(select(Tag).where(Tag.id.in_(tag_ids)))).all()
    missing = sorted(set(tag_ids) - {t.id for t in tags})
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Tags {missing} do not exist"
        )
    return list(tags)


async def ensure_unique_name(
    session: AsyncSession, name: str, exclude_id: int | None = None
) -> None:
    query = select(Tag.id).where(Tag.name == name)
    if exclude_id is not None:
        query = query.where(Tag.id != exclude_id)
    if await session.scalar(query) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)


@router.get("", response_model=list[TagOut])
async def list_tags(session: DBSession):
    return (await session.scalars(select(Tag).order_by(Tag.name))).all()


@router.get("/{tag_id}", response_model=TagOut, responses=NOT_FOUND)
async def get_tag(tag_id: ID, session: DBSession):
    return await get_or_404(session, Tag, tag_id, "Tag")


@router.get("/{tag_id}/tasks", response_model=list[TaskOut], responses=NOT_FOUND)
async def list_tag_tasks(tag_id: ID, session: DBSession):
    await get_or_404(session, Tag, tag_id, "Tag")
    result = await session.scalars(
        select(Task)
        .join(task_tags, task_tags.c.task_id == Task.id)
        .where(task_tags.c.tag_id == tag_id)
        .order_by(Task.id)
    )
    return result.all()


@router.post(
    "",
    response_model=TagOut,
    status_code=status.HTTP_201_CREATED,
    responses={**AUTH_RESPONSES, **CONFLICT},
)
async def create_tag(payload: TagCreate, _: CurrentUser, session: DBSession):
    await ensure_unique_name(session, payload.name)
    tag = Tag(**payload.model_dump())
    session.add(tag)
    await commit_or_409(session, DUPLICATE)
    await session.refresh(tag)
    return tag


@router.put(
    "/{tag_id}",
    response_model=TagOut,
    responses={**AUTH_RESPONSES, **NOT_FOUND, **CONFLICT},
)
async def replace_tag(
    tag_id: ID, payload: TagCreate, _: CurrentUser, session: DBSession
):
    return await _update(session, tag_id, payload.model_dump())


@router.patch(
    "/{tag_id}",
    response_model=TagOut,
    responses={**AUTH_RESPONSES, **NOT_FOUND, **CONFLICT},
)
async def update_tag(
    tag_id: ID, payload: TagUpdate, _: CurrentUser, session: DBSession
):
    return await _update(session, tag_id, payload.model_dump(exclude_unset=True))


async def _update(session: AsyncSession, tag_id: int, data: dict) -> Tag:
    tag = await get_or_404(session, Tag, tag_id, "Tag")
    if "name" in data:
        await ensure_unique_name(session, data["name"], exclude_id=tag_id)
    for field, value in data.items():
        setattr(tag, field, value)
    await commit_or_409(session, DUPLICATE)
    await session.refresh(tag)
    return tag


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**AUTH_RESPONSES, **NOT_FOUND},
)
async def delete_tag(tag_id: ID, _: CurrentUser, session: DBSession):
    """Delete a tag; it is removed from all tasks (DB cascade on task_tags)."""
    tag = await get_or_404(session, Tag, tag_id, "Tag")
    await session.delete(tag)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
