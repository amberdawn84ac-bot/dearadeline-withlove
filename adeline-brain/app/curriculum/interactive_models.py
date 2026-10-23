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


class SequenceStep(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=160)
    position: int = Field(ge=1, le=8)
    reason: str = Field(min_length=5, max_length=400)


class MatchChoice(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=160)


class MatchPair(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    prompt: str = Field(min_length=1, max_length=160)
    match_id: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=5, max_length=400)


PROPERTY_MENU = (
    ("color", "Color you can see"),
    ("shape", "A shape of its own"),
    ("texture", "Texture you can feel"),
    ("space", "Takes up space"),
    ("mass", "Has mass you can feel or measure"),
    ("cold", "Feels cold"),
    ("pours", "Pours or flows"),
    ("invisible", "The material itself is invisible"),
    ("compressible", "You can squeeze it smaller and it pushes back"),
    ("fixed_shape", "Keeps its own shape"),
)

# Answers stay on the server. Titles below are safe to show before an attempt.
MATTER_SAMPLES = {
    "ice_cube": {
        "title": "Ice cube you can hold",
        "detail": "A solid piece of frozen pure water, about the size of a walnut, on a plate. It has not melted.",
        "applicable": {"color", "shape", "texture", "space", "mass", "cold", "fixed_shape"},
    },
    "liquid_water": {
        "title": "Glass of liquid water",
        "detail": "A clear glass of liquid water at room temperature.",
        "applicable": {"color", "space", "mass", "pours"},
    },
    "sealed_air": {
        "title": "Air in a sealed syringe",
        "detail": "A syringe blocked at the tip, partly filled with air, with the plunger free to move. No water is inside.",
        "applicable": {"space", "invisible", "compressible"},
    },
    "dry_sand": {
        "title": "Spoon of dry sand",
        "detail": "Dry sand on a plate. The grains are visible and can be poured.",
        "applicable": {"color", "texture", "space", "mass", "pours"},
    },
}


class Interaction(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    kind: Literal[
        "water_heating",
        "mass_balance",
        "diagram",
        "molecule_builder",
        "air_volume",
        "graph_compare",
        "sequence",
        "matching",
        "matter_properties",
    ]
    prediction_prompt: str = Field(min_length=5, max_length=500)
    observation_prompt: str = Field(min_length=5, max_length=500)
    nodes: list[DiagramNode] = Field(default_factory=list, max_length=10)
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=16)
    formula: Literal["H2O", "CO2", "CH4"] = "H2O"
    steps: list[SequenceStep] = Field(default_factory=list, max_length=8)
    choices: list[MatchChoice] = Field(default_factory=list, max_length=6)
    pairs: list[MatchPair] = Field(default_factory=list, max_length=6)
    series_a: list[float] = Field(default_factory=list, max_length=8)
    series_b: list[float] = Field(default_factory=list, max_length=8)
    series_a_label: str = ""
    series_b_label: str = ""
    sample: Literal["ice_cube", "liquid_water", "sealed_air", "dry_sand"] = "ice_cube"

    @model_validator(mode="after")
    def valid_mechanism(self):
        extras = bool(self.steps or self.choices or self.pairs or self.series_a or self.series_b)
        if self.kind == "diagram":
            ids = {n.id for n in self.nodes}
            if len(ids) != len(self.nodes) or len(ids) < 2:
                raise ValueError("A diagram needs 2–10 uniquely identified nodes")
            if not self.edges or any(
                e.source not in ids or e.target not in ids or e.source == e.target
                for e in self.edges
            ):
                raise ValueError("Diagram connections must join existing distinct nodes")
            if extras:
                raise ValueError("Diagrams do not use sequence, matching, or graph data")
        elif self.nodes or self.edges:
            raise ValueError("Nodes and edges belong only to diagrams")
        elif self.kind == "sequence":
            if not 3 <= len(self.steps) <= 8 or len({s.id for s in self.steps}) != len(self.steps):
                raise ValueError("A sequence needs 3–8 unique steps")
            positions = [s.position for s in self.steps]
            if sorted(positions) != list(range(1, len(self.steps) + 1)):
                raise ValueError("Sequence positions must be 1 through the number of steps")
            if self.choices or self.pairs or self.series_a or self.series_b:
                raise ValueError("A sequence only contains ordered steps")
        elif self.kind == "matching":
            choice_ids = {c.id for c in self.choices}
            if (
                not 2 <= len(self.pairs) <= 6
                or len({p.id for p in self.pairs}) != len(self.pairs)
                or len(choice_ids) != len(self.choices)
                or any(p.match_id not in choice_ids for p in self.pairs)
            ):
                raise ValueError("Every match must use a unique pair and an existing choice")
            if self.steps or self.series_a or self.series_b:
                raise ValueError("Matching does not use sequence steps or graph series")
        elif self.kind == "graph_compare":
            if (
                not 2 <= len(self.series_a) == len(self.series_b) <= 8
                or not self.series_a_label.strip()
                or not self.series_b_label.strip()
                or any(not math.isfinite(n) for n in (*self.series_a, *self.series_b))
            ):
                raise ValueError("Graph comparison needs two equal finite series and labels")
            if self.steps or self.choices or self.pairs:
                raise ValueError("Graph comparison does not use sequence or matching keys")
        elif extras:
            raise ValueError("This mechanism does not accept sequence, matching, or graph data")
        return self


