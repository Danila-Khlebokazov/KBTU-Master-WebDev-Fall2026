from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer

from app.models import Role

Money = Annotated[
    Decimal,
    Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Positive amount in KZT, up to 2 decimal places",
        examples=[4500.5],
    ),
    PlainSerializer(float, return_type=float),
]
HexColor = Annotated[
    str,
    Field(pattern=r"^#[0-9a-fA-F]{6}$", description="Hex color `#RRGGBB`", examples=["#22c55e"]),
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str = Field(description="Human-readable message", examples=["Expense not found"])


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"email": "student@example.com", "full_name": "John Doe", "password": "secret123"}
            ]
        }
    )

    email: EmailStr = Field(description="Unique email, used as login")
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=72, description="6-72 characters")


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "admin@example.com", "password": "admin12345"}]}
    )

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str = Field(description="JWT; send as `Authorization: Bearer <token>`")
    token_type: str = Field(default="bearer", examples=["bearer"])
    expires_in: int = Field(description="Token lifetime in seconds", examples=[3600])


# ---------- Users ----------
class UserRead(ORMModel):
    id: int = Field(examples=[2])
    email: EmailStr = Field(examples=["aruzhan@example.com"])
    full_name: str = Field(examples=["Aruzhan Nurlanovna"])
    role: Role = Field(description="`user` or `admin`")
    is_active: bool = Field(description="Disabled users cannot log in")
    created_at: datetime


class UserUpdate(BaseModel):
    """Partial update: only the provided fields are changed."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"role": "admin"}]})

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: Role | None = None
    is_active: bool | None = None


# ---------- Categories ----------
class CategoryBase(BaseModel):
    name: str = Field(
        min_length=1, max_length=100, description="Unique (case-insensitive)", examples=["Food"]
    )
    color: HexColor = "#6366f1"


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryRead(ORMModel, CategoryBase):
    id: int = Field(examples=[1])


# ---------- Expenses ----------
class ExpenseBase(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Groceries at Magnum",
                    "amount": 12450.75,
                    "spent_on": "2026-10-12",
                    "note": "Paid with Kaspi Gold",
                    "category_id": 1,
                }
            ]
        }
    )

    title: str = Field(min_length=1, max_length=200, description="What the money was spent on")
    amount: Money
    spent_on: date = Field(description="Date of the expense (`YYYY-MM-DD`)")
    note: str | None = Field(default=None, max_length=2000, description="Optional comment")
    category_id: int | None = Field(
        default=None, description="ID of an existing category; `null` = uncategorized"
    )


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(ExpenseBase):
    """Full replacement of the expense fields."""


class ExpenseOwner(ORMModel):
    id: int
    email: EmailStr
    full_name: str


class ExpenseRead(ORMModel, ExpenseBase):
    model_config = ConfigDict(from_attributes=True, json_schema_extra={})

    id: int = Field(examples=[42])
    owner: ExpenseOwner = Field(description="User who owns the expense")
    category: CategoryRead | None
    created_at: datetime
    updated_at: datetime


class ExpenseList(BaseModel):
    items: list[ExpenseRead] = Field(description="Current page, newest first")
    total: int = Field(description="Total number of matching expenses", examples=[235])
    limit: int = Field(examples=[20])
    offset: int = Field(examples=[0])


class CategoryTotal(BaseModel):
    category_id: int | None = Field(description="`null` for uncategorized expenses")
    name: str = Field(examples=["Food"])
    color: str = Field(examples=["#f97316"])
    total: float = Field(description="Sum of amounts", examples=[154300.0])
    count: int = Field(description="Number of expenses", examples=[37])


class ExpenseSummary(BaseModel):
    total: float = Field(description="Sum of all matching expenses", examples=[412000.5])
    count: int = Field(examples=[96])
    by_category: list[CategoryTotal] = Field(description="Sorted by total, descending")
