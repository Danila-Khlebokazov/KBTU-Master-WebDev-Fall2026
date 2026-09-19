from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from db import DBManager, User, UserCreateModel, get_db_session
from settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_manager = DBManager(settings.POSTGRES_URL)
    await db_manager.connect()
    try:
        yield {
            "db_manager": db_manager,
        }
    finally:
        await db_manager.disconnect()


simple_app = FastAPI(description="Simple FastAPI app from HW2", lifespan=lifespan)


@simple_app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(tz=UTC).isoformat()}


@simple_app.get("/users")
async def get_users(db_session: Annotated[AsyncSession, Depends(get_db_session)]):
    users = await db_session.execute(select(User))
    return users.scalars().all()


@simple_app.post("/users")
async def create_user(
    user: UserCreateModel, db_session: Annotated[AsyncSession, Depends(get_db_session)]
):
    created_user = User(email=user.email, name=user.name)
    db_session.add(created_user)
    await db_session.commit()
    await db_session.refresh(created_user)
    return created_user


@simple_app.get("/users/{user_id}")
async def get_user(
    user_id: int, db_session: Annotated[AsyncSession, Depends(get_db_session)]
):
    user = await db_session.get(User, user_id)
    if user is None:
        return JSONResponse(status_code=404, content={"message": "User not found"})
    return user


@simple_app.delete("/users/{user_id}")
async def delete_user(
    user_id: int, db_session: Annotated[AsyncSession, Depends(get_db_session)]
):
    user = await db_session.get(User, user_id)
    if user is None:
        return JSONResponse(status_code=404, content={"message": "User not found"})
    await db_session.delete(user)
    await db_session.commit()
    return JSONResponse(status_code=204, content={})


@simple_app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "details": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        simple_app,
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        loop="uvloop",
        http="httptools",
    )
