"""Rich lesson visuals, actions, and code-owned activities."""

import pytest
from pydantic import ValidationError

from app.curriculum.classroom import Blueprint, Classroom, Scene, public_classroom
from app.curriculum.interactive_models import (
    Interaction,
    air_volume,
    evaluate_interaction,
    redact_interaction,
)
from app.curriculum.runtime_capabilities import authoring_capabilities


def blueprint():
    return {
        "title": "Mixtures",
        "understanding": "Ratios compare quantities multiplicatively.",
        "essential_question": "How can we compare mixtures?",
        "demonstration": "Compare and explain two new mixtures.",
        "integrated_tracks": ["CREATION_SCIENCE", "APPLIED_MATHEMATICS"],
        "roster": [
            {"id": "adeline", "name": "Adeline", "role": "teacher", "persona": "Warm, knowledgeable mentor."},
            {"id": "peer", "name": "Colleague", "role": "assistant", "persona": "Asks for evidence and clarification."},
        ],
        "scenes": [
            {"id": f"s{i}", "title": f"Compare mixture {i}", "type": "quiz" if i == 3 else "slide", "objective": "Explain the quantities.", "brief": "Show a concrete example and explain it."}
            for i in range(4)
        ],
        "next_revisit": "Connect ratios to graphs in another context.",
    }


def scene(i):
    return {
        "id": f"s{i}",
        "title": "Compare mixtures",
        "type": "quiz" if i == 3 else "slide",
        "content": "One cup to two cups gives a 1:2 ratio.",
        "actions": [{"role_id": "adeline", "text": "What changes when both amounts double?"}],
        "learner_task": "Explain the comparison.",
        "success_criteria": ["Use multiplicative reasoning."],
        "family_roles": {"elementary": "Draw amounts.", "middle": "Compare ratios.", "high_school": "Justify scaling."},
        **({"question": {"prompt": "Which equals 1:2?", "choices": [{"id": "a", "label": "2:4"}, {"id": "b", "label": "2:3"}], "answer": "a", "explanation": "Multiplying both amounts by two preserves the ratio."}} if i == 3 else {}),
    }


def _prompts():
    return {
        "prediction_prompt": "What do you expect to notice?",
        "observation_prompt": "Explain what changed and what stayed the same.",
    }


def test_visual_is_readable_and_actions_cannot_target_missing_parts():
    data = scene(0)
    data["visual"] = {
        "reading": "Ice keeps its shape until it melts.",
        "elements": [
            {"id": "chart", "type": "chart", "text": "States", "labels": ["Ice", "Water"], "values": [1, 2]},
            {"id": "photo", "type": "image", "alt": ""},
        ],
    }
    with pytest.raises(ValidationError):
        Scene(**data)
    data["visual"]["elements"][1]["alt"] = "A photograph of an ice cube on a plate."
    data["actions"] = [
        {"role_id": "adeline", "text": "Look at the chart.", "kind": "focus", "target_id": "missing"}
    ]
    with pytest.raises(ValidationError):
        Scene(**data)
    data["actions"][0]["target_id"] = "chart"
    assert Scene(**data).visual.elements[0].id == "chart"


def test_public_sequence_hides_order_and_reasons():
    plan = blueprint()
    plan["scenes"][1]["type"] = "interactive"
    data = scene(1)
    data["type"] = "interactive"
    data["interaction"] = {
        **_prompts(),
        "kind": "sequence",
        "steps": [
            {"id": "melt", "label": "Ice melts", "position": 2, "reason": "Heat changes the state."},
            {"id": "warm", "label": "Ice warms", "position": 1, "reason": "Temperature rises first."},
            {"id": "boil", "label": "Water boils", "position": 3, "reason": "A later energy change."},
        ],
    }
    built = [Scene(**(data if i == 1 else scene(i))) for i in range(4)]
    classroom = Classroom(blueprint=Blueprint(**plan), scenes=built)
    public = public_classroom(classroom)["scenes"][1]["interaction"]
    assert [step["id"] for step in public["steps"]] == ["boil", "melt", "warm"]
    assert "position" not in public["steps"][0]
    assert "reason" not in public["steps"][0]
    result = evaluate_interaction(classroom.scenes[1].interaction, {"order": "warm,melt,boil"})
    assert result["correct"] is True
    assert "position" not in result


def test_air_volume_keeps_pressure_times_volume_constant():
    spec = Interaction(kind="air_volume", **_prompts())
    products = []
    for volume in (20, 50, 100):
        result = evaluate_interaction(spec, {"volume_ml": volume})
        products.append(result["pressure_times_volume"])
        assert result == air_volume(volume)
    assert products[0] == pytest.approx(products[1]) == pytest.approx(5066.25)
    with pytest.raises(ValueError):
        evaluate_interaction(spec, {"volume_ml": 10})


def test_graph_and_matter_answers_are_recomputed():
    graph = Interaction(
        kind="graph_compare",
        series_a=[1, 3],
        series_b=[2, 3],
        series_a_label="Morning",
        series_b_label="Evening",
        **_prompts(),
    )
    assert evaluate_interaction(graph, {"index": 0, "choice": "b"})["correct"] is True
    assert evaluate_interaction(graph, {"index": 1, "choice": "a"})["correct"] is False
    matter = Interaction(kind="matter_properties", sample="sealed_air", **_prompts())
    selected = evaluate_interaction(matter, {"selected": "space,invisible,compressible"})
    assert selected["correct"] is True
    missed = evaluate_interaction(matter, {"selected": "cold"})
    assert missed["correct"] is False
    assert all("applicable" not in item for item in missed["items"])


def test_matching_rejects_partial_work_and_hides_keys():
    spec = Interaction(
        kind="matching",
        choices=[{"id": "gas", "label": "Gas"}, {"id": "solid", "label": "Solid"}],
        pairs=[
            {"id": "air", "prompt": "Air in a closed syringe", "match_id": "gas", "reason": "It fills and can be squeezed."},
            {"id": "ice", "prompt": "Ice cube", "match_id": "solid", "reason": "It keeps a shape."},
        ],
        **_prompts(),
    )
    public = spec.model_dump()
    redact_interaction(public)
    assert "match_id" not in public["pairs"][0]
    with pytest.raises(ValueError):
        evaluate_interaction(spec, {"matches": "air:gas"})
    assert evaluate_interaction(spec, {"matches": "air:gas,ice:solid"})["correct"] is True


def test_catalog_lists_the_new_mechanisms_without_promising_html():
    catalog = authoring_capabilities()
    ids = {item["id"] for item in catalog["mechanisms"]}
    assert {"air_volume", "graph_compare", "sequence", "matching", "matter_properties"} <= ids
    assert len(ids) == 13
    assert "generated_html_or_javascript_execution" in catalog["not_available"]
    assert catalog["delivery"]["slide"].startswith("Responsive prose")
