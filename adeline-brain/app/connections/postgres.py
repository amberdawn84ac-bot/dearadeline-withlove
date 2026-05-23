"""
PostgreSQL Connection — SQLAlchemy Async Sessions

Provides get_db_session() dependency for FastAPI endpoints that need
to interact with PostgreSQL directly (e.g., StandardsMapper queries).

Uses the same DSN as pgvector_client for consistency.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import ASYNC_POSTGRES_DSN

logger = logging.getLogger(__name__)

# Create engine and session factory
_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        _engine = create_async_engine(
            ASYNC_POSTGRES_DSN,
            echo=False,
            connect_args={"ssl": ctx, "statement_cache_size": 0},
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async SQLAlchemy session.
    
    Usage:
        @router.post("/example")
        async def example(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(...)
    """
    session = _get_session_factory()()
    try:
        yield session
    finally:
        await session.close()


async def init_postgres():
    """Initialize connection (called during app startup)."""
    engine = _get_engine()
    from sqlalchemy import text
    async with engine.begin() as conn:
        # Verify connection
        await conn.execute(text("SELECT 1"))
    logger.info("[Postgres] Connected")
