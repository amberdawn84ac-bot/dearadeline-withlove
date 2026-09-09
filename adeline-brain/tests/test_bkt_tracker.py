"""BKT persistence: Prisma @default(uuid()) is client-only, so raw SQL must supply id."""
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.algorithms import bkt_tracker


class _FakeConn:
    def __init__(self):
        self.execute_calls = []

    async def fetchrow(self, _sql, *_args):
        return None

    async def execute(self, sql, *args):
        self.execute_calls.append((sql, args))

    async def close(self):
        return None


def _assert_insert_supplies_id(sql: str, args: tuple) -> None:
    compact = "".join(sql.split())
    assert 'INSERTINTO"SpacedRepetitionCard"' in compact
    assert compact.startswith("INSERTINTO") or "(id," in compact
    assert "(id," in compact
    UUID(str(args[0]))


@pytest.mark.asyncio
async def test_update_bkt_inserts_a_card_id(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(bkt_tracker, "get_db_conn", AsyncMock(return_value=conn))

    await bkt_tracker.update_bkt("student-1", "C1", "CREATION_SCIENCE", True)

    assert conn.execute_calls, "expected an INSERT"
    sql, args = conn.execute_calls[0]
    _assert_insert_supplies_id(sql, args)
    assert args[1] == "student-1"
    assert args[2] == "C1"


@pytest.mark.asyncio
async def test_update_card_after_lesson_inserts_a_card_id(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(bkt_tracker, "get_db_conn", AsyncMock(return_value=conn))

    await bkt_tracker.update_card_after_lesson(
        "student-1", "C10", "Wild yeast", "CREATION_SCIENCE", quality=4,
    )

    sql, args = conn.execute_calls[0]
    _assert_insert_supplies_id(sql, args)
    assert args[1] == "student-1"
    assert args[2] == "C10"
