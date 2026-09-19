FROM python:3.12-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip uv

COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --locked --no-install-project

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "src/main.py"]