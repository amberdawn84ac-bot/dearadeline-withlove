from unittest.mock import AsyncMock, patch

import pytest

from app.agents.adapter import AdaptationRequest, adapt_canonical_for_student
from app.jobs.canonical_seeding import (
    CANONICAL_SEED_CATALOG,
    CanonicalSeed,
    canonical_seeding_enabled,
    configured_batch_size,
    replenish_canonical_library,
)


class _LockConnection:
    def __init__(self, owns_lock: bool = True):
        self.owns_lock = owns_lock
        self.executed: list[tuple] = []
        self.closed = False

    async def fetchval(self, query: str, *args):
        return self.owns_lock

    async def execute(self, query: str, *args):
        self.executed.append((query, args))

    async def close(self):
        self.closed = True


def test_canonical_seeding_is_explicitly_controlled(monkeypatch):
    monkeypatch.delenv("CANONICAL_SEEDING_ENABLED", raising=False)
    assert canonical_seeding_enabled() is False
    monkeypatch.setenv("CANONICAL_SEEDING_ENABLED", "YES")
    assert canonical_seeding_enabled() is True


def test_batch_size_is_bounded(monkeypatch):
    monkeypatch.setenv("CANONICAL_SEED_BATCH_SIZE", "999")
    assert configured_batch_size() == 50
    monkeypatch.setenv("CANONICAL_SEED_BATCH_SIZE", "not-a-number")
    assert configured_batch_size() == 6


def test_launch_catalog_includes_power_and_nation_building_investigation():
    topic = next(
        seed for seed in CANONICAL_SEED_CATALOG
        if "Railroads, Oil, and the Robber Barons" in seed.topic
    )
    assert topic.track == "TRUTH_HISTORY"
    assert topic.cross_track is True
    assert topic.archive_query == "railroads monopoly Standard Oil"
    assert topic.evidence_revision == "robber-baron-primary-pack-v2"
    assert "Building America or Consolidating Power?" in topic.topic


def test_only_deliberately_briefed_seeds_are_quality_approved():
    approved = [seed for seed in CANONICAL_SEED_CATALOG if seed.quality_approved]

    assert approved
    assert all(seed.family_summary.strip() for seed in approved)
    assert all(seed.authoring_brief.strip() for seed in approved)
    assert all(seed.content_revision.strip() for seed in approved)


def test_operation_hooked_states_pleas_plainly_without_collapsing_opioid_history():
    seed = next(seed for seed in CANONICAL_SEED_CATALOG if seed.learner_title.startswith("Operation Hooked"))

    assert "pleaded guilty" in seed.authoring_brief
    assert "not chemically identical" in seed.authoring_brief
    assert "do not attribute every opioid death to Purdue" in seed.authoring_brief
    assert "Greek word" in seed.authoring_brief


def test_bitter_harvest_preserves_mission_energy_and_requires_real_records():
    seed = next(seed for seed in CANONICAL_SEED_CATALOG if seed.learner_title.startswith("Operation Bitter Harvest"))

    assert "PRESERVE THE MISSION/CASE-FILE ENERGY" in seed.authoring_brief
    assert "State any documented verdict" in seed.authoring_brief
    assert "Do not fabricate internal memos" in seed.authoring_brief
    assert "minors" in seed.authoring_brief


def test_regulatory_capture_uses_actual_model_and_legislative_text():
    seed = next(seed for seed in CANONICAL_SEED_CATALOG if seed.learner_title.startswith("Operation Regulatory Capture"))

    assert "Living Wage Mandate Preemption Act" in seed.authoring_brief
    assert "side-by-side textual comparison" in seed.authoring_brief
    assert "actual representative" in seed.authoring_brief


@pytest.mark.asyncio
async def test_replenishment_exits_when_another_replica_owns_lock():
    conn = _LockConnection(owns_lock=False)
    author = AsyncMock()
    with (
        patch("app.config.get_db_conn", new=AsyncMock(return_value=conn)),
        patch("app.jobs.canonical_seeding.seed_one_canonical", new=author),
    ):
        result = await replenish_canonical_library(
            batch_size=1,
            catalog=(CanonicalSeed("One", "TRUTH_HISTORY"),),
        )

    assert result["locked"] is True
    author.assert_not_awaited()
    assert conn.closed is True


@pytest.mark.asyncio
async def test_replenishment_skips_existing_and_bounds_expensive_attempts():
    conn = _LockConnection()
    author = AsyncMock(side_effect=["skipped", "seeded", "failed", "seeded"])
    catalog = tuple(
        CanonicalSeed(str(index), "TRUTH_HISTORY") for index in range(4)
    )
    with (
        patch("app.config.get_db_conn", new=AsyncMock(return_value=conn)),
        patch("app.jobs.canonical_seeding.seed_one_canonical", new=author),
        patch("app.jobs.canonical_seeding.asyncio.sleep", new=AsyncMock()),
    ):
        result = await replenish_canonical_library(batch_size=2, catalog=catalog)

    assert result == {
        "seeded": 1,
        "skipped": 1,
        "failed": 1,
        "attempted": 2,
        "locked": False,
    }
    assert author.await_count == 3
    assert any("pg_advisory_unlock" in query for query, _ in conn.executed)
    assert conn.closed is True


@pytest.mark.asyncio
async def test_preseeded_lesson_preparation_uses_no_model_and_preserves_content():
    canonical = {
        "topic": "Hard Questions",
        "blocks": [{
            "block_type": "PRIMARY_SOURCE",
            "content": "Examine the record, then compare the competing claims.",
            "family_roles": {
                "elementary": "Notice what the record shows.",
                "middle": "Compare two claims.",
                "high_school": "Evaluate the evidence and uncertainty.",
            },
        }],
    }
    request = AdaptationRequest(grade_level="9", track="TRUTH_HISTORY")

    with patch("app.agents.adapter._llm_call", new=AsyncMock()) as llm:
        prepared = await adapt_canonical_for_student(canonical, request)

    llm.assert_not_awaited()
    assert prepared[0]["content"] == canonical["blocks"][0]["content"]
    assert prepared[0]["metadata"]["learner_entry"]["role_band"] == "high_school"
    assert prepared[0]["metadata"]["learner_entry"]["role"] == (
        "Evaluate the evidence and uncertainty."
    )
    assert "metadata" not in canonical["blocks"][0]
