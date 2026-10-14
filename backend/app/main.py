from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db import engine
from app.routers import auth, categories, expenses, users
from app.seed import seed_demo_data, seed_initial_data
from app.settings import get_settings

settings = get_settings()

API_DESCRIPTION = """
**Spendwise** is a personal expense tracker. Users record their daily expenses, group them
by category and see where their money goes. Administrators manage the shared category
list and user accounts.

## Authentication

The API uses **JWT bearer tokens**.

1. Create an account with `POST /api/auth/register` (or use a demo account below).
2. Call `POST /api/auth/login` and copy `access_token` from the response.
3. Click **Authorize** (top right) and paste the token.
4. `POST /api/auth/logout` revokes the token on the server; it can no longer be used.

## Roles

| Role | Permissions |
|---|---|
| `user` | CRUD on **own** expenses, read categories |
| `admin` | All of the above + CRUD on **all** expenses, categories and users |

## Demo accounts

| Email | Password | Role |
|---|---|---|
| `admin@example.com` | `admin12345` | admin |
| `aruzhan@example.com` | `demo12345` | user |
| `timur@example.com` | `demo12345` | user |
| `dana@example.com` | `demo12345` | user |
| `alikhan@example.com` | `demo12345` | user |
| `madina@example.com` | `demo12345` | user |

Defaults; can be changed with `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `DEMO_USER_PASSWORD`.

## Errors

All errors return JSON `{"detail": "..."}`. Validation errors (`422`) return a list of
`{"loc", "msg", "type"}` objects in `detail`.

| Code | Meaning |
|---|---|
| `401` | Missing, invalid, expired or revoked token |
| `403` | Authenticated, but the action requires the `admin` role |
| `404` | Resource not found (also for another user's expense) |
| `409` | Conflict: duplicate email or category name |
| `422` | Request validation failed |
"""

TAGS_METADATA = [
    {"name": "Auth", "description": "Registration, login, logout and the current user profile."},
    {
        "name": "Expenses",
        "description": "Main resource. Users see only their own expenses; admins see everyone's.",
    },
    {
        "name": "Categories",
        "description": "Shared expense categories. Any authenticated user can read; only admins "
        "can create, update or delete.",
    },
    {"name": "Users (admin)", "description": "User management. Admin role required."},
    {"name": "Health", "description": "Service and database health check used by Docker."},
]


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    database: str = Field(examples=["ok"])
    timestamp: datetime


@asynccontextmanager
async def lifespan(_: FastAPI):
    await seed_initial_data()
    if settings.SEED_DEMO_DATA:
        await seed_demo_data()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    summary="REST API for tracking personal expenses (FastAPI + PostgreSQL + JWT).",
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    contact={"name": "Danila Khlebokazov", "email": "danilik_2003@mail.ru"},
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

for router in (auth.router, expenses.router, categories.router, users.router):
    app.include_router(router, prefix="/api")


@app.get(
    "/api/health",
    tags=["Health"],
    response_model=HealthResponse,
    summary="Liveness and database check",
)
async def health() -> HealthResponse:
    """Runs `SELECT 1` against PostgreSQL. Used by the Docker `HEALTHCHECK`."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="ok", timestamp=datetime.now(UTC))
