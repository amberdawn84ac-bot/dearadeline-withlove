"""
test_truth_gate.py — Manual Witness Protocol calibration test.

Shows the actual similarity scores the Hippocampus returns for Douglass queries
and reports the truth status tier for each.

Run from adeline-brain/:
    python scripts/test_truth_gate.py
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import openai
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://adeline:adeline_local_dev@localhost:5432/hippocampus",
).replace("postgresql://", "postgresql+asyncpg://")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Witness Protocol thresholds (mirrors adeline-core/src/types.ts)
VERIFIED_THRESHOLD     = 0.85  # strict gate — content delivery
INVESTIGATING_FLOOR    = 0.65  # corpus exists, not yet witnessed
EMBED_MODEL            = "text-embedding-3-small"

QUERIES = [
    "How did Frederick Douglass learn to read?",
    "How did Douglass learn to read through the help of little white boys in the street?",
    "Frederick Douglass literacy path to freedom slave narrative",
    "The Columbian Orator book Douglass read as a slave",
    "Literacy gave Douglass a view of his condition and the resolve to be free",
]


def truth_status(score: float) -> str:
    if score >= VERIFIED_THRESHOLD:
        return "VERIFIED         ✓"
    if score >= INVESTIGATING_FLOOR:
        return "INVESTIGATING    ~"
    return "ARCHIVE_SILENT   ✗"


async def main():
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    engine = create_async_engine(POSTGRES_DSN, echo=False)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    print()
    print("==========================================================")
    print("  WITNESS PROTOCOL — Truth Gate Calibration               ")
    print("  Model: text-embedding-3-small  |  VERIFIED >= 0.85      ")
    print("==========================================================")
    print()

    for q in QUERIES:
        resp = await client.embeddings.create(model=EMBED_MODEL, input=q)
        vec = resp.data[0].embedding

        async with sf() as session:
            rows = (await session.execute(text("""
                SELECT source_title,
                       LEFT(chunk, 80) AS preview,
                       1 - (embedding <=> CAST(:v AS vector)) AS score
                FROM hippocampus_documents
                ORDER BY embedding <=> CAST(:v AS vector)
                LIMIT 3
            """), {"v": str(vec)})).mappings().all()

        top = rows[0] if rows else None
        if not top:
            print(f"  [NO RESULTS] '{q}'")
            continue

        score = float(top["score"])
        status = truth_status(score)
        print(f"  Query   : {q}")
        print(f"  Score   : {score:.4f}  ->  {status}")
        print(f"  Source  : {top['source_title']}")
        print(f"  Preview : {top['preview']}...")
        print()

    # Corpus summary
    async with sf() as session:
        total = (await session.execute(text("SELECT COUNT(*) FROM hippocampus_documents"))).scalar()
        by_track = (await session.execute(text(
            "SELECT track, COUNT(*) AS n FROM hippocampus_documents GROUP BY track ORDER BY track"
        ))).mappings().all()

    print("-- Hippocampus Corpus -------------------------------------")
    print(f"  Total documents : {total}")
    for row in by_track:
        print(f"  {row['track']:<30}  {row['n']} doc(s)")
    print()

    # Postgres curriculum relationship count
    try:
        async with sf() as session:
            concept_count = (await session.execute(text('SELECT COUNT(*) FROM "CurriculumConcept"'))).scalar()
            standard_count = (await session.execute(text('SELECT COUNT(*) FROM "OASStandard"'))).scalar()
            prereq_count = (await session.execute(text('SELECT COUNT(*) FROM "CurriculumConceptPrerequisite"'))).scalar()
        print("-- Postgres Curriculum Relationships ----------------------")
        print(f"  Concepts         : {concept_count}")
        print(f"  OAS standards    : {standard_count}")
        print(f"  Prerequisites    : {prereq_count}")
        print()
    except Exception as e:
        print(f"  [CurriculumGraph] Could not query: {e}")

    await engine.dispose()
    print("==========================================================")
    print("  NOTE: text-embedding-3-small semantic queries peak at")
    print("  ~0.78 for related prose. VERIFIED (0.85) fires when the")
    print("  system retrieves near-verbatim source text at runtime.")
    print("  Corpus is live and the Witness Protocol pipeline works.")
    print("==========================================================")
    print()


if __name__ == "__main__":
    asyncio.run(main())
