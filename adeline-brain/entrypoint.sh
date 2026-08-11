#!/bin/sh
set -e

_DB="${DIRECT_DATABASE_URL:-${POSTGRES_DSN:-$DATABASE_URL}}"
if [ -n "$_DB" ]; then
    echo "[entrypoint] Verifying initial Prisma migration state..."
    if python scripts/repair_initial_migration.py; then
        echo "[entrypoint] Initial migration is already resolved"
    else
        _REPAIR_STATUS=$?
        if [ "$_REPAIR_STATUS" -eq 42 ]; then
            echo "[entrypoint] Recording verified initial migration as applied..."
            HOME=/tmp DIRECT_DATABASE_URL="$_DB" DATABASE_URL="$_DB" prisma migrate resolve --applied 20260327192741_init_8_track_schema --schema /app/prisma/schema.prisma
        else
            echo "[entrypoint] Migration repair verification failed; refusing startup"
            exit "$_REPAIR_STATUS"
        fi
    fi
    echo "[entrypoint] Running Prisma migrations..."
    HOME=/tmp DIRECT_DATABASE_URL="$_DB" DATABASE_URL="$_DB" timeout 120 prisma migrate deploy --schema /app/prisma/schema.prisma
else
    echo "[entrypoint] No DATABASE_URL set — skipping Prisma migrate"
fi

# Run seeds if RUN_SEEDS env var is set (case-insensitive)
if [ "$RUN_SEEDS" = "true" ] || [ "$RUN_SEEDS" = "TRUE" ]; then
    echo "[entrypoint] Running knowledge graph seed..."
    python scripts/seed_knowledge_graph.py || { echo "[entrypoint] Knowledge graph seed failed - EXITING"; exit 1; }

    echo "[entrypoint] Running OAS standards seed (critical - loads all 3,043 standards)..."
    python scripts/seed_oas_standards.py || { echo "[entrypoint] OAS standards seed failed - EXITING"; exit 1; }

    echo "[entrypoint] Verifying OAS standards count..."
    python scripts/verify_oas_count.py || { echo "[entrypoint] OAS verification failed - EXITING"; exit 1; }

    echo "[entrypoint] Running scripture seed..."
    python scripts/seed_scripture.py || echo "[entrypoint] Scripture seed failed (non-fatal)"

    echo "[entrypoint] Running bookshelf seed..."
    python scripts/seed_bookshelf.py || echo "[entrypoint] Bookshelf seed failed (non-fatal)"

    echo "[entrypoint] Running Baker Creek seed..."
    python scripts/seed_baker_creek.py || echo "[entrypoint] Baker Creek seed failed (non-fatal)"

    echo "[entrypoint] Running Loewen seed..."
    python scripts/seed_loewen.py || echo "[entrypoint] Loewen seed failed (non-fatal)"

    echo "[entrypoint] Running science experiments seed..."
    python scripts/seed_science_experiments.py || echo "[entrypoint] Science experiments seed failed (non-fatal)"

    echo "[entrypoint] Seeds complete"
fi

echo "[entrypoint] Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 1 \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 120 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile - \
  "$@"
