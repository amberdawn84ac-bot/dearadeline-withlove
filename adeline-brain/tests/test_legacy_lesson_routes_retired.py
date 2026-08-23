"""Only the canonical experience author may create full learner experiences."""
from app.main import app


def test_legacy_full_lesson_authoring_routes_are_not_mounted():
    paths = {route.path for route in app.routes}
    for path in {
        "/lesson/generate", "/lesson/stream", "/lesson/build", "/lesson/deliver",
        "/lesson/status/{job_id}",
        "/brain/lesson/generate", "/brain/lesson/stream", "/brain/lesson/build",
        "/brain/lesson/deliver", "/brain/lesson/status/{job_id}",
    }:
        assert path not in paths


def test_used_non_authoring_lesson_utilities_remain_available():
    paths = {route.path for route in app.routes}
    assert "/brain/lesson/scaffold" in paths
    assert "/brain/lesson/ask-context" in paths
    assert "/brain/lesson/student-state/{student_id}" in paths
    assert "/brain/experience/build" in paths
