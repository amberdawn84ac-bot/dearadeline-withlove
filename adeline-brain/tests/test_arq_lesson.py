"""Tests for async lesson generation via ARQ."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app


@pytest.mark.asyncio
async def test_generate_lesson_returns_job_id():
    """POST /lesson/generate returns job_id immediately, not a full LessonResponse."""
    mock_job = MagicMock()
    mock_job.job_id = "test-job-id-123"

    async def override_user_id():
        return "student-123"

    from app.api.middleware import get_current_user_id
    app.dependency_overrides[get_current_user_id] = override_user_id

    try:
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.api.lessons._enqueue_lesson_job", AsyncMock(return_value=mock_job))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/lesson/generate", json={
                    "student_id": "student-123",
                    "track": "TRUTH_HISTORY",
                    "topic": "Frederick Douglass",
                    "is_homestead": False,
                    "grade_level": "5",
                }, headers={"Authorization": "Bearer test-token"})
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"] == "test-job-id-123"
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_lesson_status_done():
    """GET /lesson/status/{job_id} returns done + result when ARQ job is complete."""
    from arq.jobs import JobStatus

    mock_job = MagicMock()
    mock_job.status = AsyncMock(return_value=JobStatus.complete)
    mock_job.result = AsyncMock(return_value={"lesson_id": "abc", "title": "Test Lesson"})

    async def override_user_id():
        return "student-123"

    from app.api.middleware import get_current_user_id
    app.dependency_overrides[get_current_user_id] = override_user_id

    try:
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.api.lessons._get_arq_job", MagicMock(return_value=mock_job))
            mp.setattr("app.api.lessons._get_arq_redis_pool", AsyncMock(return_value=MagicMock(aclose=AsyncMock())))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/lesson/status/test-job-id-123",
                                       headers={"Authorization": "Bearer test-token"})
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["result"]["lesson_id"] == "abc"


@pytest.mark.asyncio
async def test_lesson_status_queued():
    """GET /lesson/status/{job_id} returns queued while job is waiting."""
    from arq.jobs import JobStatus

    mock_job = MagicMock()
    mock_job.status = AsyncMock(return_value=JobStatus.queued)

    async def override_user_id():
        return "student-123"

    from app.api.middleware import get_current_user_id
    app.dependency_overrides[get_current_user_id] = override_user_id

    try:
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.api.lessons._get_arq_job", MagicMock(return_value=mock_job))
            mp.setattr("app.api.lessons._get_arq_redis_pool", AsyncMock(return_value=MagicMock(aclose=AsyncMock())))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/lesson/status/test-job-id-123",
                                       headers={"Authorization": "Bearer test-token"})
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
