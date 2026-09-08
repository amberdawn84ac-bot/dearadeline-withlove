"""Unauthenticated admin and experiments routes must not serve."""
from fastapi.testclient import TestClient

from app.api.student_auth import mint_student_token
from app.main import app

client = TestClient(app)


def _student_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_student_token('student-123')}"}


def test_admin_env_check_requires_auth():
    response = client.get("/admin/env-check")
    assert response.status_code == 401
    assert "users_total" not in response.text


def test_admin_env_check_brain_prefix_requires_auth():
    response = client.get("/brain/admin/env-check")
    assert response.status_code == 401
    assert "users_total" not in response.text


def test_admin_seed_requires_auth():
    response = client.post("/admin/seed")
    assert response.status_code == 401


def test_student_cannot_read_admin_env_check():
    response = client.get("/admin/env-check", headers=_student_headers())
    assert response.status_code == 403
    assert "users_total" not in response.text


def test_experiments_list_requires_auth():
    response = client.get("/experiments")
    assert response.status_code == 401


def test_experiments_detail_requires_auth():
    response = client.get("/experiments/exp-elephant-toothpaste")
    assert response.status_code == 401


def test_experiments_start_requires_auth():
    response = client.post("/experiments/exp-elephant-toothpaste/start")
    assert response.status_code == 401


def test_experiments_brain_prefix_requires_auth():
    response = client.get("/brain/experiments")
    assert response.status_code == 401


def test_signed_in_student_can_list_experiments():
    response = client.get("/experiments", headers=_student_headers())
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(item.get("id") == "exp-elephant-toothpaste" for item in body)
