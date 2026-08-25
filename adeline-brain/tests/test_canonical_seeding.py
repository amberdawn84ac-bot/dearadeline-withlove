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
    assert "Building America or Consolidating Power?" in topic.topic


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
