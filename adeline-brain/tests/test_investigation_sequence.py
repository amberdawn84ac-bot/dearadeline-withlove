import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from app.services.investigation_sequence import InvestigationSequence, SequenceRequest, canonical_topics, plan_investigation


def plan():
    return {"title": "Forensic scientist", "shared_question": "What can evidence establish?", "sessions": [
        {"title": "Observe", "objective": "Separate inference", "track": "CREATION_SCIENCE", "investigation": "Compare prints", "evidence_required": "Justify a distinction", "resource_hint": "comparison", "depends_on": []},
        {"title": "Measure", "objective": "Test a claim", "track": "CREATION_SCIENCE", "investigation": "Safe controlled comparison", "evidence_required": "Actual data and conclusion", "resource_hint": "science_lab notebook", "depends_on": [1]},
    ]}


def test_session_outline_passes_into_existing_canonical_queue_with_shared_context():
    topics = canonical_topics(InvestigationSequence.model_validate(plan()))
    assert len(topics) == 2
    assert "What can evidence establish?" in topics[1]["canonical_topic"]
    assert "science_lab notebook" in topics[1]["canonical_topic"]
    assert "Builds on sessions: 1" in topics[1]["canonical_topic"]
    assert "Actual data" in topics[1]["canonical_topic"]


def test_cannot_depend_on_future_sessions_or_duplicate_session_titles():
    for change in ({"depends_on": [2]}, {"title": "Observe"}):
        invalid = plan()
        invalid["sessions"][1].update(change)
        with pytest.raises(ValidationError):
            InvestigationSequence.model_validate(invalid)


@pytest.mark.asyncio
async def test_planning_uses_family_and_materials_but_does_not_queue_or_author_lessons():
    llm = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content=json.dumps(plan()))))
    result = await plan_investigation(SequenceRequest(topic="Forensic scientist", session_count=2, available_materials="paper, ruler"), [{"gradeLevel": "7"}], lambda: llm, json.loads)
    supplied = json.loads(llm.ainvoke.call_args.args[0][1].content)
    assert supplied["available_materials"] == "paper, ruler"
    assert supplied["family_learners"] == [{"gradeLevel": "7"}]
    assert len(result["experiences"]) == 2
    assert "blocks" not in result
    assert "HISTORY:" in llm.ainvoke.call_args.args[0][0].content


@pytest.mark.asyncio
async def test_count_mismatch_is_rejected_before_queue_changes():
    llm = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content=json.dumps(plan()))))
    with pytest.raises(ValueError):
        await plan_investigation(SequenceRequest(topic="Forensic scientist", session_count=3), [], lambda: llm, json.loads)
