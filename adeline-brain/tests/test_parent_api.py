"""
Tests for Parent Dashboard API endpoints.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_parent_auth():
    """Mock authentication for parent user."""
    with patch('app.api.parent.get_current_user_id') as mock:
        mock.return_value = 'parent-123'
        yield mock


@pytest.fixture
def mock_db_conn():
    """Mock database connection."""
    with patch('app.api.parent._get_conn') as mock:
        yield mock


def test_list_students_success(mock_parent_auth, mock_db_conn):
    """Test listing students for a parent."""
    # Mock database responses
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"role": "PARENT"}
    mock_conn.fetch.side_effect = [
        [{
            "id": "student-1",
            "name": "Alice Smith",
            "email": "alice@example.com",
            "gradeLevel": "8",
            "interests": ["science", "art"],
            "createdAt": datetime(2024, 1, 1, tzinfo=timezone.utc),
        }],
        [],
    ]
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    response = client.get("/api/parent/students")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Alice Smith"
    assert data[0]["grade_level"] == "8"


def test_list_students_forbidden_non_parent(mock_parent_auth, mock_db_conn):
    """Test that non-parent users cannot list students."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"role": "STUDENT"}
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    response = client.get("/api/parent/students")
    
    assert response.status_code == 403


def test_add_student_success(mock_parent_auth, mock_db_conn):
    """Test adding a new student."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.side_effect = [
        {"role": "PARENT", "email": "parent@example.com"},  # Parent role check
        None,  # Player identity doesn't exist
    ]
    mock_conn.execute.return_value = None
    # asyncpg's conn.transaction() is a sync call returning an async context
    # manager, not itself awaitable — AsyncMock's default child mocking makes
    # mock_conn.transaction() return a coroutine, which `async with` rejects.
    mock_conn.transaction = MagicMock()
    mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=None)
    mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_db_conn.return_value.__aenter__.return_value = mock_conn

    payload = {
        "name": "Bob Smith",
        "username": "bob_smith",
        "pin": "1234",
        "grade_level": "6",
        "privacy_consent": True,
        "privacy_notice_version": "2026-08-23",
    }
    
    response = client.post("/api/parent/students", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bob Smith"
    assert data["email"] == "bob_smith@mobile.adelineworld.local"
    issued_sql = "\n".join(str(call.args[0]) for call in mock_conn.execute.await_args_list)
    assert 'INSERT INTO "ChildPrivacyConsent"' in issued_sql
    assert "CREATE TABLE" not in issued_sql


def test_add_student_requires_explicit_privacy_consent(mock_parent_auth, mock_db_conn):
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"role": "PARENT", "email": "parent@example.com"}
    mock_db_conn.return_value.__aenter__.return_value = mock_conn

    response = client.post("/api/parent/students", json={
        "name": "Bob Smith",
        "username": "bob_smith",
        "pin": "1234",
        "grade_level": "6",
        "privacy_consent": False,
    })

    assert response.status_code == 422
    assert mock_conn.execute.await_count == 0


def test_add_student_duplicate_player_name(mock_parent_auth, mock_db_conn):
    """Test that duplicate player identity is rejected."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.side_effect = [
        {"role": "PARENT", "email": "parent@example.com"},
        {"id": "existing-student"},
    ]
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    payload = {
        "name": "Bob Smith",
        "username": "existing_player",
        "pin": "1234",
        "grade_level": "6",
        "privacy_consent": True,
    }
    
    response = client.post("/api/parent/students", json=payload)
    
    assert response.status_code == 409


@patch('app.services.rate_limit.enforce_rate_limit', new_callable=AsyncMock)
def test_get_family_dashboard_uses_bounded_batch_queries(mock_rate_limit, mock_parent_auth, mock_db_conn):
    """A multi-child family uses a fixed number of queries and keeps data isolated."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"role": "PARENT"}
    mock_conn.fetch.side_effect = [
        [
            {"id": "student-1", "name": "Alice", "gradeLevel": "8", "interests": ["science"]},
            {"id": "student-2", "name": "Ben", "gradeLevel": "10", "interests": ["history"]},
        ],
        [
            {"studentId": "student-1", "credits": 2.5},
            {"studentId": "student-2", "credits": 1.0},
        ],
        [
            {"student_id": "student-1", "lessons_completed": 5, "projects_sealed": 2,
             "last_activity": datetime(2024, 1, 2, tzinfo=timezone.utc), "active_track": "CREATION_SCIENCE"},
            {"student_id": "student-2", "lessons_completed": 3, "projects_sealed": 1,
             "last_activity": datetime(2024, 1, 3, tzinfo=timezone.utc), "active_track": "TRUTH_HISTORY"},
        ],
        [
            {"studentId": "student-1", "books_finished": 2},
            {"studentId": "student-2", "books_finished": 1},
        ],
        [
            {"studentId": "student-1", "planJson": {"suggestions": [{"title": "Water evidence", "canonical_slug": "water"}]}},
            {"studentId": "student-2", "planJson": {"suggestions": [{"title": "Labor records", "canonical_slug": "labor"}]}},
        ],
        [{"student_id": "student-2", "student_name": "Ben", "lesson_id": "lesson-2",
          "track": "TRUTH_HISTORY", "sealed_at": datetime(2024, 1, 3, tzinfo=timezone.utc),
          "title": "Reading company files"}],
    ]
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    response = client.get("/api/parent/dashboard")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_students"] == 2
    assert data["family_total_credits"] == 3.5
    assert len(data["students"]) == 2
    assert data["students"][0]["lessons_completed"] == 5
    assert data["students"][0]["learning"]["current_learning"][0]["title"] == "Water evidence"
    assert data["students"][1]["learning"]["current_learning"][0]["title"] == "Labor records"
    assert mock_conn.fetch.await_count == 6
    assert mock_conn.fetchval.await_count == 0
    issued_sql = "\n".join(
        str(call.args[0])
        for method in (mock_conn.fetch, mock_conn.fetchrow, mock_conn.fetchval)
        for call in method.await_args_list
        if call.args
    )
    assert '"JournalEntry"' not in issued_sql
    assert '"StudentBook"' not in issued_sql
    assert "student_journal" in issued_sql


def test_update_student(mock_parent_auth, mock_db_conn):
    """Test updating student profile."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"parentId": "parent-123"}
    mock_conn.execute.return_value = None
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    payload = {"name": "Alice Johnson", "grade_level": "9"}
    
    response = client.patch("/api/parent/students/student-1", json=payload)
    
    assert response.status_code == 200


def test_remove_student(mock_parent_auth, mock_db_conn):
    """Test removing student from family."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"parentId": "parent-123"}
    mock_conn.execute.return_value = None
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    response = client.delete("/api/parent/students/student-1")
    
    assert response.status_code == 200
    data = response.json()
    assert "removed" in data["message"].lower()
