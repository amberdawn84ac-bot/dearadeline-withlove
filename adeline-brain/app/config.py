"""
Centralized configuration — single source of truth for connection strings.

Reads from environment variables with a clear priority chain.
In production (ADELINE_ENV=production), missing database credentials
cause an immediate startup failure instead of silent fallback.
"""
import os
import logging

logger = logging.getLogger(__name__)

# ── Environment ──────────────────────────────────────────────────────────────

ADELINE_ENV = os.getenv("ADELINE_ENV", "development")
IS_PRODUCTION = ADELINE_ENV == "production"

# ── Postgres DSN ─────────────────────────────────────────────────────────────
# Priority: POSTGRES_DSN > DATABASE_URL > DIRECT_DATABASE_URL > dev fallback

_DEV_FALLBACK_DSN = "postgresql://adeline:adeline_local_dev@postgres:5432/hippocampus"

POSTGRES_DSN = (
    os.getenv("POSTGRES_DSN")
    or os.getenv("DATABASE_URL")
    or os.getenv("DIRECT_DATABASE_URL")
    or (None if IS_PRODUCTION else _DEV_FALLBACK_DSN)
)

if POSTGRES_DSN is None:
    raise RuntimeError(
        "FATAL: No database DSN configured. "
        "Set POSTGRES_DSN, DATABASE_URL, or DIRECT_DATABASE_URL. "
        "Refusing to start in production without explicit credentials."
    )

if not IS_PRODUCTION and POSTGRES_DSN == _DEV_FALLBACK_DSN:
    logger.warning("[Config] Using development fallback DSN — set POSTGRES_DSN for production")

# Print DSN details (no password) so we can debug connection issues
# Using print() because logging isn't configured yet at import time
try:
    from urllib.parse import urlparse as _urlparse
    _parsed = _urlparse(POSTGRES_DSN)
    print(
        f"[Config] DSN: user={_parsed.username}, host={_parsed.hostname}, "
        f"port={_parsed.port}, db={_parsed.path}, "
        f"source={'POSTGRES_DSN' if os.getenv('POSTGRES_DSN') else 'DATABASE_URL' if os.getenv('DATABASE_URL') else 'DIRECT_DATABASE_URL' if os.getenv('DIRECT_DATABASE_URL') else 'fallback'}"
    )
    print(f"[Config] POSTGRES_DSN set: {bool(os.getenv('POSTGRES_DSN'))}, DATABASE_URL set: {bool(os.getenv('DATABASE_URL'))}")
except Exception as _e:
    print(f"[Config] DSN parse error: {_e}")

# Async variant for SQLAlchemy
ASYNC_POSTGRES_DSN = POSTGRES_DSN.replace("postgresql://", "postgresql+asyncpg://")

# ── Neo4j ────────────────────────────────────────────────────────────────────

NEO4J_URI = os.getenv("NEO4J_URI", "" if IS_PRODUCTION else "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "" if IS_PRODUCTION else "adeline_local_dev")

if IS_PRODUCTION and (not NEO4J_URI or not NEO4J_PASSWORD):
    raise RuntimeError(
        "FATAL: Neo4j credentials not configured. "
        "Set NEO4J_URI and NEO4J_PASSWORD. "
        "Refusing to start in production without explicit credentials."
    )

# ── Redis ────────────────────────────────────────────────────────────────────

UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "" if IS_PRODUCTION else "redis://localhost:6379/0")

# ── OpenAI ───────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if IS_PRODUCTION and not OPENAI_API_KEY:
    raise RuntimeError(
        "FATAL: OPENAI_API_KEY not set. Required for embeddings in production."
    )

# ── Auth (Supabase JWT) ──────────────────────────────────────────────────────
# SUPABASE_JWT_SECRET is required in production for token verification.
# In development, if unset, falls back to permissive header-based auth.

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

if IS_PRODUCTION and not SUPABASE_JWT_SECRET:
    raise RuntimeError(
        "FATAL: SUPABASE_JWT_SECRET not set. "
        "Required for JWT auth in production."
    )

# ── CORS ─────────────────────────────────────────────────────────────────────

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000")


# ── Shared DB connection helper ──────────────────────────────────────────────

async def get_db_conn():
    """Get an asyncpg connection with SSL for Supabase pooler compatibility."""
    import asyncpg
    import ssl as _ssl
    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    return await asyncpg.connect(POSTGRES_DSN, ssl=ctx)
