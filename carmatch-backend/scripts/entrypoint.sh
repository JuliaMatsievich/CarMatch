#!/bin/sh
set -e
# stdout/stderr сразу в лог (без буфера)
echo "[entrypoint] Starting migrations..."
python -m alembic upgrade head 2>&1
echo "[entrypoint] Migrations OK, starting uvicorn..."
exec python -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
