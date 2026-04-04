"""
adeline-brain — FastAPI Entry Point
The Intelligence Layer of Dear Adeline 2.0
"""
import logging
import os

import openai
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas.api_models import TRUTH_THRESHOLD
from app.connections.neo4j_client import neo4j_client
from app.connections.pgvector_client import hippocampus
from app.connections.bookshelf_search import bookshelf_search
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
from app.api.onboarding import router as onboarding_router
from app.connections.journal_store import journal_store
from app.jobs.seed_scheduler import startup_seed_scheduler, shutdown_seed_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[adeline-brain] Starting up...")
    await neo4j_client.connect()
    await hippocampus.connect()
    await bookshelf_search.connect()
    await journal_store.connect()
    await startup_seed_scheduler()
    yield
    logger.info("[adeline-brain] Shutting down...")
    await shutdown_seed_scheduler()
    await bookshelf_search.disconnect()
    await neo4j_client.close()


app = FastAPI(
    title="adeline-brain",
    description="Intelligence Layer — Dear Adeline 2.0 Truth-First K-12 AI Mentor",
    version="0.2.0",
    lifespan=lifespan,
)

_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
# Always include Docker-internal UI hostname
if "http://adeline-ui:3000" not in _CORS_ORIGINS:
    _CORS_ORIGINS.append("http://adeline-ui:3000")

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
app.include_router(onboarding_router)


@app.get("/health")
async def health():
    return {"status": "alive", "service": "adeline-brain", "version": "0.2.0"}


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
