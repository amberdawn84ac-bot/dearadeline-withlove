from app.api.journal import SealRequest, _evidence_proficiency
from app.curriculum.experience_contract import annotate_experience, validate_experience
from app.schemas.api_models import LessonRequest, Track
from app.api.experience_builder import (
    canonical_resource_query,
    has_verified_history_source,
    shared_family_canonical_slug,
)
from app.services.investigation_printable import build_investigation_pdf


def test_experience_requires_action_and_demonstration():
    blocks = annotate_experience([
        {"block_type": "TEXT", "content": "Why did the creek change course?"},
        {"block_type": "PRIMARY_SOURCE", "content": "Examine these two maps."},
    ])
    errors = validate_experience(blocks)
    assert any("action or creation" in error for error in errors)
    assert any("demonstration" in error for error in errors)


def test_reflection_records_exposure_not_mastery():
    request = SealRequest(
        lesson_id="lesson-1",
        track=Track.CREATION_SCIENCE,
        learner_reflection="I changed my prediction after the second observation.",
    )
    assert _evidence_proficiency(request) == "DEVELOPING"


def test_scored_demonstration_can_reach_understanding():
    request = SealRequest(
        lesson_id="lesson-1",
        track=Track.CREATION_SCIENCE,
        quiz_results=[{"correct": True}, {"correct": True}, {"correct": True}, {"correct": False}],
    )
    assert _evidence_proficiency(request) == "UNDERSTANDING"


def test_extending_requires_strong_score_plus_real_artifact():
    request = SealRequest(
        lesson_id="lesson-1",
        track=Track.CREATION_SCIENCE,
        quiz_results=[{"correct": True}] * 10,
        artifact_refs=["portfolio://artifact-1"],
    )
    assert _evidence_proficiency(request) == "EXTENDING"


def test_siblings_share_canonical_but_keep_individual_standards():
    first = LessonRequest(student_id="first", track=Track.CREATION_SCIENCE, topic="Creek Detectives", grade_level="1", required_standard_codes=["1.LS1.1"])
    older = LessonRequest(student_id="older", track=Track.CREATION_SCIENCE, topic="Creek Detectives", grade_level="7", required_standard_codes=["7.ESS3.2"])
    assert shared_family_canonical_slug(first) == shared_family_canonical_slug(older)
    assert first.required_standard_codes != older.required_standard_codes


def test_truth_history_requests_and_requires_item_level_primary_sources():
    request = LessonRequest(
        student_id="historian",
        track=Track.TRUTH_HISTORY,
        topic="Railroads and Power",
        grade_level="9",
    )
    query = canonical_resource_query(request)
    assert query.topic == "Railroads and Power"
    assert query.resource_types == ("PRIMARY_SOURCE",)
    assert query.interactive_preferred is False
    assert query.limit == 8

    search_page = [{
        "resource_type": "PRIMARY_SOURCE",
        "availability": "COLLECTION_SEARCH",
        "source_url": "https://example.org/search",
        "provider": "Example Archive",
    }]
    actual_item = [{**search_page[0], "availability": "VERIFIED_API_ITEM"}]
    curated_item = [{**search_page[0], "availability": "VERIFIED_ARCHIVE_ITEM"}]
    assert has_verified_history_source(search_page) is False
    assert has_verified_history_source(actual_item) is True
    assert has_verified_history_source(curated_item) is True


def test_truth_history_archive_query_removes_framing_question():
    request = LessonRequest(
        student_id="historian",
        track=Track.TRUTH_HISTORY,
        topic="Railroads, Oil, and the Robber Barons: Building America or Consolidating Power?",
        grade_level="9",
    )

    assert canonical_resource_query(request).topic == "Railroads, Oil, and the Robber Barons"


def test_only_direct_experience_builder_is_mounted():
    from app.main import app
    paths = {route.path for route in app.routes}
    assert "/experience/build" in paths
    assert "/brain/experience/build" in paths
    assert "/experience/printable" in paths
    assert "/brain/experience/printable" in paths
    assert "/lesson/build" not in paths
    assert "/brain/lesson/build" not in paths


def test_author_contract_budgets_repetition_not_learning_quality():
    from app.curriculum.canonical_author import CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT

    prompt = CANONICAL_LESSON_AUTHOR_SYSTEM_PROMPT
    assert "under roughly 24,000 characters" in prompt
    assert "accurate evidence" in prompt
    assert "meaningful action" in prompt
    assert "observable" in prompt
    assert "CONCISE IS NOT SHALLOW" in prompt
    assert '  "visual_assets": []' not in prompt
    assert "Do not repeat family roles inside every block" in prompt
    assert "actual routed items" in prompt
    assert "archive search page" in prompt


def test_printable_is_same_experience_and_hides_internal_standards():
    pdf = build_investigation_pdf(
        title="Creek Detectives", topic="erosion", grade_level="Grade 3",
        blocks=[
            {"block_type": "PRIMARY_SOURCE", "experience_stage": "DISCOVERY", "title": "Compare the creek maps", "content": "Notice what moved and record your evidence.", "is_silenced": False},
            {"block_type": "EXPERIMENT", "experience_stage": "ACTION", "title": "Test a stream table", "content": "Change one variable and measure the result.", "is_silenced": False},
        ],
    )
    assert pdf.startswith(b"%PDF")
    assert b"3-ESS2-1" not in pdf
