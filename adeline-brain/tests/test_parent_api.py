"""
Tests for Parent Dashboard API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
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
    mock_conn.fetch.return_value = [
        {
            "id": "student-1",
            "name": "Alice Smith",
            "email": "alice@example.com",
            "gradeLevel": "8",
            "interests": ["science", "art"],
            "createdAt": "2024-01-01T00:00:00Z",
        }
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
        {"role": "PARENT"},  # Parent role check
        None,  # Email doesn't exist
    ]
    mock_conn.execute.return_value = None
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    payload = {
        "name": "Bob Smith",
        "email": "bob@example.com",
        "grade_level": "6",
    }
    
    response = client.post("/api/parent/students", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bob Smith"
    assert data["email"] == "bob@example.com"


def test_add_student_duplicate_email(mock_parent_auth, mock_db_conn):
    """Test that duplicate email is rejected."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.side_effect = [
        {"role": "PARENT"},
        {"id": "existing-student"},  # Email exists
    ]
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    payload = {
        "name": "Bob Smith",
        "email": "existing@example.com",
        "grade_level": "6",
    }
    
    response = client.post("/api/parent/students", json=payload)
    
    assert response.status_code == 409


def test_get_family_dashboard(mock_parent_auth, mock_db_conn):
    """Test family dashboard aggregation."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {"role": "PARENT"}
    mock_conn.fetch.side_effect = [
        [{"id": "student-1", "name": "Alice"}],  # Students
        [{"creditHours": 2.5}],  # Transcript for student-1
        [],  # Recent activity
    ]
    mock_conn.fetchval.side_effect = [5, 3, 2]  # lessons, books, projects
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    response = client.get("/api/parent/dashboard")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_students"] == 1
    assert data["family_total_credits"] == 2.5
    assert len(data["students"]) == 1
    assert data["students"][0]["lessons_completed"] == 5


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