def redact_interaction(interaction: dict) -> None:
    """Remove answer keys. Sequence steps are listed by id so array order is not the key."""
    if interaction.get("kind") == "sequence":
        for step in interaction.get("steps", []):
            step.pop("position", None)
            step.pop("reason", None)
        interaction["steps"] = sorted(interaction.get("steps", []), key=lambda step: step["id"])
    if interaction.get("kind") == "matching":
        for pair in interaction.get("pairs", []):
            pair.pop("match_id", None)
            pair.pop("reason", None)
        interaction["pairs"] = sorted(interaction.get("pairs", []), key=lambda pair: pair["id"])
        interaction["choices"] = sorted(interaction.get("choices", []), key=lambda choice: choice["id"])



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


def air_volume(volume_ml):
    """Fixed amount of air at constant temperature. 50 mL corresponds to 101.325 kPa."""
    pressure = 101.325 * (50 / volume_ml)
    return {
        "volume_ml": volume_ml,
        "pressure_kpa": pressure,
        "pressure_times_volume": pressure * volume_ml,
    }


def _ids(text):
    if not isinstance(text, str) or len(text) > 200:
        raise ValueError("Submit the ids as one short list")
    return [part for part in text.split(",") if part]


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
    if spec.kind == "air_volume":
        if set(inputs) != {"volume_ml"}:
            raise ValueError("Air volume needs volume_ml only")
        return air_volume(bounded(inputs, "volume_ml", 20, 100))
    if spec.kind == "graph_compare":
        if set(inputs) != {"index", "choice"} or inputs.get("choice") not in {
            "a",
            "b",
            "same",
        }:
            raise ValueError("Choose a plotted position and whether A, B, or both match")
        index = bounded(inputs, "index", 0, len(spec.series_a) - 1)
        if int(index) != index:
            raise ValueError("Choose one plotted position")
        point = int(index)
        left, right = spec.series_a[point], spec.series_b[point]
        actual = "same" if left == right else "a" if left > right else "b"
        matches = inputs["choice"] == actual
        return {
            "index": point,
            "choice": inputs["choice"],
            "correct": matches,
            "review": (
                "Your comparison matches the plotted values."
                if matches
                else "Read that position again and compare the two heights."
            ),
        }
    if spec.kind == "sequence":
        if set(inputs) != {"order"}:
            raise ValueError("Submit the order only")
        submitted = _ids(inputs.get("order"))
        expected = [step.id for step in sorted(spec.steps, key=lambda step: step.position)]
        if sorted(submitted) != sorted(expected) or len(submitted) != len(expected):
            raise ValueError("Include each step once")
        details = []
        correct = 0
        for place, step_id in enumerate(submitted):
            step = next(item for item in spec.steps if item.id == step_id)
            ok = step_id == expected[place]
            correct += ok
            details.append({"item_id": step_id, "correct": ok, "explanation": step.reason})
        return {
            "correct": correct == len(expected),
            "review": f"{correct} of {len(expected)} steps are in place. Revise the order or explain your reasoning.",
            "items": details,
        }
    if spec.kind == "matching":
        if set(inputs) != {"matches"}:
            raise ValueError("Submit the matches only")
        parts = _ids(inputs.get("matches"))
        if len(parts) != len(spec.pairs):
            raise ValueError("Match each prompt once")
        found = {}
        for part in parts:
            if part.count(":") != 1:
                raise ValueError("Match each prompt to one choice")
            pair_id, choice_id = part.split(":")
            found[pair_id] = choice_id
        choice_ids = {choice.id for choice in spec.choices}
        if set(found) != {pair.id for pair in spec.pairs} or any(
            choice not in choice_ids for choice in found.values()
        ):
            raise ValueError("Match each prompt to one available choice")
        details = []
        correct = 0
        for pair in spec.pairs:
            ok = found[pair.id] == pair.match_id
            correct += ok
            details.append({"item_id": pair.id, "correct": ok, "explanation": pair.reason})
        return {
            "correct": correct == len(spec.pairs),
            "review": f"{correct} of {len(spec.pairs)} matches fit. Revise a mismatch or explain the relationship.",
            "items": details,
        }
    if spec.kind == "matter_properties":
        selected = set(_ids(inputs.get("selected"))) if inputs.get("selected") else set()
        menu = {item[0] for item in PROPERTY_MENU}
        if set(inputs) != {"selected"} or not selected <= menu:
            raise ValueError("Choose only listed properties. Use selected.")
        applicable = MATTER_SAMPLES[spec.sample]["applicable"]
        details = []
        correct = 0
        for prop, _label in PROPERTY_MENU:
            chose = prop in selected
            ok = chose == (prop in applicable)
            correct += ok
            details.append(
                {
                    "item_id": prop,
                    "correct": ok,
                    "explanation": (
                        "This sample is set up so you can observe that."
                        if prop in applicable
                        else "This sample is not set up to show that observation."
                    ),
                }
            )
        total = len(PROPERTY_MENU)
        return {
            "correct": correct == total,
            "review": f"{correct} of {total} property decisions match this sample. This menu does not describe every substance.",
            "items": details,
        }
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
