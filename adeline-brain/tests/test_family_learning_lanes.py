from datetime import date

from app.api.experience_builder import skill_connections_for_contract
from app.api.learning_plan import (
    LessonSuggestion,
    _family_investigation_for_learner,
    _family_investigation_suggestion,
    _individual_skill_targets,
)


def suggestion(**updates) -> LessonSuggestion:
    values = {
        "id": "skill-1",
        "title": "Compare ratios",
        "track": "APPLIED_MATHEMATICS",
        "description": "Use ratios in a new example.",
        "emoji": "📐",
        "priority": 1.0,
        "source": "zpd",
        "concept_id": "ratio-concept",
        "sequence_policy": "HARD",
        "sequence_state": "READY",
        "sequence_target_id": "ratio-concept",
        "prerequisite_readiness": 1.0,
        "delivery_mode": "INDIVIDUAL_SKILL",
    }
    values.update(updates)
    return LessonSuggestion(**values)


def test_locked_skill_cannot_be_attached_to_family_investigation():
    ready_math = suggestion()
    locked_literacy = suggestion(
        id="locked-reading",
        title="Analyze rhetoric",
        track="ENGLISH_LITERATURE",
        concept_id="rhetoric-concept",
        sequence_target_id="rhetoric-concept",
        sequence_state="LOCKED",
        prerequisite_readiness=0.2,
    )

    targets = _individual_skill_targets([ready_math, locked_literacy], "7")

    assert [target.suggestion_id for target in targets] == ["skill-1"]
    assert targets[0].mastery_eligible is True


def test_siblings_share_the_investigation_but_keep_distinct_skill_targets():
    catalog = (("saved-canonical", "Railroads and Power", "TRUTH_HISTORY", "Compare the records."),)
    plan_date = date(2026, 8, 26)
    younger = _family_investigation_suggestion(
        "household-1",
        plan_date,
        [suggestion(title="Count equal groups", concept_id="equal-groups")],
        "3",
        catalog,
    )
    older = _family_investigation_suggestion(
        "household-1",
        plan_date,
        [suggestion(title="Compare rates of change", concept_id="rates")],
        "9",
        catalog,
    )

    assert younger is not None and older is not None
    assert younger.id == older.id
    assert younger.canonical_slug == older.canonical_slug == "saved-canonical"
    assert younger.title == older.title == "Railroads and Power"
    assert younger.individual_skill_targets[0].title == "Count equal groups"
    assert older.individual_skill_targets[0].title == "Compare rates of change"
    assert younger.sequence_policy == older.sequence_policy == "OPEN"
    assert younger.bridge_required is older.bridge_required is False


def test_durable_household_choice_replaces_private_skill_attachments():
    catalog = (("saved-canonical", "Bread Chemistry", "CREATION_SCIENCE", "Test fermentation."),)
    shared = _family_investigation_suggestion(
        "household-1", date(2026, 8, 26), [suggestion(title="Count batches")], "3", catalog,
    )
    assert shared is not None

    older = _family_investigation_for_learner(
        shared,
        [suggestion(title="Calculate baker's percentages", concept_id="percent")],
        "10",
    )

    assert older.id == shared.id
    assert older.title == shared.title
    assert older.individual_skill_targets[0].title == "Calculate baker's percentages"
    assert older.individual_skill_targets[0].working_level == "10"


def test_family_card_is_withheld_when_no_pregenerated_lesson_is_ready():
    assert _family_investigation_suggestion(
        "household-1", date(2026, 8, 26), [suggestion()], "7", (),
    ) is None


def test_only_authored_interdisciplinary_connections_are_woven_into_theme():
    targets = [
        {
            "suggestion_id": "math-1",
            "domain": "math",
            "title": "Compare percentages",
            "track": "APPLIED_MATHEMATICS",
        },
        {
            "suggestion_id": "literacy-1",
            "domain": "literacy",
            "title": "Analyze an argument",
            "track": "ENGLISH_LITERATURE",
        },
    ]
    contract = {
        "experience_design": {
            "disciplines_integrated": ["history", "statistics"],
            "integration_rationale": "Statistics are needed to test railroad land-grant claims.",
        },
    }

    integrated, separate = skill_connections_for_contract(contract, targets)

    assert [item["suggestion_id"] for item in integrated] == ["math-1"]
    assert integrated[0]["integration_status"] == "INTEGRATED"
    assert [item["suggestion_id"] for item in separate] == ["literacy-1"]
    assert separate[0]["integration_status"] == "SEPARATE"
