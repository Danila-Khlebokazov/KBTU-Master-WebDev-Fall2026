from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine
from app.routers import criminals, hunts
from app.seed import seed_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    await seed_data()
    yield
    await engine.dispose()


app = FastAPI(
    title="Space Bounty Hunters API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(criminals.router, prefix="/api")
app.include_router(hunts.router, prefix="/api")


@app.get("/api/health", tags=["Health"])
async def health() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok"}
