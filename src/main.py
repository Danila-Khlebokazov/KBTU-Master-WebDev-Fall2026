from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from starlette.responses import JSONResponse

from db import DBManager
from routers import projects, tasks, users
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


simple_app = FastAPI(
    title="Task Tracker API",
    description="HW3: REST API with Users, Projects and Tasks",
    lifespan=lifespan,
)
simple_app.include_router(users.router)
simple_app.include_router(projects.router)
simple_app.include_router(tasks.router)


@simple_app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(tz=UTC).isoformat()}


@simple_app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Don't leak internals to the client
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        simple_app,
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        loop="uvloop",
        http="httptools",
    )
