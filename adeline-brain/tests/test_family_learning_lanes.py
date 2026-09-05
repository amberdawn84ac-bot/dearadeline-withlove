from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.api.experience_builder import skill_connections_for_contract
from app.api.learning_plan import (
    GradeLevelStandard,
    LessonSuggestion,
    _family_investigation_for_learner,
    _family_investigation_suggestion,
    _individual_skill_targets,
    _learner_progression_targets,
    _progression_map_status,
    _standard_suggestion,
)

# These tests exercise the no-override fallback path only (the existing
# algorithmic rotation); the override lookup itself is covered separately in
# test_family_investigation_override.py.
_no_override = patch(
    "app.api.learning_plan.family_investigation_override_store.get",
    new=AsyncMock(return_value=None),
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


def test_progression_checklist_uses_exact_targets_across_tracks_not_starters():
    science = suggestion(
        id="science-1",
        title="Run a controlled plant experiment",
        track="CREATION_SCIENCE",
        concept_id="controlled-variables",
        delivery_mode="INDIVIDUAL_EXTENSION",
    )
    literacy = suggestion(
        id="literacy-1",
        title="Use text evidence to support a claim",
        track="ENGLISH_LITERATURE",
        concept_id="text-evidence",
    )
    starter = suggestion(
        id="starter-precalculus",
        title="Pre-Calculus Concepts",
        concept_id=None,
        standard_code=None,
        source="explore",
    )

    targets = _learner_progression_targets([starter, science, literacy], "9")

    assert [(target.domain, target.title) for target in targets] == [
        ("science", "Run a controlled plant experiment"),
        ("literacy", "Use text evidence to support a claim"),
    ]
    assert all(target.title != "Pre-Calculus Concepts" for target in targets)


def test_progression_status_counts_placed_standard_targets_as_mapped():
    targets = _learner_progression_targets([
        suggestion(
            concept_id=None,
            standard_code="MATHEM_G7_7.N.1.1",
            prerequisite_concept_ids=[],
            prerequisite_standard_ids=[],
        ),
        suggestion(
            id="reading",
            track="ENGLISH_LITERATURE",
            concept_id="text-evidence",
            title="Use text evidence",
        ),
    ], "7")

    status = _progression_map_status(targets)

    math = next(item for item in status.tracks if item.track == "APPLIED_MATHEMATICS")
    assert math.map_status == "PLACED_STANDARD_SEQUENCE"
    assert status.mapped_target_count == 2
    assert status.placed_standard_target_count == 1


def test_standard_card_does_not_prepend_the_generic_literacy_hook():
    standard = GradeLevelStandard(
        standard_id="7.1.S.1",
        subject="English Language Arts",
        grade=7,
        description=(
            "Students will actively listen using agreed-upon discussion rules "
            "with control of verbal and nonverbal cues."
        ),
        mastered=False,
        priority=1,
        track="ENGLISH_LITERATURE",
        lesson_hook="What does this text say, and how do you know?",
    )

    result = _standard_suggestion(standard)

    assert result.title == "Listen closely and contribute thoughtfully in discussion"
    assert "What does this text say" not in result.title


def test_sequential_standard_waits_for_the_earlier_lane_target():
    standard = GradeLevelStandard(
        standard_id="MATHEM_G7_7.N.2.1",
        subject="Mathematics",
        grade=7,
        description="Students will solve proportional problems.",
        mastered=False,
        priority=1,
        track="APPLIED_MATHEMATICS",
        progression_lane="applied_mathematics:n",
        progression_mode="SEQUENTIAL",
        progression_ordinal=12,
        progression_ready=False,
    )

    result = _standard_suggestion(standard)

    assert result.sequence_policy == "HARD"
    assert result.sequence_state == "LOCKED"
    assert result.prerequisite_readiness == 0


def test_first_unfinished_sequential_target_is_ready():
    standard = GradeLevelStandard(
        standard_id="ENGLIS_G7_7.3.R.1",
        subject="English Language Arts",
        grade=7,
        description="Students will cite textual evidence.",
        mastered=False,
        priority=1,
        track="ENGLISH_LITERATURE",
        progression_lane="english_literature:r",
        progression_mode="SEQUENTIAL",
        progression_ordinal=1,
        progression_ready=True,
    )

    result = _standard_suggestion(standard)

    assert result.sequence_policy == "HARD"
    assert result.sequence_state == "READY"


@pytest.mark.asyncio
async def test_siblings_share_the_investigation_but_keep_distinct_skill_targets():
    catalog = (("saved-canonical", "Railroads and Power", "TRUTH_HISTORY", "Compare the records."),)
    plan_date = date(2026, 8, 26)
    with _no_override:
        younger = await _family_investigation_suggestion(
            "household-1",
            plan_date,
            [suggestion(title="Count equal groups", concept_id="equal-groups")],
            "3",
            catalog,
        )
        older = await _family_investigation_suggestion(
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
    assert younger.learner_progression_targets[0].concept_id == "equal-groups"
    assert older.learner_progression_targets[0].concept_id == "rates"
    assert younger.sequence_policy == older.sequence_policy == "OPEN"
    assert younger.bridge_required is older.bridge_required is False


@pytest.mark.asyncio
async def test_durable_household_choice_replaces_private_skill_attachments():
    catalog = (("saved-canonical", "Bread Chemistry", "CREATION_SCIENCE", "Test fermentation."),)
    with _no_override:
        shared = await _family_investigation_suggestion(
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


@pytest.mark.asyncio
async def test_family_card_is_withheld_when_no_pregenerated_lesson_is_ready():
    assert await _family_investigation_suggestion(
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


def test_statistics_does_not_turn_precalculus_into_themed_busywork():
    contract = {
        "experience_design": {
            "disciplines_integrated": ["history", "statistics"],
            "integration_rationale": "Learners graph railroad land-grant data.",
        },
    }
    integrated, separate = skill_connections_for_contract(contract, [{
        "suggestion_id": "precalc",
        "domain": "math",
        "title": "Use polynomial functions and limits",
        "track": "APPLIED_MATHEMATICS",
        "working_level": "11",
    }])

    assert integrated == []
    assert separate[0]["suggestion_id"] == "precalc"


def test_real_science_and_design_targets_can_join_one_family_investigation():
    contract = {
        "experience_design": {
            "disciplines_integrated": ["science", "creative design"],
            "integration_rationale": "A controlled plant test determines the greenhouse design.",
        },
        "real_world_task": {
            "description": "Observe plant growth, then design a tested greenhouse model.",
            "deliverable": "A model and evidence log.",
        },
    }
    integrated, separate = skill_connections_for_contract(contract, [
        {
            "suggestion_id": "science",
            "domain": "science",
            "title": "Use observations in a controlled plant experiment",
            "track": "CREATION_SCIENCE",
            "working_level": "6",
        },
        {
            "suggestion_id": "design",
            "domain": "creative_economy",
            "title": "Design and communicate a useful product",
            "track": "CREATIVE_ECONOMY",
            "working_level": "6",
        },
    ])

    assert [target["suggestion_id"] for target in integrated] == ["science", "design"]
    assert separate == []
    assert "working level 6" in integrated[0]["contribution_prompt"]
