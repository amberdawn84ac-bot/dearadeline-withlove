import json
import math
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.classrooms import Submission, save_response
from app.curriculum.classroom import Scene
from app.curriculum.interactive_models import (
    ActivityWork,
    Interaction,
    checked_work,
    evaluate_interaction,
    mass_balance,
    water_heating,
)
from fastapi import HTTPException
from pydantic import ValidationError

from tests.test_classroom import blueprint, scene


def spec(kind="water_heating", **extra):
    return Interaction(
        kind=kind,
        prediction_prompt="What changes when energy is added?",
        observation_prompt="Explain the result using your observations.",
        **extra,
    )


def model_scene(kind="water_heating", **extra):
    return Scene(
        **{**scene(0), "type": "interactive", "interaction": spec(kind, **extra)}
    )


@pytest.mark.parametrize(
    "energy,temp,solid,liquid,gas",
    [
        (0, -20, 1, 0, 0),
        (4.2, 0, 1, 0, 0),
        (20.9, 0, 0.5, 0.5, 0),
        (37.6, 0, 0, 1, 0),
        (79.44, 100, 0, 1, 0),
        (192.24, 100, 0, 0.5, 0.5),
        (305.04, 100, 0, 0, 1),
    ],
)
def test_heating_curve_has_correct_phase_boundaries_and_latent_heat(
    energy, temp, solid, liquid, gas
):
    result = water_heating(energy)
    for key, expected in {
        "temperature_c": temp,
        "solid_fraction": solid,
        "liquid_fraction": liquid,
        "gas_fraction": gas,
    }.items():
        assert result[key] == pytest.approx(expected, abs=1e-10)
    assert result["mass_g"] == 100


def test_heating_all_inputs_preserve_mass_and_particle_fractions():
    last = -math.inf
    for tenth in range(3301):
        result = evaluate_interaction(spec(), {"energy_kj": tenth / 10})
        assert result["temperature_c"] >= last - 1e-10
        assert sum(
            result[k] for k in ("solid_fraction", "liquid_fraction", "gas_fraction")
        ) == pytest.approx(1)
        assert all(
            -1e-10 <= result[k] <= 1 + 1e-10
            for k in ("solid_fraction", "liquid_fraction", "gas_fraction")
        )
        assert result["mass_g"] == 100
        last = result["temperature_c"]


@pytest.mark.parametrize("soda", [0, 0.1, 5, 50])
@pytest.mark.parametrize("vinegar", [0, 10, 50, 200])
def test_mass_cannot_disappear_or_fall_below_empty_assembly(soda, vinegar):
    for system in ("open", "closed"):
        for progress in (0, 0.5, 1):
            r = mass_balance(soda, vinegar, progress, system)
            assert r["scale_g"] + r["escaped_g"] == pytest.approx(r["initial_g"])
            assert r["scale_g"] >= 150
            assert r["co2_g"] <= soda + vinegar
            if system == "closed":
                assert r["scale_g"] == r["initial_g"]
                assert r["retained_gas_g"] == r["co2_g"]


def test_mass_uses_stoichiometry_and_limiting_reactant():
    assert mass_balance(0.840066, 120.104, 1, "open")["co2_g"] == pytest.approx(
        0.440095
    )
    assert mass_balance(50, 10, 1, "open")["co2_g"] == pytest.approx(
        0.5 / 60.052 * 44.0095
    )
    assert mass_balance(0, 200, 1, "open")["co2_g"] == 0


def test_molecule_builder_preserves_extra_atoms():
    good = evaluate_interaction(spec("molecule_builder"), {"H": 2, "O": 1, "C": 0})
    extra = evaluate_interaction(spec("molecule_builder"), {"H": 2, "O": 1, "C": 1})
    assert good["matches"] and not extra["matches"]
    assert extra["unused_atoms"]["C"] == 1
    assert extra["counts"] == {"H": 2, "O": 1, "C": 1}
    with pytest.raises(ValueError):
        evaluate_interaction(spec("molecule_builder"), {"H": 2.5, "O": 1, "C": 0})


@pytest.mark.parametrize("bad", [-1, 331, float("inf"), float("nan"), "10", True])
def test_model_rejects_out_of_domain_or_non_numeric_inputs(bad):
    with pytest.raises(ValueError):
        evaluate_interaction(spec(), {"energy_kj": bad})


def test_diagram_validates_real_edges_and_narration_targets():
    nodes = [
        {"id": "a", "label": "Evidence", "detail": "The observations we can inspect."},
        {"id": "b", "label": "Claim", "detail": "The explanation to be tested."},
    ]
    edges = [{"source": "a", "target": "b", "label": "supports or challenges"}]
    actual = model_scene("diagram", nodes=nodes, edges=edges)
    assert evaluate_interaction(actual.interaction, {"node_id": "a"}) == {
        "node_id": "a"
    }
    data = actual.model_dump()
    data["actions"][0]["node_id"] = "absent"
    with pytest.raises(ValidationError):
        Scene(**data)
    with pytest.raises(ValidationError):
        spec("diagram", nodes=nodes, edges=[{**edges[0], "target": "absent"}])


