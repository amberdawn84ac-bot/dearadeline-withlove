"""Behavior checks for the unit, evidence and adaptation contracts."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.curriculum.learning_method import (
    STAGES,
    validate_learning_method,
    validate_character_integrity,
    validate_real_world_contract,
)
from app.services.curriculum_state import select_skill_work, evaluate_evidence
from app.connections.family_unit_store import FamilyUnitStore


def stages():
    return [
        dict(
            stage=s,
            prompt="Authored teaching",
            block_ids=[],
            evidence_required=["notes"],
            activity="Measure runoff",
        )
        for s in STAGES
    ]


def test_stages_are_structural_and_ordered():
    assert not validate_learning_method(stages(), set())
    assert validate_learning_method(list(reversed(stages())), set())
    assert validate_learning_method(stages()[:-1], set())


def test_write_and_experience_require_evidence():
    method = stages()
    method[2]["evidence_required"] = []
    method[4]["activity"] = ""
    assert len(validate_learning_method(method, set())) == 2


def test_service_requires_a_recipient_and_deliverable():
    assert validate_real_world_contract(None, claims_service=True)
    assert not validate_real_world_contract(None)
    assert validate_real_world_contract({"recipient": "household"})


def test_character_cannot_change_truth():
    original = [
        {
            "block_id": "a",
            "content": "DNA does not establish guilt.",
            "evidence": [{"source_url": "primary"}],
        }
    ]
    validate_character_integrity(
        original, [dict(original[0], metadata={"character": "Detective"})]
    )
    with pytest.raises(ValueError):
        validate_character_integrity(
            original, [dict(original[0], content="DNA establishes guilt.")]
        )


def test_ordered_skill_does_not_skip_for_a_convenient_unit_fit():
    result = select_skill_work(
        subject="math",
        next_skill={"skill_id": "ratio-1", "sequence_state": "READY"},
        opportunities=[
            {
                "skill_id": "ratio-2",
                "task": "dilute",
                "evidence_requirement": "calculation",
            }
        ],
    )
    assert result["individual"][0]["skill_id"] == "ratio-1"
    assert not result["integrated"]


def test_explicit_identity_task_and_evidence_required_for_fit():
    target = {"skill_id": "ratio", "sequence_state": "READY"}
    assert select_skill_work(
        subject="math",
        next_skill=target,
        opportunities=[{"skill_id": "ratio", "task": "measure"}],
    )["individual"]
    assert select_skill_work(
        subject="math",
        next_skill=target,
        opportunities=[
            {
                "skill_id": "ratio",
                "task": "measure",
                "evidence_requirement": "calculation",
            }
        ],
    )["integrated"]


def test_mastered_science_foundation_is_reviewed():
    result = select_skill_work(
        subject="science",
        next_skill=None,
        opportunities=[],
        foundations=[
            {"skill_id": "cell", "status": "secure"},
            {"skill_id": "chromosome", "status": "missing"},
        ],
    )
    assert [f["instruction"] for f in result["foundations"]] == ["REVIEW", "TEACH"]


def connection():
    conn = AsyncMock()
    conn.transaction = MagicMock()
    conn.transaction.return_value.__aenter__ = AsyncMock()
    conn.transaction.return_value.__aexit__ = AsyncMock(return_value=False)
    return conn


@pytest.mark.asyncio
async def test_unit_read_does_not_advance_even_if_a_space_completed():
    from app.api.learning_plan import _family_investigation_suggestions

    current = {
        "id": "queue",
        "unitId": "unit",
        "experienceId": "exp",
        "canonicalTopic": "Forensic science",
        "track": "CREATION_SCIENCE",
        "position": 0,
    }
    with (
        patch(
            "app.api.learning_plan.family_unit_store.current",
            new=AsyncMock(return_value=current),
        ),
        patch(
            "app.api.learning_plan._shared_investigation_completed",
            new=AsyncMock(return_value=True),
        ) as legacy,
    ):
        result = await _family_investigation_suggestions("household", [], "7")
    assert len(result) == 1
    assert result[0].shared_investigation_id == "family-unit-queue-exp"
    legacy.assert_not_awaited()


@pytest.mark.asyncio
async def test_incomplete_unit_cannot_advance():
    conn = connection()
    conn.fetchrow.return_value = {"unitId": "unit", "status": "active"}
    conn.fetchval.return_value = 1
    with patch(
        "app.connections.family_unit_store.get_db_conn",
        new=AsyncMock(return_value=conn),
    ):
        with pytest.raises(ValueError, match="every experience"):
            await FamilyUnitStore().advance("household", "queue")
    assert not any("SET status" in c.args[0] for c in conn.execute.await_args_list)


@pytest.mark.asyncio
async def test_completed_unit_retry_does_not_advance_next_unit():
    conn = connection()
    conn.fetchrow.return_value = {"unitId": "unit", "status": "completed"}
    with patch(
        "app.connections.family_unit_store.get_db_conn",
        new=AsyncMock(return_value=conn),
    ):
        await FamilyUnitStore().advance("household", "queue")
    assert not any("UPDATE" in c.args[0] for c in conn.execute.await_args_list)


@pytest.mark.asyncio
async def test_evaluation_retry_does_not_increment_mastery():
    conn = connection()
    conn.fetchrow.side_effect = [
        {"content": json.dumps({"text": "Measured 2:1"}), "studentId": "child"},
        None,
        {"result": "demonstrated", "reasoning": "Calculation checked"},
    ]
    with patch(
        "app.services.curriculum_state.get_db_conn", new=AsyncMock(return_value=conn)
    ):
        result = await evaluate_evidence(
            attempt_id="attempt",
            student_id="child",
            skill_id="ratio",
            evaluator_id="parent",
            result="demonstrated",
            reasoning="Calculation checked",
        )
    assert not result["new_evaluation"]
    conn.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_evidence_review_updates_state_only_after_evaluation():
    conn = connection()
    conn.fetchrow.side_effect = [{"content": {"text": "Measured 2:1"}}, {"id": "eval"}]
    with patch(
        "app.services.curriculum_state.get_db_conn", new=AsyncMock(return_value=conn)
    ):
        await evaluate_evidence(
            attempt_id="a",
            student_id="child",
            skill_id="ratio",
            evaluator_id="parent",
            result="demonstrated",
            reasoning="Checked",
        )
    assert "StudentSkillState" in conn.execute.await_args.args[0]
    assert conn.execute.await_args.args[-1] == "a"


def test_forensic_unit_contains_ten_distinct_canonicals():
    from app.curriculum.builtin_canonicals import unit_experiences, builtin_canonical
    from app.curriculum.kitchen_case_file import TOPIC, TRACK, _slug
    from app.curriculum.family_style import is_current_family_canonical

    experiences = unit_experiences(TOPIC, TRACK)
    assert len(experiences) == 10
    records = [
        builtin_canonical(_slug(e["canonical_topic"], e["track"])) for e in experiences
    ]
    assert len({r["topic_slug"] for r in records}) == 10
    for record in records:
        assert is_current_family_canonical(record["blocks"])
        assert not validate_learning_method(
            record["stages"], {b["block_id"] for b in record["blocks"]}
        )
        contract = record["blocks"][0]["metadata"]["canonical_contract"]
        assert len(contract["unit_plan"]["lessons"]) == 1


@pytest.mark.asyncio
async def test_character_adaptation_preserves_all_shared_facts_and_sources():
    from app.agents.adapter import AdaptationRequest, adapt_canonical_for_student

    canonical = {
        "blocks": [
            {
                "block_id": "a",
                "block_type": "TEXT",
                "content": "One clue does not establish guilt.",
                "evidence": [{"source_url": "primary"}],
            }
        ]
    }
    younger = await adapt_canonical_for_student(
        canonical,
        AdaptationRequest(
            grade_level="5", track="CREATION_SCIENCE", character={"name": "Observer"}
        ),
    )
    older = await adapt_canonical_for_student(
        canonical,
        AdaptationRequest(
            grade_level="10",
            track="CREATION_SCIENCE",
            character={"name": "Investigator"},
        ),
    )
    validate_character_integrity(canonical["blocks"], younger)
    validate_character_integrity(canonical["blocks"], older)
    assert (
        younger[0]["metadata"]["learner_entry"]["character"]
        != older[0]["metadata"]["learner_entry"]["character"]
    )


def test_api_decodes_database_json_before_returning_saved_notes():
    from app.api.curriculum import _record

    result = _record(
        {
            "content": '{"text":"first observation"}',
            "sources": '["primary record"]',
            "id": "attempt",
        }
    )
    assert result["content"]["text"] == "first observation"
    assert result["sources"] == ["primary record"]


@pytest.mark.asyncio
async def test_unit_advancement_completes_and_activates_inside_one_transaction():
    conn = connection()
    conn.fetchrow.return_value = {"unitId": "unit", "status": "active"}
    conn.fetchval.return_value = 0
    with patch(
        "app.connections.family_unit_store.get_db_conn",
        new=AsyncMock(return_value=conn),
    ):
        await FamilyUnitStore().advance("household", "queue")
    conn.transaction.assert_called_once()
    statements = [c.args[0] for c in conn.execute.await_args_list]
    assert "pg_advisory_xact_lock" in statements[0]
    assert "status='completed'" in statements[1]
    assert "status='active'" in statements[2]


@pytest.mark.asyncio
async def test_revision_must_reference_same_child_and_experience():
    from app.api.curriculum import AttemptRequest, submit_evidence
    from fastapi import HTTPException

    conn = connection()
    conn.fetchrow.return_value = {
        "studentId": "other-child",
        "canonicalSlug": "c",
        "lessonId": "l",
    }
    body = AttemptRequest(
        canonical_slug="c",
        lesson_id="l",
        parent_attempt_id="old",
        kind="revision",
        content={"text": "revised"},
        submission_key="unique",
    )
    with patch("app.api.curriculum.get_db_conn", new=AsyncMock(return_value=conn)):
        with pytest.raises(HTTPException) as error:
            await submit_evidence("child", body, "parent")
    assert error.value.status_code == 400
    conn.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cached_today_projects_the_current_unit_without_authoring():
    from app.api.learning_plan import (
        LearningPlanResponse,
        FamilyLearningContext,
        LessonSuggestion,
        _attach_individual_lessons,
    )

    context = FamilyLearningContext(household_id="household", shared_with_siblings=True)
    old = LessonSuggestion(
        id="old",
        title="Old unit",
        track="CREATION_SCIENCE",
        description="",
        emoji="x",
        priority=1,
        source="family",
        delivery_mode="FAMILY_INVESTIGATION",
    )
    current = old.model_copy(update={"id": "current", "title": "Current unit"})
    plan = LearningPlanResponse.model_construct(
        student_id="child",
        placement=None,
        grade_standards=[],
        family_context=context,
        suggestions=[old],
        family_investigations=[old],
        family_investigation=old,
    )
    with (
        patch(
            "app.api.learning_plan._family_investigation_suggestions",
            new=AsyncMock(return_value=[current]),
        ),
        patch(
            "app.api.learning_plan._upcoming_family_investigations",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.api.learning_plan.individual_lessons_for",
            new=AsyncMock(return_value=[]),
        ),
    ):
        result = await _attach_individual_lessons(plan, refresh_family=True)
    assert result.family_investigation.id == "current"
    assert [s.id for s in result.suggestions] == ["current"]


@pytest.mark.asyncio
async def test_database_revision_invalidates_a_redis_hit():
    from app.connections.canonical_store import CanonicalStore

    store = CanonicalStore()
    cached = {"content_revision": "old", "title": "Old facts", "blocks": []}
    fresh = {"content_revision": "new", "title": "Revised facts", "blocks": []}
    with (
        patch.object(
            store, "_redis_get", new=AsyncMock(return_value=json.dumps(cached))
        ),
        patch.object(
            store,
            "_db_revision",
            new=AsyncMock(
                return_value={"contentRevision": "new", "pendingApproval": False}
            ),
        ),
        patch.object(store, "_db_get", new=AsyncMock(return_value=fresh)),
        patch.object(store, "_redis_set", new=AsyncMock()),
    ):
        assert await store.get("not-a-repository-canonical") == fresh


@pytest.mark.asyncio
async def test_current_redis_revision_avoids_loading_content_again():
    from app.connections.canonical_store import CanonicalStore

    store = CanonicalStore()
    cached = {"content_revision": "same", "title": "Shared facts", "blocks": []}
    with (
        patch.object(
            store, "_redis_get", new=AsyncMock(return_value=json.dumps(cached))
        ),
        patch.object(
            store,
            "_db_revision",
            new=AsyncMock(
                return_value={"contentRevision": "same", "pendingApproval": False}
            ),
        ),
        patch.object(store, "_db_get", new=AsyncMock()) as full_read,
        patch.object(store, "_redis_set", new=AsyncMock()),
    ):
        assert await store.get("not-a-repository-canonical") == cached
    full_read.assert_not_awaited()
