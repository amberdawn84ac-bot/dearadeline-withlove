import json
import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from app.services.science_lab import ScienceLabSpec, LabNotebook, NOTEBOOK_PREFIX, notebook_from_message, update_notebook
from app.services.instructional_resources import prepare_instructional_resource
from app.services.sequence_evidence import evidence_from_prior_sessions


def lab():
    return {
        "question": "How does light exposure affect growth?", "investigation_kind": "controlled_experiment",
        "prediction_prompt": "Predict and explain.", "independent_variable": "Light hours", "dependent_variable": "Height",
        "controls_or_limits": ["Same species, water and soil; small sample."], "safety": ["Wash hands after handling soil."],
        "columns": [{"key": "hours", "label": "Light", "unit": "h", "kind": "number"}, {"key": "height", "label": "Height", "unit": "cm", "kind": "number"}],
        "graph": {"x_key": "hours", "y_key": "height", "kind": "scatter"},
        "claim_prompt": "What does the data support?", "evidence_prompt": "Which measurements support it?", "reasoning_prompt": "Explain the mechanism and limits.",
    }


def messages():
    return [{"role": "assistant", "content": "Collect actual data", "resource_block": {"block_type": "SCIENCE_LAB", "metadata": {"resource_id": "issued-1", "lab": lab(), "decision": {"block_id": "measure"}}}}]


def test_real_notebook_roundtrip_and_revision_preserve_measurements():
    notebook = LabNotebook(resource_id="issued-1", prediction="More light may help.", rows=[{"hours": "4", "height": "5.2"}, {"hours": "8", "height": "7"}])
    saved = notebook_from_message(NOTEBOOK_PREFIX + notebook.model_dump_json())
    history = messages()
    assert update_notebook(history, saved) == "measure"
    assert history[0]["resource_block"]["metadata"]["notebook"]["rows"][0]["height"] == "5.2"
    revised = saved.model_copy(update={"claim": "Growth differed; other factors may matter."})
    update_notebook(history, revised)
    assert history[0]["resource_block"]["metadata"]["notebook"]["claim"] == revised.claim


@pytest.mark.parametrize("changes", [{"graph": {"x_key": "unknown", "y_key": "height"}}, {"independent_variable": ""}, {"columns": [lab()["columns"][0], lab()["columns"][0]]}])
def test_lab_rejects_incoherent_graphs_or_variables(changes):
    with pytest.raises(ValidationError):
        ScienceLabSpec.model_validate({**lab(), **changes})


@pytest.mark.parametrize("rows", [[{"height": "NaN"}], [{"made_up_column": "2"}], [{"height": "not a measurement"}]])
def test_data_must_match_issued_columns_and_be_finite(rows):
    with pytest.raises(ValueError):
        update_notebook(messages(), LabNotebook(resource_id="issued-1", rows=rows))


def test_cannot_attach_data_to_another_session_resource():
    with pytest.raises(ValueError):
        update_notebook(messages(), LabNotebook(resource_id="somebody-elses-lab"))


def test_prior_session_evidence_is_real_data_not_an_awarded_status():
    history = messages()
    update_notebook(history, LabNotebook(resource_id="issued-1", rows=[{"hours": "4", "height": "5.2"}]))
    result = evidence_from_prior_sessions([{"title": "Measure", "status": "completed", "messagesJson": json.dumps(history)}])
    assert result[0]["lab_notebooks"][0]["notebook"]["rows"][0]["height"] == "5.2"
    assert "mastery" not in result[0]


@pytest.mark.asyncio
async def test_maker_emits_structured_lab_with_blank_observation_table():
    state = {"current_block": {"block_id": "measure", "content": "Measure growth"}, "status": "active", "messages": []}
    decision = {"block_id": "measure", "objective": "Measure growth", "instructional_need": "Collect actual data", "teaching_move": "Run experiment", "purpose": "Test a claim", "success_evidence": "Data and justified conclusion", "route": "generate", "resource_type": "science_lab", "duration_minutes": 30}
    resource = {"title": "Light and growth", "teaching": "Compare plants while controlling other factors.", "materials": ["plants"], "steps": ["Check materials and record measurements."], "evidence_prompt": "Explain the results.", "lab": lab()}
    llm = SimpleNamespace(ainvoke=AsyncMock(side_effect=[SimpleNamespace(content=json.dumps(p)) for p in (decision, resource)]))
    result = await prepare_instructional_resource(state, "Make the lab", lambda: llm, json.loads)
    block = result["instructional_resource"]
    assert block["block_type"] == "SCIENCE_LAB"
    assert "notebook" not in block["metadata"]
    assert block["metadata"]["lab"]["columns"][1]["unit"] == "cm"


@pytest.mark.asyncio
async def test_draft_notebook_cannot_advance_current_activity(monkeypatch):
    from app.api import spaces
    initial = {"version": 3, "status": "active", "student_id": "student-1", "plan_item_id": "unit-1", "current_block": {"block_id": "measure"}, "messages": messages(), "current_block_index": 0, "total_blocks": 1}
    async def identity(value): return value
    monkeypatch.setattr(spaces, "_load_or_create", AsyncMock(return_value=({}, {})))
    monkeypatch.setattr(spaces, "_state", lambda *_: initial)
    for name in ("_attach_offer_catalog", "_attach_mastery_context", "_attach_household_learners"):
        monkeypatch.setattr(spaces, name, identity)
    monkeypatch.setattr("app.services.curriculum_state.get_curriculum_state", AsyncMock(return_value={"skills": []}))
    monkeypatch.setattr(spaces, "_evaluate_turn", AsyncMock(return_value=spaces._TurnEvaluation(adeline_message="Saved.", evaluation="correct", recommended_action="advance", is_waiting_for_user=False)))
    apply = AsyncMock(return_value={})
    monkeypatch.setattr(spaces, "_apply_transition", apply)
    before = copy.deepcopy(initial)
    body = spaces.SpaceTurnRequest(user_message=NOTEBOOK_PREFIX + LabNotebook(resource_id="issued-1", rows=[{"height": "5.2"}]).model_dump_json(), expected_version=3)
    await spaces.space_turn("student-1", "unit-1", body)
    assert apply.call_args.args[2].recommended_action == "stay"
    assert apply.call_args.args[2].evaluation == "not_answered"
    assert initial["messages"] == before["messages"]