def test_prediction_is_saved_before_results_and_kept_when_explanation_changes():
    actual = model_scene()
    prediction = ActivityWork(
        stage="prediction", prediction="I think ice warms continuously."
    )
    prior = checked_work(actual, prediction, None)
    assert "output" not in prior
    observation = ActivityWork(
        stage="observation",
        prediction=prediction.prediction,
        inputs={"energy_kj": 20.9},
        trials=[{"energy_kj": 4.2}, {"energy_kj": 20.9}],
    )
    with pytest.raises(ValueError):
        checked_work(actual, observation, None)
    result = checked_work(actual, observation, prior)
    assert result["results"][1]["output"]["temperature_c"] == 0
    assert result["prediction"] == prediction.prediction
    with pytest.raises(ValueError):
        checked_work(
            actual,
            observation.model_copy(
                update={"prediction": "Changed after seeing results"}
            ),
            prior,
        )
    with pytest.raises(ValueError):
        checked_work(actual, prediction, result)
    with pytest.raises(ValidationError):
        ActivityWork(**{**observation.model_dump(), "output": {"temperature_c": 999}})


@pytest.mark.asyncio
async def test_activity_endpoint_restores_results_and_replays_original_prediction_after_observations():
    actual = model_scene()
    bp = blueprint()
    bp["scenes"][0]["type"] = "interactive"
    document = {
        "format_version": "openmaic-classroom-v1",
        "phase": "ready",
        "blueprint": bp,
        "scenes": [actual.model_dump(), *[scene(i) for i in range(1, 4)]],
        "canonical_slug": "matter",
        "responses": {},
    }
    ledger = {}
    conn = AsyncMock()
    conn.transaction = MagicMock(return_value=AsyncMock())

    async def fetchrow(query, *args):
        return (
            {"id": "experience", "metadataJson": document}
            if 'FROM "StudentExperience"' in query
            else ledger.get(args[1])
        )

    async def insert(query, *args):
        ledger[args[-1]] = {"lessonId": "experience", "content": json.loads(args[-2])}
        return "attempt"

    conn.fetchrow.side_effect = fetchrow
    conn.fetchval.side_effect = insert
    prediction = Submission(
        scene_id="s0",
        text="I expect a continuous rise.",
        submission_key="prediction-1",
        activity=ActivityWork(
            stage="prediction", prediction="I expect a continuous rise."
        ),
    )
    observations = Submission(
        scene_id="s0",
        text="Temperature stayed at zero while ice melted.",
        submission_key="observation-1",
        activity=ActivityWork(
            stage="observation",
            prediction=prediction.text,
            inputs={"energy_kj": 20.9},
            trials=[{"energy_kj": 20.9}],
        ),
    )
    with patch("app.api.classrooms.get_db_conn", new=AsyncMock(return_value=conn)):
        with pytest.raises(HTTPException) as exc:
            await save_response("child", "unit", observations)
        assert exc.value.status_code == 422
        first = await save_response("child", "unit", prediction)
        assert "output" not in document["responses"]["s0"]["activity"]
        await save_response("child", "unit", observations)
        saved = deepcopy(document["responses"]["s0"])
        assert saved["activity"]["output"]["temperature_c"] == 0
        assert await save_response("child", "unit", prediction) == first
        assert document["responses"]["s0"] == saved
        with pytest.raises(HTTPException) as exc:
            await save_response(
                "child",
                "unit",
                prediction.model_copy(update={"text": "different work"}),
            )
        assert exc.value.status_code == 409
    assert len(ledger) == 2


def test_earlier_saved_notes_survive_prediction_and_observation_upgrade():
    actual = model_scene()
    prior = checked_work(
        actual,
        ActivityWork(stage="prediction", prediction="I think it warms."),
        {"earlier_notes": "My earlier measurements."},
    )
    assert prior["earlier_notes"] == "My earlier measurements."
    saved = checked_work(
        actual,
        ActivityWork(
            stage="observation",
            prediction="I think it warms.",
            inputs={"energy_kj": 20.9},
            trials=[{"energy_kj": 20.9}],
        ),
        prior,
    )
    assert saved["earlier_notes"] == "My earlier measurements."


def test_client_cannot_submit_boolean_measurement_or_invented_outputs():
    with pytest.raises(ValidationError):
        ActivityWork(
            stage="observation",
            prediction="Test prediction.",
            inputs={"energy_kj": True},
            trials=[],
        )
