#!/bin/sh
set -e

echo "[entrypoint] Running Prisma migrations..."
prisma migrate deploy 2>/dev/null || echo "[entrypoint] Prisma migrate skipped (client not configured or no migrations pending)"

# Run seeds if RUN_SEEDS env var is set
if [ "$RUN_SEEDS" = "true" ]; then
    echo "[entrypoint] Running curriculum seed..."
    python scripts/seed_curriculum.py || echo "[entrypoint] Curriculum seed failed"
    
    echo "[entrypoint] Running knowledge graph seed..."
    python scripts/seed_knowledge_graph.py || echo "[entrypoint] Knowledge graph seed failed"

    echo "[entrypoint] Running scripture seed..."
    python scripts/seed_scripture.py || echo "[entrypoint] Scripture seed failed"

    echo "[entrypoint] Seeds complete"
fi

echo "[entrypoint] Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" "$@"
