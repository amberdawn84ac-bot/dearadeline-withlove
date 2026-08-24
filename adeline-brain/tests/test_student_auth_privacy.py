"""Age-aware learner-first registration and guardian approval."""
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_registration_does_not_return_a_student_session_before_approval():
    conn = AsyncMock()
    conn.transaction = MagicMock()
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
            "age_band": "UNDER_13",
            "parent_name": "Guardian",
            "parent_email": "guardian@example.com",
            "parent_verification_token": "b" * 64,
        })

    assert response.status_code == 200
    body = response.json()
    assert body["requires_parent_verification"] is True
    assert body["token"] is None
    insert_call = conn.execute.await_args_list[0]
    assert insert_call.args[4] == "PLACEMENT"
    assert len(conn.execute.await_args_list) == 1


def test_learner_13_or_older_can_start_and_link_a_parent_later():
    conn = AsyncMock()
    conn.transaction = MagicMock()
    conn.fetchrow.return_value = {
        "profile": {
            "id": "student-older",
            "name": "Older Learner",
            "role": "STUDENT",
            "username": "older_learner",
            "gradeLevel": "9",
            "linkCode": "123456ABCDEF",
            "xp": 0,
            "adeCoins": 0,
            "reputation": 0,
            "coppaVerified": True,
        }
    }
    with (
        patch("app.api.student_auth.get_db_conn", new=AsyncMock(return_value=conn)),
        patch("app.api.student_auth.uuid.uuid4", return_value="student-older"),
        patch("app.api.student_auth.mint_student_token", return_value="student-session"),
    ):
        response = client.post("/auth/student/register", json={
            "display_name": "Older Learner",
            "username": "older_learner",
            "pin": "1234",
            "grade_level": "9",
            "age_band": "13_OR_OLDER",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["requires_parent_verification"] is False
    assert body["token"] == "student-session"
    assert body["user"]["link_code"] == "123456ABCDEF"
    insert_call = conn.execute.await_args_list[0]
    assert insert_call.args[4] == "9"
    assert insert_call.args[8] is None
    assert insert_call.args[9] is None
    assert insert_call.args[10] is True
    assert insert_call.args[11] is None
    assert insert_call.args[12] is None


def test_under_13_registration_requires_parent_contact():
    response = client.post("/auth/student/register", json={
        "display_name": "Learner",
        "username": "learner_2",
        "pin": "1234",
        "grade_level": "PLACEMENT",
        "age_band": "UNDER_13",
    })

    assert response.status_code == 422
    assert "parent or guardian" in str(response.json()).lower()


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
