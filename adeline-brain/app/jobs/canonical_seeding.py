"""Controlled background authoring for the shared canonical lesson library.

The web experience route and this job deliberately call the same canonical
author.  Background work only moves that expensive call ahead of the learner;
it does not introduce a second lesson format or a block-by-block generator.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, replace
from typing import Iterable

logger = logging.getLogger(__name__)

_LOCK_NAME = "dear-adeline:canonical-library-replenishment"


@dataclass(frozen=True)
class CanonicalSeed:
    topic: str
    track: str
    cross_track: bool = False
    archive_query: str = ""


# Ordered deliberately: launch-critical public-interest and practical family
# investigations are authored first, followed by balanced track coverage.
CANONICAL_SEED_CATALOG: tuple[CanonicalSeed, ...] = (
    CanonicalSeed(
        "The Opioid Crisis: Corporate Decisions, Regulation, and Unequal Consequences",
        "JUSTICE_CHANGEMAKING",
        True,
    ),
    CanonicalSeed(
        "From Possession to Prison: Drug Policy, Diversion, and Reform",
        "JUSTICE_CHANGEMAKING",
        True,
    ),
    CanonicalSeed(
        "Food Systems: Who Profits, Who Pays, and What the Evidence Shows",
        "JUSTICE_CHANGEMAKING",
        True,
    ),
    CanonicalSeed(
        "Ultra-Processed Food: Marketing, Regulation, and Health Evidence",
        "HEALTH_NATUROPATHY",
        True,
    ),
    CanonicalSeed(
        "Pesticides, Farmworkers, and the Food Supply",
        "JUSTICE_CHANGEMAKING",
        True,
    ),
    CanonicalSeed(
        "Seed Patents, Market Concentration, and Farmer Choice",
        "GOVERNMENT_ECONOMICS",
        True,
    ),
    CanonicalSeed(
        "Railroads, Oil, and the Robber Barons: Building America or Consolidating Power?",
        "TRUTH_HISTORY",
        True,
        "railroads monopoly Standard Oil",
    ),
    CanonicalSeed("The Oklahoma Land Run: Multiple Perspectives", "TRUTH_HISTORY"),
    CanonicalSeed("Oral Tradition and Family History", "TRUTH_HISTORY"),
    CanonicalSeed("The Boston Tea Party: Primary Accounts", "TRUTH_HISTORY"),
    CanonicalSeed("Plant Life Cycles and Seeds", "CREATION_SCIENCE"),
    CanonicalSeed("The Fossil Record and Catastrophism", "CREATION_SCIENCE"),
    CanonicalSeed("Design in the Human Eye", "CREATION_SCIENCE"),
    CanonicalSeed("Building a Rainwater Collection System", "HOMESTEADING"),
    CanonicalSeed("Soil Regeneration and Composting", "HOMESTEADING"),
    CanonicalSeed("Corporate Lobbying vs. Citizen Advocacy", "JUSTICE_CHANGEMAKING"),
    CanonicalSeed("Regulatory Capture in Practice", "JUSTICE_CHANGEMAKING"),
    CanonicalSeed("The Parable of the Sower: Original Context", "DISCIPLESHIP"),
    CanonicalSeed("What Does 'Love Your Neighbor' Mean in Practice?", "DISCIPLESHIP"),
    CanonicalSeed("History of the Income Tax in the United States", "GOVERNMENT_ECONOMICS"),
    CanonicalSeed("How Property Taxes Are Calculated and Used", "GOVERNMENT_ECONOMICS"),
    CanonicalSeed("The Hero's Journey in Literature", "ENGLISH_LITERATURE"),
    CanonicalSeed("Symbolism in Scripture and Classic Stories", "ENGLISH_LITERATURE"),
    CanonicalSeed("Calculating Board Feet for Building Projects", "APPLIED_MATHEMATICS"),
    CanonicalSeed("Reading a Land Survey and Calculating Acreage", "APPLIED_MATHEMATICS"),
    CanonicalSeed("Pricing Handmade Goods for Market", "CREATIVE_ECONOMY"),
    CanonicalSeed("Photography for Online Product Sales", "CREATIVE_ECONOMY"),
    CanonicalSeed("Herbal First Aid: Plantain, Lavender, and Calendula", "HEALTH_NATUROPATHY"),
    CanonicalSeed("Stewardship in Creation Science", "CREATION_SCIENCE", True),
    CanonicalSeed("Justice Themes in Scripture and History", "TRUTH_HISTORY", True),
    CanonicalSeed("Biblical Economics and Property Rights", "GOVERNMENT_ECONOMICS", True),
    CanonicalSeed("Healing the Land: Soil, Health, and Sabbath Rest", "HOMESTEADING", True),
    CanonicalSeed("Kitchen Chemistry: Bread and Fermentation", "CREATION_SCIENCE", True),
    CanonicalSeed("Household Water: Testing, Treatment, and Public Responsibility", "CREATION_SCIENCE", True),
    CanonicalSeed("School Lunches: Nutrition, Budgets, Contracts, and Student Voice", "GOVERNMENT_ECONOMICS", True),
    CanonicalSeed("Housing, Zoning, and Who Gets to Live Where", "GOVERNMENT_ECONOMICS", True),
    CanonicalSeed("News Claims Under Pressure: Evidence, Incentives, and Verification", "ENGLISH_LITERATURE", True),
    CanonicalSeed("Design and Test a Low-Cost Food Dryer", "HOMESTEADING", True),
    CanonicalSeed("Map a Household Supply Chain from Raw Material to Waste", "APPLIED_MATHEMATICS", True),
    CanonicalSeed("Build a Community Price Index", "APPLIED_MATHEMATICS", True),
    CanonicalSeed("Create a Useful Product with a Real Customer", "CREATIVE_ECONOMY", True),
)


def canonical_seeding_enabled() -> bool:
    return os.getenv("CANONICAL_SEEDING_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }


def configured_batch_size() -> int:
    try:
        return max(1, min(int(os.getenv("CANONICAL_SEED_BATCH_SIZE", "6")), 50))
    except ValueError:
        logger.warning("Invalid CANONICAL_SEED_BATCH_SIZE; using 6")
        return 6


async def seed_one_canonical(seed: CanonicalSeed) -> str:
    """Create one missing/outdated canonical through the production author."""
    from app.api.experience_builder import _author, canonical_resource_query
    from app.connections.canonical_store import canonical_slug, canonical_store
    from app.curriculum.family_style import finalize_family_lesson, is_current_family_canonical
    from app.schemas.api_models import LessonRequest, Track
    from app.services.resource_router import resource_router

    slug = canonical_slug(seed.topic, seed.track)
    existing = await canonical_store.get(slug)
    if existing and is_current_family_canonical(existing.get("blocks") or []):
        logger.info("[CanonicalSeed] SKIP current — %s / %s", seed.topic, seed.track)
        return "skipped"
    if existing:
        await canonical_store.archive(slug, reason="canonical_format_upgrade")

    try:
        request = LessonRequest(
            student_id="canonical-seeder",
            track=Track(seed.track),
            topic=seed.topic,
            is_homestead=seed.track == "HOMESTEADING",
            grade_level="9",
        )
        resource_query = canonical_resource_query(request)
        if seed.archive_query:
            resource_query = replace(resource_query, topic=seed.archive_query)
        packet = await resource_router.search(resource_query)
        routed = packet.get("resources") or []
        verified_primary = sum(
            1 for item in routed
            if str(item.get("resource_type") or "").upper() == "PRIMARY_SOURCE"
            and str(item.get("availability") or "").upper()
            in {"VERIFIED_API_ITEM", "VERIFIED_ARCHIVE_ITEM"}
        )
        logger.info(
            "[CanonicalSeed] Sources — topic=%s routed=%d verified_primary=%d provider_failures=%s",
            seed.topic,
            len(routed),
            verified_primary,
            packet.get("provider_failures") or [],
        )
        authored = await _author(request, packet.get("resources") or [])
        blocks = finalize_family_lesson(
            authored.get("blocks") or [], seed.topic, track=seed.track
        )
        if not blocks:
            raise ValueError("canonical author returned no valid investigation blocks")
        blocks[0].setdefault("metadata", {})["canonical_contract"] = {
            key: authored.get(key)
            for key in (
                "big_question",
                "learning_goal",
                "shared_experience",
                "experience_design",
                "investigation_scope_contract",
                "public_interest_contract",
                "real_world_task",
                "portfolio_task",
                "printable_contract",
                "demonstration_contract",
                "mastery_evidence_map",
                "family_roles",
            )
        }
        record = {
            "id": str(uuid.uuid4()),
            "topic": seed.topic,
            "track": seed.track,
            "title": authored.get("title") or seed.topic,
            "blocks": blocks,
            "oas_standards": [],
            "researcher_activated": bool(packet.get("resources")),
            "agent_name": "Canonical Experience Author",
        }
        await canonical_store.save(slug, record, pending=False)
        logger.info("[CanonicalSeed] READY — %s / %s", seed.topic, seed.track)
        return "seeded"
    except Exception:
        logger.exception("[CanonicalSeed] FAILED — %s / %s", seed.topic, seed.track)
        return "failed"


async def replenish_canonical_library(
    *,
    batch_size: int | None = None,
    catalog: Iterable[CanonicalSeed] | None = None,
) -> dict[str, int | bool]:
    """Author a bounded number of missing canonicals, once across all replicas."""
    from app.config import get_db_conn

    limit = configured_batch_size() if batch_size is None else max(1, min(batch_size, 50))
    seeds = tuple(catalog or CANONICAL_SEED_CATALOG)
    result: dict[str, int | bool] = {
        "seeded": 0,
        "skipped": 0,
        "failed": 0,
        "attempted": 0,
        "locked": False,
    }
    conn = await get_db_conn()
    owns_lock = False
    try:
        owns_lock = bool(await conn.fetchval(
            "SELECT pg_try_advisory_lock(hashtext($1))", _LOCK_NAME
        ))
        if not owns_lock:
            result["locked"] = True
            logger.info("[CanonicalSeed] Another replica owns this replenishment run")
            return result

        logger.info(
            "[CanonicalSeed] Replenishment started — batch=%d catalog=%d", limit, len(seeds)
        )
        for seed in seeds:
            if int(result["attempted"]) >= limit:
                break
            status = await seed_one_canonical(seed)
            result[status] = int(result[status]) + 1
            if status != "skipped":
                result["attempted"] = int(result["attempted"]) + 1
            # Keep provider traffic deliberately serial and gentle.
            if status != "skipped":
                await asyncio.sleep(2)
        logger.info("[CanonicalSeed] Replenishment complete — %s", result)
        return result
    finally:
        if owns_lock:
            try:
                await conn.execute("SELECT pg_advisory_unlock(hashtext($1))", _LOCK_NAME)
            except Exception:
                logger.exception("[CanonicalSeed] Failed to release advisory lock")
        await conn.close()


async def scheduled_canonical_replenishment() -> dict[str, int | bool]:
    """APScheduler entry point; the scheduler itself controls enablement."""
    return await replenish_canonical_library()
