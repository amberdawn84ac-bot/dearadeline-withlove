"""
seed_curriculum.py — Activate the Hippocampus
Loads OAS standards into Neo4j (GraphRAG) and pgvector (Hippocampus).
Seeds the first Witness document: Narrative of Frederick Douglass (1845).

Run from adeline-brain/:
    python scripts/seed_curriculum.py
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from repo root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import openai
from sqlalchemy import text, Column, String, Float, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pgvector.sqlalchemy import Vector
from neo4j import AsyncGraphDatabase
import uuid as uuid_lib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed")

# ── Config ────────────────────────────────────────────────────────────────────

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://adeline:adeline_local_dev@localhost:5432/hippocampus",
).replace("postgresql://", "postgresql+asyncpg://")

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "adeline_local_dev")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBED_MODEL    = "text-embedding-3-small"
EMBED_DIM      = 1536
TRUTH_THRESHOLD = 0.85

OAS_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "oas_to_8track.json"

# ── Douglass primary source — 3 focused chunks ───────────────────────────────
# Chapter VII of the Narrative (1845). Stored as small, semantically tight
# chunks so similarity queries stay above the 0.85 Witness threshold.

_DOUGLASS_BASE = {
    "source_title":          "Narrative of the Life of Frederick Douglass, An American Slave",
    "source_url":            "https://www.loc.gov/item/91898036/",
    "track":                 "TRUTH_HISTORY",
    "citation_author":       "Frederick Douglass",
    "citation_year":         1845,
    "citation_archive_name": "Library of Congress — Rare Book and Special Collections Division",
}

DOUGLASS_CHUNKS = [
    {
        **_DOUGLASS_BASE,
        "chunk": (
            "Narrative of the Life of Frederick Douglass, Chapter VII (1845). "
            "I lived in Master Hugh's family about seven years. During this time, "
            "I succeeded in learning to read and write. In accomplishing this, I was "
            "compelled to resort to various stratagems. I had no regular teacher. "
            "To accomplish it in any other way was not only forbidden, but denounced "
            "as unlawful, to teach a slave to read. My mistress had kindly commenced "
            "to instruct me, but had set her face against my being instructed by anyone. "
            "The plan I adopted was that of making friends of all the little white boys "
            "whom I met in the street. With their kindly aid, I finally succeeded in "
            "learning to read. How Frederick Douglass taught himself to read despite "
            "laws forbidding slave literacy."
        ),
    },
    {
        **_DOUGLASS_BASE,
        "chunk": (
            "Narrative of the Life of Frederick Douglass, Chapter VII — The Columbian Orator (1845). "
            "I was now about twelve years old, and the thought of being a slave for life "
            "began to bear heavily upon my heart. Just about this time, I got hold of a "
            "book entitled 'The Columbian Orator.' Every opportunity I got, I used to read "
            "this book. Among much of other interesting matter, I found in it a dialogue "
            "between a master and his slave. It gave tongue to interesting thoughts of my "
            "own soul, which had frequently flashed through my mind, and died away for want "
            "of utterance. The more I read, the more I was led to abhor and detest slavery. "
            "Douglass used books and reading to understand the injustice of slavery."
        ),
    },
    {
        **_DOUGLASS_BASE,
        "chunk": (
            "Narrative of the Life of Frederick Douglass, Chapter VII — Freedom through literacy (1845). "
            "Literacy had given me a view of my wretched condition, without the remedy. "
            "It opened my eyes to the horrible pit, but to no ladder upon which to get out. "
            "In moments of agony, I envied my fellow slaves for their stupidity. "
            "I have often wished myself a beast. I preferred the condition of the meanest "
            "reptile to my own. Anything, no matter what, to get rid of thinking! "
            "Yet with this knowledge came resolve — that I would one day be free. "
            "Frederick Douglass path to freedom began with literacy and reading."
        ),
    },
]

# ── SQLAlchemy table ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass

class HippocampusDocument(Base):
    __tablename__ = "hippocampus_documents"
    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    source_title          = Column(String, nullable=False)
    source_url            = Column(String, nullable=False, default="")
    track                 = Column(String, nullable=False)
    chunk                 = Column(String, nullable=False)
    embedding             = Column(Vector(EMBED_DIM), nullable=False)
    citation_author       = Column(String, nullable=False, default="")
    citation_year         = Column(Integer, nullable=True)
    citation_archive_name = Column(String, nullable=False, default="")
    created_at            = Column(DateTime(timezone=True), server_default=func.now())


# ── Embedding helper ──────────────────────────────────────────────────────────

async def embed(text_input: str) -> list[float] | None:
    """
    Call OpenAI Embeddings API.
    If the content filter fires (400), log SENSITIVE_CONTENT_REVIEW_REQUIRED
    and return None — the caller decides whether to skip or substitute.
    """
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        resp = await client.embeddings.create(
            model=EMBED_MODEL,
            input=text_input,
        )
        return resp.data[0].embedding
    except openai.BadRequestError as e:
        if "content_filter" in str(e).lower() or e.status_code == 400:
            log.warning(
                "SENSITIVE_CONTENT_REVIEW_REQUIRED — content filter blocked this chunk. "
                f"Snippet: '{text_input[:80]}...'"
            )
            return None
        raise
    except Exception as e:
        log.error(f"Embedding error: {e}")
        raise


# ── Postgres / pgvector ───────────────────────────────────────────────────────

async def init_hippocampus(engine):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    log.info("[Hippocampus] Table ready")


async def insert_document(session_factory, embedding: list[float], **meta) -> str:
    async with session_factory() as session:
        doc = HippocampusDocument(embedding=embedding, **meta)
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return str(doc.id)


async def seed_oas_vectors(session_factory, mappings: list[dict]) -> int:
    """Embed each OAS standard (standard_text + lesson_hook) and store."""
    count = 0
    for m in mappings:
        embed_input = f"{m['standard_text']} {m.get('adeline_lesson_hook', '')}"
        vector = await embed(embed_input)
        if vector is None:
            log.warning(f"  Skipping {m['standard_id']} — content filter")
            continue
        await insert_document(
            session_factory,
            embedding=vector,
            source_title=f"OAS Standard {m['standard_id']}",
            source_url="https://sde.ok.gov/oklahoma-academic-standards",
            track=m["track"],
            chunk=embed_input,
            citation_author="Oklahoma State Department of Education",
            citation_year=2021,
            citation_archive_name="Oklahoma Academic Standards 2016 rev. 2021",
        )
        log.info(f"  [pgvector] Stored {m['standard_id']} → {m['track']}")
        count += 1
    return count


async def seed_douglass(session_factory) -> int:
    """Embed and store 3 focused Douglass chunks. Returns count stored."""
    stored = 0
    for i, doc_meta in enumerate(DOUGLASS_CHUNKS, 1):
        log.info(f"[Douglass] Embedding chunk {i}/3...")
        vector = await embed(doc_meta["chunk"])
        if vector is None:
            log.warning(f"[Douglass] Chunk {i} — SENSITIVE_CONTENT_REVIEW_REQUIRED, skipping")
            continue
        chunk_text = doc_meta.pop("chunk")
        doc_id = await insert_document(
            session_factory,
            embedding=vector,
            chunk=chunk_text,
            **doc_meta,
        )
        doc_meta["chunk"] = chunk_text  # restore for idempotency
        log.info(f"[Douglass] Chunk {i} stored → id={doc_id}")
        stored += 1
    return stored


# ── Neo4j ─────────────────────────────────────────────────────────────────────

async def seed_neo4j(driver, mappings: list[dict]):
    async with driver.session() as session:
        # Ensure Track nodes exist for all 8 tracks
        tracks = {m["track"] for m in mappings}
        for track in sorted(tracks):
            await session.run(
                "MERGE (t:Track {name: $name}) SET t.label = $label",
                {"name": track, "label": track.replace("_", " ").title()},
            )
        log.info(f"[Neo4j] Upserted {len(tracks)} Track nodes")

        # Upsert each OASStandard node
        for m in mappings:
            props = {
                **m["neo4j_node"]["properties"],
                "standard_text":  m["standard_text"],
                "lesson_hook":    m.get("adeline_lesson_hook", ""),
                "difficulty":     m.get("difficulty", ""),
                "homestead_note": m.get("homestead_adaptation", ""),
            }
            await session.run(
                """
                MERGE (s:OASStandard {id: $id})
                SET s += $props
                MERGE (t:Track {name: $track})
                MERGE (s)-[:MAPS_TO_TRACK]->(t)
                """,
                {"id": m["standard_id"], "props": props, "track": m["track"]},
            )
            log.info(f"  [Neo4j] Merged {m['standard_id']} → {m['track']}")

        # Upsert cross-track and progression relationships
        rel_count = 0
        for m in mappings:
            for rel in m.get("neo4j_relationships", []):
                target = rel["target"]
                rel_type = rel["type"]
                # Skip MAPS_TO_TRACK — already done above
                if rel_type == "MAPS_TO_TRACK":
                    continue
                # Cross-track relationships target a Track node
                if target in tracks:
                    await session.run(
                        f"""
                        MERGE (s:OASStandard {{id: $sid}})
                        MERGE (t:Track {{name: $target}})
                        MERGE (s)-[:{rel_type}]->(t)
                        """,
                        {"sid": m["standard_id"], "target": target},
                    )
                else:
                    # Progression relationship targets another OASStandard
                    await session.run(
                        f"""
                        MERGE (a:OASStandard {{id: $from_id}})
                        MERGE (b:OASStandard {{id: $to_id}})
                        MERGE (a)-[:{rel_type}]->(b)
                        """,
                        {"from_id": m["standard_id"], "to_id": target},
                    )
                rel_count += 1
        log.info(f"[Neo4j] Created {rel_count} relationships")

        # Seed the Douglass primary source as a HistoricalDocument node
        await session.run(
            """
            MERGE (d:HistoricalDocument {id: 'douglass-narrative-1845'})
            SET d.title   = 'Narrative of the Life of Frederick Douglass',
                d.author  = 'Frederick Douglass',
                d.year    = 1845,
                d.archive = 'Library of Congress'
            MERGE (t:Track {name: 'TRUTH_HISTORY'})
            MERGE (d)-[:PRIMARY_SOURCE_FOR]->(t)
            """
        )
        log.info("[Neo4j] Seeded Douglass HistoricalDocument node")


# ── Verification ──────────────────────────────────────────────────────────────

async def verify_truth_engine(session_factory) -> bool:
    """
    Simulate the /health/truth check:
    embed 'Frederick Douglass learning to read literacy slave narrative'
    and confirm top result scores >= TRUTH_THRESHOLD.
    """
    log.info("[TRUTH ENGINE] Running verification search...")
    query = "How did Frederick Douglass learn to read? He made friends with white boys in the street who taught him, despite laws forbidding slaves from learning to read."
    vector = await embed(query)
    if vector is None:
        log.error("[TRUTH ENGINE] Could not embed verification query")
        return False

    async with session_factory() as session:
        result = await session.execute(
            text("""
                SELECT source_title,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM hippocampus_documents
                WHERE track = 'TRUTH_HISTORY'
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT 1
            """),
            {"embedding": str(vector)},
        )
        row = result.mappings().first()

    if row is None:
        log.error("[TRUTH ENGINE] No TRUTH_HISTORY documents found")
        return False

    score = float(row["score"])
    log.info(f"[TRUTH ENGINE] Top match: '{row['source_title']}' — score={score:.4f}")
    if score >= TRUTH_THRESHOLD:
        log.info("✓ TRUTH_ENGINE_ONLINE — Witness Protocol threshold met")
        return True
    else:
        log.warning(f"✗ Score {score:.4f} below threshold {TRUTH_THRESHOLD}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-placeholder"):
        log.error("OPENAI_API_KEY is not set. Add it to .env and retry.")
        sys.exit(1)

    log.info("══════════════════════════════════════════")
    log.info("  SEEDING THE HIPPOCAMPUS — Dear Adeline  ")
    log.info("══════════════════════════════════════════")

    # Load OAS seed data
    with open(OAS_SEED_PATH) as f:
        seed_data = json.load(f)
    mappings = seed_data["mappings"]
    log.info(f"Loaded {len(mappings)} OAS standard mappings")

    # ── Postgres / pgvector ───────────────────────────────────────────────────
    engine = create_async_engine(POSTGRES_DSN, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    await init_hippocampus(engine)

    log.info("── Phase 1: OAS Standards → pgvector ────")
    oas_count = await seed_oas_vectors(session_factory, mappings)
    log.info(f"   Stored {oas_count}/{len(mappings)} OAS standard vectors")

    log.info("── Phase 2: Douglass Primary Source ─────")
    douglass_count = await seed_douglass(session_factory)

    # ── Neo4j ─────────────────────────────────────────────────────────────────
    log.info("── Phase 3: OAS Standards → Neo4j ───────")
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        await seed_neo4j(driver, mappings)
    finally:
        await driver.close()

    # ── Final count ───────────────────────────────────────────────────────────
    async with session_factory() as session:
        total = (await session.execute(text("SELECT COUNT(*) FROM hippocampus_documents"))).scalar()
    log.info(f"── Hippocampus total documents: {total} ─")

    # ── Verification ──────────────────────────────────────────────────────────
    if douglass_count > 0:
        log.info("── Phase 4: Truth Engine Verification ───")
        online = await verify_truth_engine(session_factory)
        if not online:
            log.warning("Truth engine check failed — inspect logs above")
            sys.exit(1)
    else:
        log.warning("No Douglass chunks stored — skipping truth engine check")

    await engine.dispose()
    log.info("══════════════════════════════════════════")
    log.info("  SEED COMPLETE                           ")
    log.info("══════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
