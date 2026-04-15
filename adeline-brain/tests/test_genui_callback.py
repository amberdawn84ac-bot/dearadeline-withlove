"""Tests for /genui/callback endpoint — covers the NameError fix and all 4 event types."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from app.main import app
from app.api.middleware import get_current_user_id
from app.models.student import load_student_state, StudentState


def _override_auth():
    """Dependency override: bypass JWT verification, return a fixed user ID."""
    return "student-123"


@pytest.fixture(autouse=True)
def override_auth():
    """Override get_current_user_id for all tests in this module."""
    app.dependency_overrides[get_current_user_id] = _override_auth
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture
def auth_headers():
    """Dummy auth headers — auth is bypassed via dependency override."""
    return {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_onAnswer_returns_updated_mastery(auth_headers):
    """onAnswer event returns a float mastery score — not a NameError."""
    mock_state = StudentState(student_id="student-123")
    with patch("app.api.genui.load_student_state", new_callable=AsyncMock, return_value=mock_state):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/genui/callback", json={
                "student_id": "student-123",
                "lesson_id": "lesson-abc",
                "component_type": "InteractiveQuiz",
                "event": "onAnswer",
                "state": {"isCorrect": True},
            }, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["updated_mastery"], float)
    assert 0.0 <= body["updated_mastery"] <= 1.0


@pytest.mark.asyncio
async def test_onComplete_succeeds(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/genui/callback", json={
            "student_id": "student-123",
            "lesson_id": "lesson-abc",
            "component_type": "ScaffoldedProblem",
            "event": "onComplete",
            "state": {},
        }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_onHint_triggers_rerender_at_threshold(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/genui/callback", json={
            "student_id": "student-123",
            "lesson_id": "lesson-abc",
            "component_type": "ScaffoldedProblem",
            "event": "onHint",
            "state": {"hintsUsed": 3},
        }, headers=auth_headers)
    body = resp.json()
    assert body["success"] is True
    assert body["should_re_render"] is True


@pytest.mark.asyncio
async def test_onStruggle_triggers_scaffolding_rerender(auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/genui/callback", json={
            "student_id": "student-123",
            "lesson_id": "lesson-abc",
            "component_type": "ScaffoldedProblem",
            "event": "onStruggle",
            "state": {"wrongAttempts": 2, "scaffolding_level": 0},
        }, headers=auth_headers)
    body = resp.json()
    assert body["success"] is True
    assert body["should_re_render"] is True
    assert body["new_state"]["scaffolding_level"] == 1
