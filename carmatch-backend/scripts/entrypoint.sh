#!/bin/sh
set -e
echo "[entrypoint] Starting migrations..."
python -m alembic upgrade head
echo "[entrypoint] Migrations OK, starting uvicorn..."
exec python -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
