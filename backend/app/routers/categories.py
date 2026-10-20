from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status
from sqlalchemy import func, select

from app.deps import FORBIDDEN, UNAUTHORIZED, AdminUser, CurrentUser, SessionDep
from app.models import Category
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate, Message

router = APIRouter(prefix="/categories", tags=["Categories"], responses=UNAUTHORIZED)

NOT_FOUND = {404: {"model": Message, "description": "Category not found"}}
CONFLICT = {409: {"model": Message, "description": "Category name already exists"}}

CategoryId = Annotated[int, Path(description="Category ID", examples=[1])]


async def _get_category(session: SessionDep, category_id: int) -> Category:
    category = await session.get(Category, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    return category


async def _ensure_unique_name(session: SessionDep, name: str, exclude_id: int | None = None):
    stmt = select(Category.id).where(func.lower(Category.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    if await session.scalar(stmt):
        raise HTTPException(status.HTTP_409_CONFLICT, "Category name already exists")


@router.get("", response_model=list[CategoryRead], summary="List categories")
async def list_categories(_: CurrentUser, session: SessionDep) -> list[Category]:
    """All categories sorted by name. Used to fill category dropdowns in the UI."""
    return list(await session.scalars(select(Category).order_by(Category.name)))


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Get category by ID",
    responses=NOT_FOUND,
)
async def get_category(category_id: CategoryId, _: CurrentUser, session: SessionDep) -> Category:
    return await _get_category(session, category_id)


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    responses=FORBIDDEN | CONFLICT,
)
async def create_category(data: CategoryCreate, _: AdminUser, session: SessionDep) -> Category:
    """Create a shared category. Names are unique (case-insensitive)."""
    await _ensure_unique_name(session, data.name)
    category = Category(**data.model_dump())
    session.add(category)
    await session.commit()
    return category


@router.put(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Update category",
    responses=FORBIDDEN | NOT_FOUND | CONFLICT,
)
async def update_category(
    category_id: CategoryId, data: CategoryUpdate, _: AdminUser, session: SessionDep
) -> Category:
    """Rename or recolor a category."""
    category = await _get_category(session, category_id)
    await _ensure_unique_name(session, data.name, exclude_id=category_id)
    for field, value in data.model_dump().items():
        setattr(category, field, value)
    await session.commit()
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete category",
    responses=FORBIDDEN | NOT_FOUND,
)
async def delete_category(category_id: CategoryId, _: AdminUser, session: SessionDep) -> Response:
    """Delete a category. Its expenses are kept and become uncategorized
    (`ON DELETE SET NULL`)."""
    category = await _get_category(session, category_id)
    await session.delete(category)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
