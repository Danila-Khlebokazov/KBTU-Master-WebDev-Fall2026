FROM python:3.12-slim-trixie

RUN pip install --upgrade pip && pip install uv

WORKDIR /app

COPY uv.lock pyproject.toml ./

RUN uv sync --no-dev --locked

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

CMD ["python", "src/main.py"]