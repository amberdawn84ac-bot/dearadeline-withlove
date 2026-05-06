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
    logger.warning(
        "[Config] No database DSN configured — DB-dependent features will fail. "
        "Set POSTGRES_DSN, DATABASE_URL, or DIRECT_DATABASE_URL."
    )
    POSTGRES_DSN = "postgresql://placeholder:placeholder@localhost:5432/placeholder"

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
    logger.warning(
        "[Config] Neo4j credentials not configured — ZPD/graph features will be disabled. "
        "Set NEO4J_URI and NEO4J_PASSWORD to enable full functionality."
    )

# ── Redis ────────────────────────────────────────────────────────────────────

UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "" if IS_PRODUCTION else "redis://localhost:6379/0")

# ── OpenAI ───────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if IS_PRODUCTION and not OPENAI_API_KEY:
    logger.warning(
        "[Config] OPENAI_API_KEY not set — embedding and lesson generation will fail. "
        "Set OPENAI_API_KEY in Railway environment variables."
    )

# ── Gemini (multimodal synthesis — 30x cheaper than Claude for JSON extraction) ──
# Uses the OpenAI-compatible endpoint so no new dependencies needed.
# Falls back to Claude if GEMINI_API_KEY is not set.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# ── Auth (Supabase JWT) ──────────────────────────────────────────────────────
# Primary: JWKS (ES256) — public key fetched from Supabase's well-known endpoint.
# Fallback: SUPABASE_JWT_SECRET (HS256) — for legacy tokens or local dev.

SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "gyxowttfwqbajoapfebf")
SUPABASE_JWKS_URL = f"https://{SUPABASE_PROJECT_REF}.supabase.co/auth/v1/.well-known/jwks.json"
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# ── Internal API Key (server-to-server calls from lesson pipeline) ──────────
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key-not-for-production")

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
    return await asyncpg.connect(POSTGRES_DSN, ssl=ctx, statement_cache_size=0)
