"""
Tests for Spaced Repetition (SM-2) API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_db_conn():
    """Mock database connection."""
    with patch('app.api.learning_records._get_conn') as mock:
        yield mock


def test_get_due_reviews_empty(mock_db_conn):
    """Test getting due reviews when none are due."""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    response = client.get("/learning/reviews/student-123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["reviews"]) == 0


def test_get_due_reviews_with_cards(mock_db_conn):
    """Test getting due reviews with cards."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": "card-1",
            "conceptId": "concept-photosynthesis",
            "conceptName": "Photosynthesis",
            "track": "CREATION_SCIENCE",
            "repetitions": 2,
            "dueAt": yesterday,
        },
        {
            "id": "card-2",
            "conceptId": "concept-civil-war",
            "conceptName": "American Civil War",
            "track": "TRUTH_HISTORY",
            "repetitions": 1,
            "dueAt": yesterday,
        },
    ]
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    response = client.get("/learning/reviews/student-123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["reviews"]) == 2
    assert data["reviews"][0]["concept_name"] == "Photosynthesis"


def test_submit_review_quality_0(mock_db_conn):
    """Test submitting review with quality 0 (blank)."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "interval": 1,
        "easeFactor": 2.5,
        "repetitions": 0,
    }
    mock_conn.execute.return_value = None
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    payload = {
        "student_id": "student-123",
        "concept_id": "concept-test",
        "quality": 0,
        "track": "CREATION_SCIENCE",
    }
    
    response = client.post("/learning/reviews", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "new_interval" in data
    assert "ease_factor" in data


def test_submit_review_quality_5(mock_db_conn):
    """Test submitting review with quality 5 (easy)."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "interval": 7,
        "easeFactor": 2.5,
        "repetitions": 3,
    }
    mock_conn.execute.return_value = None
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    payload = {
        "student_id": "student-123",
        "concept_id": "concept-test",
        "quality": 5,
        "track": "CREATION_SCIENCE",
    }
    
    response = client.post("/learning/reviews", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["new_interval"] > 7  # Should increase
    assert data["repetitions"] == 4


def test_submit_review_invalid_quality(mock_db_conn):
    """Test that invalid quality rating is rejected."""
    payload = {
        "student_id": "student-123",
        "concept_id": "concept-test",
        "quality": 6,  # Invalid - must be 0-5
        "track": "CREATION_SCIENCE",
    }
    
    response = client.post("/learning/reviews", json=payload)
    
    assert response.status_code == 422


def test_submit_review_creates_new_card(mock_db_conn):
    """Test that submitting review creates card if it doesn't exist."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = None  # No existing card
    mock_conn.execute.return_value = None
    mock_db_conn.return_value.__aenter__.return_value = mock_conn
    
    payload = {
        "student_id": "student-123",
        "concept_id": "concept-new",
        "quality": 4,
        "track": "CREATION_SCIENCE",
    }
    
    response = client.post("/learning/reviews", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["repetitions"] == 1  # First review
