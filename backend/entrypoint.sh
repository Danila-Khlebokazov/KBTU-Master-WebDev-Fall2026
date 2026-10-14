#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API on ${APP_HOST:-0.0.0.0}:${APP_PORT:-8000}"
exec uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}" --proxy-headers
