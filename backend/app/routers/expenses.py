from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response, status
from sqlalchemy import Select, func, select

from app.deps import UNAUTHORIZED, CurrentUser, SessionDep
from app.models import Category, Expense, Role, User
from app.schemas import (
    CategoryTotal,
    ExpenseCreate,
    ExpenseList,
    ExpenseRead,
    ExpenseSummary,
    ExpenseUpdate,
    Message,
)

router = APIRouter(prefix="/expenses", tags=["Expenses"], responses=UNAUTHORIZED)

NOT_FOUND = {404: {"model": Message, "description": "Expense not found or belongs to another user"}}
BAD_CATEGORY = {422: {"description": "Validation error or `category_id` does not exist"}}

ExpenseId = Annotated[int, Path(description="Expense ID", examples=[1])]
DateFrom = Annotated[
    date | None, Query(description="Include expenses on or after this date (`YYYY-MM-DD`)")
]
DateTo = Annotated[
    date | None, Query(description="Include expenses on or before this date (`YYYY-MM-DD`)")
]


def _scope(stmt: Select, user: User, owner_id: int | None) -> Select:
    """Regular users only see their own expenses; admins see all (optionally filtered by owner)."""
    if user.role != Role.ADMIN:
        return stmt.where(Expense.owner_id == user.id)
    if owner_id is not None:
        return stmt.where(Expense.owner_id == owner_id)
    return stmt


def _filters(
    stmt: Select,
    category_id: int | None,
    date_from: date | None,
    date_to: date | None,
    q: str | None = None,
) -> Select:
    if category_id is not None:
        stmt = stmt.where(Expense.category_id == category_id)
    if date_from is not None:
        stmt = stmt.where(Expense.spent_on >= date_from)
    if date_to is not None:
        stmt = stmt.where(Expense.spent_on <= date_to)
    if q:
        stmt = stmt.where(Expense.title.ilike(f"%{q}%"))
    return stmt


async def _get_expense(session: SessionDep, expense_id: int, user: User) -> Expense:
    expense = await session.get(Expense, expense_id)
    # Return 404 (not 403) for foreign expenses so their existence is not leaked
    if expense is None or (user.role != Role.ADMIN and expense.owner_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    return expense


async def _ensure_category(session: SessionDep, category_id: int | None) -> None:
    if category_id is not None and await session.get(Category, category_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Category does not exist")


@router.get("", response_model=ExpenseList, summary="List expenses (paginated, filterable)")
async def list_expenses(
    user: CurrentUser,
    session: SessionDep,
    category_id: Annotated[int | None, Query(description="Filter by category ID")] = None,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    q: Annotated[
        str | None, Query(max_length=100, description="Case-insensitive search in title")
    ] = None,
    owner_id: Annotated[
        int | None, Query(description="Admin only: show expenses of one user")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
) -> ExpenseList:
    """Return a page of expenses sorted by date (newest first) plus the `total` count
    for pagination. Regular users get only their own expenses; admins get everyone's
    and may narrow the list with `owner_id`. All filters are optional and combinable."""
    base = _filters(_scope(select(Expense), user, owner_id), category_id, date_from, date_to, q)
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = await session.scalars(
        base.order_by(Expense.spent_on.desc(), Expense.id.desc()).limit(limit).offset(offset)
    )
    return ExpenseList(
        items=[ExpenseRead.model_validate(e) for e in rows.unique()],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=ExpenseSummary, summary="Totals grouped by category")
async def expense_summary(
    user: CurrentUser,
    session: SessionDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
) -> ExpenseSummary:
    """Total amount and number of expenses per category for the given period
    (all time if no dates). Powers the dashboard. Admins get totals across all users."""
    stmt = (
        select(
            Category.id,
            Category.name,
            Category.color,
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(Expense.id),
        )
        .select_from(Expense)
        .outerjoin(Category, Expense.category_id == Category.id)
        .group_by(Category.id, Category.name, Category.color)
        .order_by(func.sum(Expense.amount).desc())
    )
    stmt = _filters(_scope(stmt, user, None), None, date_from, date_to)
    rows = (await session.execute(stmt)).all()
    by_category = [
        CategoryTotal(
            category_id=cid,
            name=name or "Uncategorized",
            color=color or "#94a3b8",
            total=float(total),
            count=count,
        )
        for cid, name, color, total, count in rows
    ]
    return ExpenseSummary(
        total=round(sum(c.total for c in by_category), 2),
        count=sum(c.count for c in by_category),
        by_category=by_category,
    )


@router.get(
    "/{expense_id}", response_model=ExpenseRead, summary="Get expense by ID", responses=NOT_FOUND
)
async def get_expense(expense_id: ExpenseId, user: CurrentUser, session: SessionDep) -> Expense:
    """Single expense with its category and owner. Users can read only their own."""
    return await _get_expense(session, expense_id, user)


@router.post(
    "",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an expense",
    responses=BAD_CATEGORY,
)
async def create_expense(data: ExpenseCreate, user: CurrentUser, session: SessionDep) -> Expense:
    """Create an expense owned by the current user."""
    await _ensure_category(session, data.category_id)
    expense = Expense(**data.model_dump(), owner_id=user.id)
    session.add(expense)
    await session.commit()
    await session.refresh(expense)
    return expense


@router.put(
    "/{expense_id}",
    response_model=ExpenseRead,
    summary="Update an expense",
    responses=NOT_FOUND | BAD_CATEGORY,
)
async def update_expense(
    expense_id: ExpenseId, data: ExpenseUpdate, user: CurrentUser, session: SessionDep
) -> Expense:
    """Replace all editable fields of an expense. Owner or admin only."""
    expense = await _get_expense(session, expense_id, user)
    await _ensure_category(session, data.category_id)
    for field, value in data.model_dump().items():
        setattr(expense, field, value)
    await session.commit()
    await session.refresh(expense)
    return expense


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
    responses=NOT_FOUND,
)
async def delete_expense(expense_id: ExpenseId, user: CurrentUser, session: SessionDep) -> Response:
    """Permanently delete an expense. Owner or admin only. Returns no body."""
    expense = await _get_expense(session, expense_id, user)
    await session.delete(expense)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
