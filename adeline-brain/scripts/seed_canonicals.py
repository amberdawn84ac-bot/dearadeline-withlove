"""
Pre-seed script: generate 25 foundational canonical lessons.

Usage:
    python -m scripts.seed_canonicals

Generates 21 per-track topics (2-3 per track) + 4 cross-track bridging topics.
Skips any slug that already exists in the canonical store.
Saves with pending_approval=False (seed canonicals are pre-approved quality).
Run once after deployment; safe to re-run (idempotent).
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Allow running as a module from the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("seed_canonicals")

# ── Seed topic list ───────────────────────────────────────────────────────────

SEED_TOPICS: list[tuple[str, str, bool]] = [
    # (topic, track, cross_track)
    # TRUTH_HISTORY × 3
    ("The Oklahoma Land Run: Multiple Perspectives",       "TRUTH_HISTORY",        False),
    ("Oral Tradition and Family History",                   "TRUTH_HISTORY",        False),
    ("The Boston Tea Party: Primary Accounts",              "TRUTH_HISTORY",        False),
    # CREATION_SCIENCE × 3
    ("Plant Life Cycles and Seeds",                         "CREATION_SCIENCE",     False),
    ("The Fossil Record and Catastrophism",                 "CREATION_SCIENCE",     False),
    ("Design in the Human Eye",                             "CREATION_SCIENCE",     False),
    # HOMESTEADING × 2
    ("Building a Rainwater Collection System",              "HOMESTEADING",         False),
    ("Soil Regeneration and Composting",                    "HOMESTEADING",         False),
    # JUSTICE_CHANGEMAKING × 2
    ("Corporate Lobbying vs. Citizen Advocacy",             "JUSTICE_CHANGEMAKING", False),
    ("Regulatory Capture in Practice",                      "JUSTICE_CHANGEMAKING", False),
    # DISCIPLESHIP × 2
    ("The Parable of the Sower: Original Context",          "DISCIPLESHIP",         False),
    ("What Does 'Love Your Neighbor' Mean in Practice?",    "DISCIPLESHIP",         False),
    # GOVERNMENT_ECONOMICS × 2
    ("History of the Income Tax in the United States",      "GOVERNMENT_ECONOMICS", False),
    ("How Property Taxes Are Calculated and Used",          "GOVERNMENT_ECONOMICS", False),
    # ENGLISH_LITERATURE × 2
    ("The Hero's Journey in Literature",                    "ENGLISH_LITERATURE",   False),
    ("Symbolism in Scripture and Classic Stories",          "ENGLISH_LITERATURE",   False),
    # APPLIED_MATHEMATICS × 2
    ("Calculating Board Feet for Building Projects",        "APPLIED_MATHEMATICS",  False),
    ("Reading a Land Survey and Calculating Acreage",       "APPLIED_MATHEMATICS",  False),
    # CREATIVE_ECONOMY × 2
    ("Pricing Handmade Goods for Market",                   "CREATIVE_ECONOMY",     False),
    ("Photography for Online Product Sales",                "CREATIVE_ECONOMY",     False),
    # HEALTH_NATUROPATHY × 1
    ("Herbal First Aid: Plantain, Lavender, and Calendula", "HEALTH_NATUROPATHY",   False),
    # Cross-track bridging × 4
    ("Stewardship in Creation Science",                     "CREATION_SCIENCE",     True),
    ("Justice Themes in Scripture and History",             "TRUTH_HISTORY",        True),
    ("Biblical Economics and Property Rights",              "GOVERNMENT_ECONOMICS", True),
    ("Healing the Land: Soil, Health, and Sabbath Rest",    "HOMESTEADING",         True),
]


async def seed_one(topic: str, track: str, cross_track: bool) -> str:
    """Generate and save a single canonical. Returns 'seeded', 'skipped', or 'failed'."""
    from app.connections.canonical_store import canonical_store, canonical_slug
    from app.agents.orchestrator import run_orchestrator
    from app.schemas.api_models import LessonRequest, Track

    slug = canonical_slug(topic, track)

    # Skip if already in store
    existing = await canonical_store.get(slug)
    if existing:
        logger.info(f"[Seed] SKIP (exists) — {topic!r} / {track}")
        return "skipped"

    try:
        track_enum = Track(track)
        lr = LessonRequest(
            student_id="seed-script",
            track=track_enum,
            topic=topic,
            is_homestead=(track == "HOMESTEADING"),
            grade_level="9",
        )

        # Use embedding for retrieval
        import openai as _oai
        client = _oai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        embed_resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=topic,
        )
        query_embedding = embed_resp.data[0].embedding

        lesson = await run_orchestrator(
            lr,
            query_embedding,
            interaction_count=10,
            cross_track_acknowledgment=(
                f"[cross-track] This topic bridges multiple curriculum tracks. "
                f"Weave in relevant OAS standards from adjacent tracks."
                if cross_track else None
            ),
            mastery_score=0.5,
            mastery_band="DEVELOPING",
        )

        canonical_record = {
            "id": lesson.lesson_id,
            "topic_slug": slug,
            "topic": topic,
            "track": track,
            "title": lesson.title,
            "blocks": [b.model_dump() for b in lesson.blocks],
            "oas_standards": lesson.oas_standards,
            "researcher_activated": lesson.researcher_activated,
            "agent_name": lesson.agent_name,
            "pending_approval": False,
            "needs_review_reason": None,
        }
        # Force save without pending gate — seed canonicals are pre-approved
        await canonical_store.save(slug, canonical_record, pending=False)
        logger.info(f"[Seed] SEEDED — {topic!r} / {track} (researcher={lesson.researcher_activated})")
        return "seeded"

    except Exception as e:
        logger.error(f"[Seed] FAILED — {topic!r} / {track}: {e}")
        return "failed"


async def main() -> None:
    logger.info(f"[Seed] Starting canonical pre-seed — {len(SEED_TOPICS)} topics")

    # Establish DB/Redis connections (same pattern as app startup)
    from app.connections.journal_store import journal_store
    try:
        await journal_store.connect()
    except Exception as e:
        logger.warning(f"[Seed] journal_store connect failed (non-fatal): {e}")

    results: dict[str, int] = {"seeded": 0, "skipped": 0, "failed": 0}

    for topic, track, cross_track in SEED_TOPICS:
        status = await seed_one(topic, track, cross_track)
        results[status] = results.get(status, 0) + 1
        # Small pause between generations to avoid rate limits
        await asyncio.sleep(2)

    logger.info(
        f"[Seed] Complete — seeded={results['seeded']} "
        f"skipped={results['skipped']} failed={results['failed']}"
    )
    if results["failed"] > 0:
        logger.warning("[Seed] Some topics failed — check logs above and re-run to retry.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
