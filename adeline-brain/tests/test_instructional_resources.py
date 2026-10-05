"""Need-first routing, canonical boundaries, and failure recovery."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.services.instructional_resources import (
    InstructionalResource, ResourceDecision, context_for_resources,
    prepare_instructional_resource,
)
from app.services.resource_toolbox import RESOURCE_TOOLBOX
from typing import get_args


def state():
    return {
        "status": "active", "current_block": {"block_id": "observe", "content": "Separate observation from inference"},
        "learner_depth": {"grade": 7}, "messages": [],
        "offer_catalog": [{"id": "museum:1", "title": "Evidence photo"}],
        "evaluated_skills": [{"skillId": "observation", "status": "developing"}],
    }


def decision(route="generate", **changes):
    return {
        "block_id": "observe", "objective": "Separate observation from inference",
        "instructional_need": "Inference stated as observation", "teaching_move": "Contrast two descriptions",
        "purpose": "Discriminate evidence from conclusions", "success_evidence": "Explain which is directly visible",
        "route": route, "resource_type": "comparison" if route == "generate" else "none", **changes,
    }


def maker(**changes):
    return {
        "title": "What does the print show?", "teaching": "An observation describes what you can directly detect.",
        "materials": [], "steps": ["Compare: a muddy print is visible; someone crossed the garden."],
        "evidence_prompt": "Which is an observation, and what would test the other claim?",
        "source_ids": [], **changes,
    }


def factory(*payloads):
    llm = SimpleNamespace(ainvoke=AsyncMock(side_effect=[SimpleNamespace(content=json.dumps(p)) for p in payloads]))
    return lambda: llm, llm


@pytest.mark.asyncio
async def test_separate_planner_and_maker_create_only_contract_resource():
    make_llm, llm = factory(decision(), maker())
    result = await prepare_instructional_resource(state(), "It proves he crossed the garden", make_llm, json.loads)
    assert llm.ainvoke.await_count == 2
    planner_context = json.loads(llm.ainvoke.call_args_list[0].args[0][1].content)
    maker_context = json.loads(llm.ainvoke.call_args_list[1].args[0][1].content)
    assert planner_context["evaluated_skills"][0]["status"] == "developing"
    assert maker_context["decision"]["objective"] == decision()["objective"]
    assert "resource_toolbox" in planner_context
    assert maker_context["selected_tool_contract"] == RESOURCE_TOOLBOX["comparison"]
    assert "resource_toolbox" not in maker_context
    block = result["instructional_resource"]
    assert block["metadata"]["does_not_award_mastery"]
    assert "Which is an observation" in block["content"]
    assert result["current_block"] == state()["current_block"]


@pytest.mark.asyncio
@pytest.mark.parametrize("route,ids", [("none", []), ("existing", ["museum:1"])])
async def test_no_maker_for_conversation_or_existing_resources(route, ids):
    make_llm, llm = factory(decision(route, resource_ids=ids))
    result = await prepare_instructional_resource(state(), "Ready", make_llm, json.loads)
    assert llm.ainvoke.await_count == 1
    assert "instructional_resource" not in result
    assert result["resource_decision"]["route"] == route


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [decision(block_id="different"), decision(objective="An independent curriculum"), decision("existing", resource_ids=["invented"])])
async def test_unknown_target_or_resource_fails_open(bad):
    original = state()
    make_llm, llm = factory(bad)
    assert await prepare_instructional_resource(original, "Hi", make_llm, json.loads) is original
    assert llm.ainvoke.await_count == 1


@pytest.mark.asyncio
async def test_maker_failure_or_invented_source_preserves_activity():
    original = state()
    make_llm, _ = factory(decision(), maker(source_ids=["made-up"]))
    assert await prepare_instructional_resource(original, "Hi", make_llm, json.loads) is original
    llm = SimpleNamespace(ainvoke=AsyncMock(side_effect=RuntimeError("provider unavailable")))
    assert await prepare_instructional_resource(original, "Hi", lambda: llm, json.loads) is original


@pytest.mark.asyncio
async def test_real_world_uses_maker_but_completed_space_does_not():
    make_llm, llm = factory(decision("real_world", resource_type="investigation"), maker())
    result = await prepare_instructional_resource(state(), "We have soil", make_llm, json.loads)
    assert result["resource_decision"]["route"] == "real_world"
    assert llm.ainvoke.await_count == 2
    completed = {**state(), "status": "completed"}
    assert await prepare_instructional_resource(completed, "Hi", make_llm, json.loads) is completed
    assert llm.ainvoke.await_count == 2


def test_contract_rejects_empty_generation_and_unbounded_steps():
    with pytest.raises(ValidationError):
        ResourceDecision.model_validate(decision(resource_type="none"))
    with pytest.raises(ValidationError):
        InstructionalResource.model_validate(maker(steps=["x" * 301]))


def test_context_does_not_pass_scheduling_probability_as_proof():
    context = context_for_resources({**state(), "track_mastery": {"score": 0.99}}, "I guessed")
    assert "track_mastery" not in context
    assert context["newest_learner_evidence"] == "I guessed"


def test_every_resource_type_has_a_teaching_contract():
    types = set(get_args(ResourceDecision.model_fields["resource_type"].annotation)) - {"none"}
    assert types == set(RESOURCE_TOOLBOX)
    for spec in RESOURCE_TOOLBOX.values():
        assert all(spec.get(key) for key in ("definition", "use_when", "avoid_when", "must_include", "success", "exit", "max_minutes"))


def test_vocabulary_requires_a_specific_barrier_and_brief_duration():
    with pytest.raises(ValidationError):
        ResourceDecision.model_validate(decision(resource_type="vocabulary_support"))
    with pytest.raises(ValidationError):
        ResourceDecision.model_validate(decision(resource_type="vocabulary_support", blocked_term="corroborate", duration_minutes=15))
    valid = ResourceDecision.model_validate(decision(resource_type="vocabulary_support", blocked_term="corroborate", duration_minutes=3))
    assert valid.blocked_term == "corroborate"
