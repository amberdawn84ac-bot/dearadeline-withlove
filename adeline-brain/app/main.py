"""
adeline-brain — FastAPI Entry Point
The Intelligence Layer of Dear Adeline 2.0
"""
import json
import logging
import os

import openai
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.schemas.api_models import TRUTH_THRESHOLD
from app.connections.neo4j_client import neo4j_client
from app.connections.pgvector_client import hippocampus
from app.connections.bookshelf_search import bookshelf_search
from app.connections.redis_client import ping as redis_ping
from app.api.lessons import router as lessons_router
from app.api.opportunities import router as opportunities_router
from app.api.journal import router as journal_router
from app.api.transcripts import router as transcripts_router
from app.api.scaffold import router as scaffold_router
from app.api.daily_bread import router as daily_bread_router
from app.api.learning_records import router as learning_records_router
from app.api.students import router as students_router
from app.api.experiments import router as experiments_router
from app.api.activities import router as activities_router
from app.api.projects import router as projects_router
from app.api.subscriptions import router as subscriptions_router
from app.api.credits import router as credits_router
from app.api.bookshelf import router as bookshelf_router
from app.api.books import router as books_router
from app.api.registrar_reports import router as registrar_reports_router
from app.api.admin_tasks import router as admin_tasks_router
from app.api.admin_review import router as admin_review_router
from app.api.metrics import router as metrics_router
from app.api.reading_session import router as reading_session_router
from app.api.onboarding import router as onboarding_router
from app.api.parent import router as parent_router
from app.api.admin import router as admin_router
from app.api.learning_plan import router as learning_plan_router
from app.api.genui import router as genui_router
from app.api.realtime import router as realtime_router
from app.api.conversation import router as conversation_router
from app.api.animated_lessons import router as animated_lessons_router
from app.api.learning_path import router as learning_path_router
from app.connections.journal_store import journal_store
from app.connections.conversation_store import conversation_store
from app.jobs.seed_scheduler import startup_seed_scheduler, shutdown_seed_scheduler

from pythonjsonlogger import jsonlogger

def _configure_logging():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

_configure_logging()
logger = logging.getLogger(__name__)

_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
        send_default_pii=False,
    )
    logger.info("[adeline-brain] Sentry initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[adeline-brain] Starting up...")

    # Neo4j is optional — ZPD reasoning degrades but the app still works
    try:
        await neo4j_client.connect()
    except Exception as e:
        logger.warning(f"[adeline-brain] Neo4j unavailable — ZPD/graph features disabled: {e}")

    # DB connections are optional at startup so the app doesn't crash
    # if a service is temporarily unreachable
    try:
        await hippocampus.connect()
    except Exception as e:
        logger.warning(f"[adeline-brain] Hippocampus (pgvector) unavailable: {e}")

    try:
        await bookshelf_search.connect()
    except Exception as e:
        logger.warning(f"[adeline-brain] Bookshelf search unavailable: {e}")

    try:
        await journal_store.connect()
    except Exception as e:
        logger.warning(f"[adeline-brain] Journal store unavailable: {e}")

    try:
        await conversation_store.connect()
    except Exception as e:
        logger.warning(f"[adeline-brain] Conversation store unavailable: {e}")

    await startup_seed_scheduler()
    yield
    logger.info("[adeline-brain] Shutting down...")
    await shutdown_seed_scheduler()
    try:
        await bookshelf_search.disconnect()
    except Exception:
        pass
    try:
        await neo4j_client.close()
    except Exception:
        pass


# ── Rate limiter (Redis-backed; shared across Gunicorn workers + Railway replicas) ─
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],       # Global: 120 req/min per IP
    storage_uri=_REDIS_URL,
)


