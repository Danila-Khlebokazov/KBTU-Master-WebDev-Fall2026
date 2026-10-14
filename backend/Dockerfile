FROM python:3.12-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_PORT=8000 
# default env for application

WORKDIR /app
RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /app/.venv /app/.venv
COPY --chown=appuser:appuser alembic.ini entrypoint.sh ./
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser app ./app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import os, urllib.request as u; u.urlopen('http://localhost:' + os.getenv('APP_PORT', '8000') + '/api/health', timeout=2)" || exit 1

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
