from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connections.curriculum_graph import CurriculumGraph


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback):
        return False


@pytest.mark.asyncio
async def test_grade_standards_types_nullable_subject_limit_for_postgres():
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    session = AsyncMock()
    session.execute.return_value = result

    with patch(
        "app.connections.curriculum_graph._get_session_factory",
        return_value=lambda: _SessionContext(session),
    ):
        rows = await CurriculumGraph().get_grade_standards(
            "student-1", 9, limit=500, per_subject_limit=None,
        )

    query, params = session.execute.await_args.args
    assert "CAST(:per_subject_limit AS INTEGER)" in str(query)
    assert params["per_subject_limit"] is None
    assert rows == []