app = FastAPI(
    title="adeline-brain",
    description="Intelligence Layer — Dear Adeline 2.0 Truth-First K-12 AI Mentor",
    version="0.2.0",
    lifespan=lifespan,
    redirect_slashes=False,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Force HTTPS scheme when behind a TLS-terminating proxy (Railway, Vercel)
# This prevents FastAPI's redirect_slashes from generating http:// URLs
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class ForceHTTPSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # If behind a proxy that terminates TLS, trust the forwarded proto
        if request.headers.get("x-forwarded-proto") == "https":
            request.scope["scheme"] = "https"
        response = await call_next(request)
        return response

app.add_middleware(ForceHTTPSMiddleware)


from app.config import CORS_ORIGINS as _cors_env
_CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
# Always include Docker-internal UI hostname and production domain
for _required_origin in [
    "http://adeline-ui:3000",
    "https://dearadeline.co",
    "https://www.dearadeline.co",
]:
    if _required_origin not in _CORS_ORIGINS:
        _CORS_ORIGINS.append(_required_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lessons_router)
app.include_router(opportunities_router)
app.include_router(journal_router)
app.include_router(transcripts_router)
app.include_router(scaffold_router)
app.include_router(daily_bread_router)
app.include_router(learning_records_router)
app.include_router(students_router)
app.include_router(experiments_router)
app.include_router(activities_router)
app.include_router(projects_router)
app.include_router(subscriptions_router)
app.include_router(credits_router)
app.include_router(bookshelf_router)
app.include_router(books_router)
app.include_router(reading_session_router)
app.include_router(onboarding_router)
app.include_router(parent_router)
app.include_router(admin_router)
app.include_router(learning_plan_router)
app.include_router(genui_router)
app.include_router(books_router, prefix="/brain")
app.include_router(learning_plan_router, prefix="/brain")
app.include_router(genui_router, prefix="/brain")
app.include_router(registrar_reports_router, prefix="/brain")
app.include_router(admin_tasks_router, prefix="/brain")
app.include_router(admin_review_router, prefix="/brain")
app.include_router(metrics_router)
app.include_router(realtime_router)
app.include_router(conversation_router)
app.include_router(animated_lessons_router)
app.include_router(learning_path_router)


@app.get("/health")
async def health():
    """Health check with data population status."""
    from app.config import get_db_conn
    
    health_status = {
        "status": "alive",
        "service": "adeline-brain",
        "version": "0.2.0",
        "hippocampus_documents": 0,
        "neo4j_concepts": 0,
        "neo4j_tracks": 0,
        "books": 0,
    }
    
    # Check Hippocampus document count
    try:
        conn = await get_db_conn()
        result = await conn.fetchval('SELECT COUNT(*) FROM "HippocampusDocument"')
        health_status["hippocampus_documents"] = result
        await conn.close()
    except Exception as e:
        health_status["hippocampus_error"] = str(e)
    
    # Check Book count
    try:
        conn = await get_db_conn()
        result = await conn.fetchval('SELECT COUNT(*) FROM "Book"')
        health_status["books"] = result
        await conn.close()
    except Exception as e:
        health_status["books_error"] = str(e)
    
    # Check Neo4j concept/track counts
    try:
        if neo4j_client.driver:
            async with neo4j_client.driver.session() as session:
                concept_result = await session.run("MATCH (c:Concept) RETURN count(c) as count")
                concept_record = await concept_result.single()
                health_status["neo4j_concepts"] = concept_record["count"] if concept_record else 0

                track_result = await session.run("MATCH (t:Track) RETURN count(t) as count")
                track_record = await track_result.single()
                health_status["neo4j_tracks"] = track_record["count"] if track_record else 0
    except Exception as e:
        health_status["neo4j_error"] = str(e)

    # Check Redis connectivity
    try:
        redis_ok = await redis_ping()
        health_status["redis"] = "ok" if redis_ok else "unreachable"
    except Exception as e:
        health_status["redis"] = f"error: {e}"

    return health_status


@app.get("/health/truth")
async def health_truth():
    """
    Truth Engine health check.
    Embeds a Douglass query and runs similarity search against the Hippocampus.
    """
    INVESTIGATING_FLOOR = 0.65
    query = "How did Frederick Douglass learn to read through the help of white boys in the street?"

    try:
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = await client.embeddings.create(model="text-embedding-3-small", input=query)
        query_embedding = resp.data[0].embedding
    except Exception as e:
        return {"status": "EMBEDDING_UNAVAILABLE", "error": str(e)}

    results = await hippocampus.similarity_search(
        query_embedding=query_embedding, track="TRUTH_HISTORY", top_k=1
    )

    if not results:
        return {"status": "CORPUS_EMPTY", "message": "Run seed_curriculum.py first.", "score": None}

    top = results[0]
    score = float(top["similarity_score"])

    if score >= TRUTH_THRESHOLD:
        verdict, status = "VERIFIED", "TRUTH_ENGINE_ONLINE"
    elif score >= INVESTIGATING_FLOOR:
        verdict, status = "INVESTIGATING", "TRUTH_ENGINE_ONLINE"
    else:
        verdict, status = "ARCHIVE_SILENT", "CORPUS_COLD"

    return {
        "status": status,
        "verdict": verdict,
        "score": round(score, 4),
        "threshold": TRUTH_THRESHOLD,
        "source": top["source_title"],
        "citation": {
            "author": top.get("citation_author"),
            "year": top.get("citation_year"),
            "archive": top.get("citation_archive_name"),
        },
    }


@app.get("/tracks")
async def list_tracks():
    from app.schemas.api_models import Track
    return {
        "tracks": [
            {"id": t.value, "label": t.value.replace("_", " ").title()}
            for t in Track
        ]
    }
