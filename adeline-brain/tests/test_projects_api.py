"""
Tests for Projects API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_projects():
    """Test listing all projects."""
    response = client.get("/projects")
    
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "projects" in data
    assert data["total"] >= 0


def test_list_projects_filter_by_track():
    """Test filtering projects by track."""
    response = client.get("/projects?track=CREATIVE_ECONOMY")
    
    assert response.status_code == 200
    data = response.json()
    assert all(p["track"] == "CREATIVE_ECONOMY" for p in data["projects"])


def test_list_projects_filter_by_difficulty():
    """Test filtering projects by difficulty."""
    response = client.get("/projects?difficulty=1")
    
    assert response.status_code == 200
    data = response.json()
    assert all(p["difficulty"] == 1 for p in data["projects"])


def test_get_project_by_id():
    """Test getting a single project."""
    # First get list to find a valid project ID
    list_response = client.get("/projects")
    projects = list_response.json()["projects"]
    
    if len(projects) > 0:
        project_id = projects[0]["id"]
        response = client.get(f"/projects/{project_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert "steps" in data
        assert "materials" in data


def test_get_project_not_found():
    """Test getting non-existent project."""
    response = client.get("/projects/nonexistent-project-id")
    
    assert response.status_code == 404


def test_start_project():
    """Test starting a project."""
    # Get a valid project ID
    list_response = client.get("/projects")
    projects = list_response.json()["projects"]
    
    if len(projects) > 0:
        project_id = projects[0]["id"]
        payload = {
            "student_id": "test-student-123",
            "project_id": project_id,
        }
        
        response = client.post(f"/projects/{project_id}/start", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id


def test_seal_project():
    """Test sealing a completed project."""
    # Get a valid project ID
    list_response = client.get("/projects")
    projects = list_response.json()["projects"]
    
    if len(projects) > 0:
        project_id = projects[0]["id"]
        payload = {
            "student_id": "test-student-123",
            "project_id": project_id,
        }
        
        response = client.post(f"/projects/{project_id}/seal", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "credit_hours" in data
        assert "credit_type" in data
        assert data["credit_hours"] > 0
