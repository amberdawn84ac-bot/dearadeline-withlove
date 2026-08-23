"""Child-consent security boundaries."""
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
RAW_TOKEN = "a" * 64


def test_student_cannot_create_consent_token_for_another_learner():
    with patch("app.api.coppa.get_current_user_id", return_value="student-1"):
        response = client.post("/api/coppa/token", json={
            "studentId": "student-2",
            "token": RAW_TOKEN,
            "expiresAt": (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat(),
        })
    assert response.status_code == 403


def test_pending_consent_token_is_hashed_at_rest():
    conn = AsyncMock()
    conn.fetchrow.return_value = {"id": "student-1"}
    with (
        patch("app.api.coppa.get_current_user_id", return_value="student-1"),
        patch("app.api.coppa._get_conn", new=AsyncMock(return_value=conn)),
    ):
        response = client.post("/api/coppa/token", json={
            "studentId": "student-1",
            "token": RAW_TOKEN,
            "expiresAt": (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat(),
        })

    assert response.status_code == 200
    update_call = conn.fetchrow.await_args
    assert update_call.args[2] == hashlib.sha256(RAW_TOKEN.encode()).hexdigest()
    assert update_call.args[2] != RAW_TOKEN


def test_guardian_approval_is_audited_and_token_is_single_use():
    conn = AsyncMock()
    conn.fetchrow.return_value = {
        "id": "student-1",
        "parentEmail": "Parent@Example.com",
        "coppaTokenExpiresAt": datetime.now(timezone.utc) + timedelta(hours=1),
        "coppaVerified": False,
    }
    with patch("app.api.coppa._get_conn", new=AsyncMock(return_value=conn)):
        response = client.post("/api/coppa/verify", json={"token": RAW_TOKEN})

    assert response.status_code == 200
    issued_sql = "\n".join(str(call.args[0]) for call in conn.execute.await_args_list)
    assert '"coppaPendingToken" = NULL' in issued_sql
    assert 'INSERT INTO "ChildPrivacyConsent"' in issued_sql
    assert "verified_parent_email" in issued_sql
