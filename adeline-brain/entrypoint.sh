#!/bin/sh
set -e

echo "[entrypoint] Running Prisma migrations..."
DATABASE_URL="${DIRECT_DATABASE_URL:-${POSTGRES_DSN:-$DATABASE_URL}}" prisma migrate deploy || echo "[entrypoint] Prisma migrate failed"

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

    echo "[entrypoint] Seeds complete"
fi

echo "[entrypoint] Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" "$@"
