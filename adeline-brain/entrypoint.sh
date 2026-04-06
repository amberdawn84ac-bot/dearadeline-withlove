#!/bin/sh
set -e

echo "[entrypoint] Running Prisma migrations..."
prisma migrate deploy 2>/dev/null || echo "[entrypoint] Prisma migrate skipped (client not configured or no migrations pending)"

echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
