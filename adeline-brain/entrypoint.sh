#!/bin/sh
set -e

_DB="${DIRECT_DATABASE_URL:-${POSTGRES_DSN:-$DATABASE_URL}}"
if [ -n "$_DB" ]; then
    echo "[entrypoint] Running Prisma migrations..."
    DIRECT_DATABASE_URL="$_DB" DATABASE_URL="$_DB" timeout 30 prisma migrate deploy --schema /app/prisma/schema.prisma || echo "[entrypoint] Prisma migrate failed (non-fatal)"
else
    echo "[entrypoint] No DATABASE_URL set — skipping Prisma migrate"
fi

# Run seeds if RUN_SEEDS env var is set
if [ "$RUN_SEEDS" = "true" ]; then
    echo "[entrypoint] Running curriculum seed..."
    python scripts/seed_curriculum.py || echo "[entrypoint] Curriculum seed failed"
    
    echo "[entrypoint] Running knowledge graph seed..."
    python scripts/seed_knowledge_graph.py || echo "[entrypoint] Knowledge graph seed failed"

    echo "[entrypoint] Running scripture seed..."
    python scripts/seed_scripture.py || echo "[entrypoint] Scripture seed failed"

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
