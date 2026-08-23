"""Learner-first registration cannot bypass guardian approval."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_registration_does_not_return_a_student_session_before_approval():
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "profile": {
            "id": "student-1",
            "name": "Learner",
            "role": "STUDENT",
            "username": "learner_1",
            "gradeLevel": "6",
            "linkCode": "ABCDEF123456",
            "xp": 0,
            "adeCoins": 0,
            "reputation": 0,
            "coppaVerified": False,
        }
    }
    with (
        patch("app.api.student_auth.get_db_conn", new=AsyncMock(return_value=conn)),
        patch("app.api.student_auth.uuid.uuid4", return_value="student-1"),
    ):
        response = client.post("/auth/student/register", json={
            "display_name": "Learner",
            "username": "learner_1",
            "pin": "1234",
            "grade_level": "6",
            "parent_name": "Guardian",
            "parent_email": "guardian@example.com",
            "parent_verification_token": "b" * 64,
        })

    assert response.status_code == 200
    body = response.json()
    assert body["requires_parent_verification"] is True
    assert body["token"] is None


def test_unverified_unlinked_learner_cannot_log_in():
    import bcrypt

    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "id": "student-1",
        "pinHash": bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode(),
        "parentId": None,
        "coppaVerified": False,
    }
    with patch("app.api.student_auth.get_db_conn", new=AsyncMock(return_value=conn)):
        response = client.post("/auth/student/login", json={"username": "learner_1", "pin": "1234"})

    assert response.status_code == 403
    assert "parent or guardian" in response.json()["detail"].lower()
