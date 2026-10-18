"""Bounded classroom mechanisms. Author supplies pedagogy; code owns the physics."""

import math
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)


class DiagramNode(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=60)
    detail: str = Field(min_length=5, max_length=800)


class DiagramEdge(BaseModel):
    source: str
    target: str
    label: str = Field(min_length=1, max_length=80)


class Interaction(BaseModel):
    kind: Literal["water_heating", "mass_balance", "diagram", "molecule_builder"]
    prediction_prompt: str = Field(min_length=5, max_length=500)
    observation_prompt: str = Field(min_length=5, max_length=500)
    nodes: list[DiagramNode] = Field(default_factory=list, max_length=10)
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=16)
    formula: Literal["H2O", "CO2", "CH4"] = "H2O"

    @model_validator(mode="after")
    def valid_graph(self):
        if self.kind == "diagram":
            ids = {n.id for n in self.nodes}
            if len(ids) != len(self.nodes) or len(ids) < 2:
                raise ValueError("A diagram needs 2–10 uniquely identified nodes")
            if not self.edges or any(
                e.source not in ids or e.target not in ids or e.source == e.target
                for e in self.edges
            ):
                raise ValueError(
                    "Diagram connections must join existing distinct nodes"
                )
        elif self.nodes or self.edges:
            raise ValueError("Nodes and edges belong only to diagrams")
        return self


class ActivityWork(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: Literal["prediction", "observation"]
    prediction: str = Field(min_length=1, max_length=1500)
    inputs: dict[str, StrictFloat | StrictInt | StrictStr] = Field(
        default_factory=dict, max_length=6
    )
    trials: list[dict[str, StrictFloat | StrictInt | StrictStr]] = Field(
        default_factory=list, max_length=12
    )


def bounded(inputs, key, minimum, maximum):
    value = inputs.get(key)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ValueError(
            f"{key} must be a finite number between {minimum} and {maximum}"
        )
    return value


def water_heating(energy_kj):
    """100 g pure water at 1 atm, initially ice at -20 C. Approximate constants."""
    q = energy_kj * 10  # kJ / 100 g -> J/g
    melt_start, melt_end = 42, 376
    boil_start, boil_end = 794.4, 3050.4
    if q < melt_start:
        temperature, solid, liquid, gas = -20 + q / 2.1, 1, 0, 0
    elif q < melt_end:
        f = (q - melt_start) / 334
        temperature, solid, liquid, gas = 0, 1 - f, f, 0
    elif q < boil_start:
        temperature, solid, liquid, gas = (q - melt_end) / 4.184, 0, 1, 0
    elif q < boil_end:
        f = (q - boil_start) / 2256
        temperature, solid, liquid, gas = 100, 0, 1 - f, f
    else:
        temperature, solid, liquid, gas = 100 + (q - boil_end) / 2, 0, 0, 1
    return {
        "temperature_c": temperature,
        "solid_fraction": solid,
        "liquid_fraction": liquid,
        "gas_fraction": gas,
        "mass_g": 100,
        "energy_kj": energy_kj,
    }


def mass_balance(soda_g, vinegar_g, progress, system):
    # 5% acetic acid by mass; NaHCO3 + CH3COOH -> CH3COONa + H2O + CO2.
    gas = min(soda_g / 84.0066, vinegar_g * 0.05 / 60.052) * 44.0095 * progress
    initial = (
        150 + soda_g + vinegar_g
    )  # 150 g assembly includes collector in closed mode.
    escaped = gas if system == "open" else 0
    return {
        "initial_g": initial,
        "scale_g": initial - escaped,
        "escaped_g": escaped,
        "retained_gas_g": gas - escaped,
        "total_accounted_g": initial,
        "co2_g": gas,
        "progress": progress,
    }


def evaluate_interaction(spec: Interaction, inputs: dict) -> dict:
    if spec.kind == "water_heating":
        if set(inputs) != {"energy_kj"}:
            raise ValueError("Water heating needs energy_kj only")
        return water_heating(bounded(inputs, "energy_kj", 0, 330))
    if spec.kind == "mass_balance":
        if set(inputs) != {"soda_g", "vinegar_g", "progress", "system"} or inputs.get(
            "system"
        ) not in {"open", "closed"}:
            raise ValueError(
                "Mass model needs soda_g, vinegar_g, progress and open/closed system"
            )
        return mass_balance(
            bounded(inputs, "soda_g", 0, 50),
            bounded(inputs, "vinegar_g", 0, 200),
            bounded(inputs, "progress", 0, 1),
            inputs["system"],
        )
    if spec.kind == "diagram":
        if set(inputs) != {"node_id"} or inputs["node_id"] not in {
            n.id for n in spec.nodes
        }:
            raise ValueError("Choose a node that exists in this diagram")
        return {"node_id": inputs["node_id"]}
    if set(inputs) != {"H", "O", "C"}:
        raise ValueError("Molecule builder needs H, O and C counts")
    counts = {k: bounded(inputs, k, 0, 10) for k in ("H", "O", "C")}
    if any(v != int(v) for v in counts.values()):
        raise ValueError("Atom counts must be whole numbers")
    target = {
        "H2O": {"H": 2, "O": 1, "C": 0},
        "CO2": {"H": 0, "O": 2, "C": 1},
        "CH4": {"H": 4, "O": 0, "C": 1},
    }[spec.formula]
    return {
        "matches": counts == target,
        "counts": counts,
        "target": spec.formula,
        "unused_atoms": {k: max(0, counts[k] - target[k]) for k in counts},
        "missing_atoms": {k: max(0, target[k] - counts[k]) for k in counts},
    }


def checked_work(scene, work: ActivityWork, previous: dict | None):
    if not work.prediction.strip():
        raise ValueError("Write a prediction before exploring")
    if work.stage == "prediction":
        if previous and previous.get("stage") == "observation":
            raise ValueError(
                "Observations are already saved; keep the original prediction"
            )
        if work.inputs or work.trials:
            raise ValueError("Prediction cannot contain results before exploration")
        if (
            previous
            and previous.get("prediction")
            and previous["prediction"] != work.prediction
        ):
            raise ValueError(
                "Keep the original prediction; explain changes in observations"
            )
        return {
            **work.model_dump(),
            **(
                {"earlier_notes": previous["earlier_notes"]}
                if previous and previous.get("earlier_notes")
                else {}
            ),
        }
    if not previous or previous.get("prediction") != work.prediction:
        raise ValueError("Save the original prediction before submitting observations")
    if not work.trials:
        raise ValueError("Record at least one trial or inspected diagram node")

    def evaluate(inputs):
        if scene.interaction:
            return evaluate_interaction(scene.interaction, inputs)
        spec = scene.simulation
        if not spec or set(inputs) != {"x", "y"}:
            raise ValueError("Numerical simulation needs x and y inputs")
        x = bounded(inputs, "x", spec.x.minimum, spec.x.maximum)
        y = bounded(inputs, "y", spec.y.minimum, spec.y.maximum)
        value = x / (x + y) if spec.model == "mixture_fraction" else x * y
        if not math.isfinite(value):
            raise ValueError("The result is outside the supported numerical range")
        return {"value": value}

    output = evaluate(work.inputs)
    return {
        **work.model_dump(),
        **(
            {"earlier_notes": previous["earlier_notes"]}
            if previous.get("earlier_notes")
            else {}
        ),
        "output": output,
        "results": [
            {"inputs": trial, "output": evaluate(trial)} for trial in work.trials
        ],
    }
