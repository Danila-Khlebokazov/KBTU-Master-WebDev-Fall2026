from datetime import UTC, datetime

from fastapi import FastAPI

simple_app = FastAPI(description="Simple FastAPI app from HW1")


@simple_app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(tz=UTC).isoformat()}


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        simple_app,
        host=os.environ.get("SERVICE_HOST", "localhost"),
        port=int(os.environ.get("SERVICE_PORT", 8000)),
        loop="uvloop",
        http="httptools",
    )
