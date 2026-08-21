"""Pre-seed foundational investigations through the current canonical author.

This is intentionally idempotent and cannot call the retired lesson pipeline.
Run from adeline-brain with: python -m scripts.seed_canonicals
"""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("seed_canonicals")

SEED_TOPICS: list[tuple[str, str, bool]] = [
    ("The Oklahoma Land Run: Multiple Perspectives", "TRUTH_HISTORY", False),
    ("Oral Tradition and Family History", "TRUTH_HISTORY", False),
    ("The Boston Tea Party: Primary Accounts", "TRUTH_HISTORY", False),
    ("Plant Life Cycles and Seeds", "CREATION_SCIENCE", False),
    ("The Fossil Record and Catastrophism", "CREATION_SCIENCE", False),
    ("Design in the Human Eye", "CREATION_SCIENCE", False),
    ("Building a Rainwater Collection System", "HOMESTEADING", False),
    ("Soil Regeneration and Composting", "HOMESTEADING", False),
    ("Corporate Lobbying vs. Citizen Advocacy", "JUSTICE_CHANGEMAKING", False),
    ("Regulatory Capture in Practice", "JUSTICE_CHANGEMAKING", False),
    ("The Parable of the Sower: Original Context", "DISCIPLESHIP", False),
    ("What Does 'Love Your Neighbor' Mean in Practice?", "DISCIPLESHIP", False),
    ("History of the Income Tax in the United States", "GOVERNMENT_ECONOMICS", False),
    ("How Property Taxes Are Calculated and Used", "GOVERNMENT_ECONOMICS", False),
    ("The Hero's Journey in Literature", "ENGLISH_LITERATURE", False),
    ("Symbolism in Scripture and Classic Stories", "ENGLISH_LITERATURE", False),
    ("Calculating Board Feet for Building Projects", "APPLIED_MATHEMATICS", False),
    ("Reading a Land Survey and Calculating Acreage", "APPLIED_MATHEMATICS", False),
    ("Pricing Handmade Goods for Market", "CREATIVE_ECONOMY", False),
    ("Photography for Online Product Sales", "CREATIVE_ECONOMY", False),
    ("Herbal First Aid: Plantain, Lavender, and Calendula", "HEALTH_NATUROPATHY", False),
    ("Stewardship in Creation Science", "CREATION_SCIENCE", True),
    ("Justice Themes in Scripture and History", "TRUTH_HISTORY", True),
    ("Biblical Economics and Property Rights", "GOVERNMENT_ECONOMICS", True),
    ("Healing the Land: Soil, Health, and Sabbath Rest", "HOMESTEADING", True),
]


async def seed_one(topic: str, track: str, cross_track: bool) -> str:
    from app.api.experience_builder import _author
    from app.connections.canonical_store import canonical_slug, canonical_store
    from app.curriculum.family_style import finalize_family_lesson, is_current_family_canonical
    from app.schemas.api_models import LessonRequest, Track
    from app.services.resource_router import ResourceQuery, resource_router

    slug = canonical_slug(topic, track)
    existing = await canonical_store.get(slug)
    if existing and is_current_family_canonical(existing.get("blocks") or []):
        logger.info("SKIP (current) — %s / %s", topic, track)
        return "skipped"
    if existing:
        await canonical_store.archive(slug, reason="canonical_format_upgrade")

    try:
        request = LessonRequest(
            student_id="canonical-seeder",
            track=Track(track),
            topic=topic,
            is_homestead=track == "HOMESTEADING",
            grade_level="9",
        )
        packet = await resource_router.search(ResourceQuery(topic=topic, track=track, grade_level="9"))
        authored = await _author(request, packet.get("resources") or [])
        blocks = finalize_family_lesson(authored.get("blocks") or [], topic, track=track)
        if not blocks:
            raise ValueError("canonical author returned no valid investigation blocks")
        blocks[0].setdefault("metadata", {})["canonical_contract"] = {
            key: authored.get(key)
            for key in (
                "big_question", "learning_goal", "shared_experience", "investigation_scope_contract", "real_world_task",
                "portfolio_task", "printable_contract", "demonstration_contract", "family_roles",
            )
        }
        record = {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "track": track,
            "title": authored.get("title") or topic,
            "blocks": blocks,
            "oas_standards": [],
            "pending_approval": False,
            "seed_cross_track": cross_track,
            "agent_name": "Canonical Experience Author",
        }
        await canonical_store.save(slug, record, pending=False)
        logger.info("SEEDED — %s / %s", topic, track)
        return "seeded"
    except Exception:
        logger.exception("FAILED — %s / %s", topic, track)
        return "failed"


async def main() -> None:
    logger.info("Starting canonical pre-seed — %d topics", len(SEED_TOPICS))
    results = {"seeded": 0, "skipped": 0, "failed": 0}
    for topic, track, cross_track in SEED_TOPICS:
        status = await seed_one(topic, track, cross_track)
        results[status] += 1
        await asyncio.sleep(2)
    logger.info("Complete — %s", results)
    if results["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
