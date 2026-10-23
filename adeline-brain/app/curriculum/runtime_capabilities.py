"""Authoring boundary for the native teaching player, not a roadmap of promises.

The schemas still validate documents and the server still validates learner work.
This catalog tells authoring calls what delivery can actually do and versions
new canonical reuse when that boundary changes. Saved plan-item IDs stay stable.
"""

import hashlib
import json
from typing import get_args

from app.curriculum.classroom import Scene, Simulation, Speech
from app.curriculum.interactive_models import Interaction

CAPABILITY_REVISION = "native-teaching-v2"

_MECHANISMS = {
    "proportional": ("simulation", "Two nonnegative inputs; output is x*y."),
    "rectangle_area": ("simulation", "Side controls and a rectangle; area is x*y."),
    "mixture_fraction": (
        "simulation",
        "Two nonnegative amounts; fraction x/(x+y), nonzero total.",
    ),
    "sorting": (
        "sorting",
        "One category per item, 2–6 categories and 2–12 items; server-checked answers.",
    ),
    "water_heating": (
        "interaction",
        "100 g pure water, ice initially at -20 C at 1 atm; added energy 0–330 kJ, phase fractions and conserved mass. No pressure or substance control.",
    ),
    "mass_balance": (
        "interaction",
        "Baking soda, 5%-by-mass vinegar, reaction progress and open/closed boundary; stoichiometric CO2 and mass accounting. No other reactants.",
    ),
    "diagram": (
        "interaction",
        "2–10 linked nodes with details and labelled edges. Inspect existing nodes; no graph editing or 3D.",
    ),
    "molecule_builder": (
        "interaction",
        "Whole H/O/C counts 0–10 for H2O, CO2 or CH4; composition and remaining atoms, not chemical synthesis.",
    ),
    "air_volume": (
        "interaction",
        "Sealed air, volume 20–100 mL, fixed amount and temperature. Pressure times volume stays constant at 5066.25 kPa·mL. Not a proof of a gas law.",
    ),
    "graph_compare": (
        "interaction",
        "Two labelled series of 2–8 finite numbers. Learner compares one plotted position: A greater, B greater, or the same.",
    ),
    "sequence": (
        "interaction",
        "Order 3–8 steps. Correct positions and reasons stay on the server.",
    ),
    "matching": (
        "interaction",
        "Match 2–6 prompts to existing choices. Correct pairs and reasons stay on the server.",
    ),
    "matter_properties": (
        "interaction",
        "Observable properties for ice_cube, liquid_water, sealed_air, or dry_sand. The menu and answers are code-owned.",
    ),
}


def authoring_capabilities() -> dict:
    """Return a fresh, JSON-safe description of the installed delivery contract."""
    numeric = set(get_args(Simulation.model_fields["model"].annotation))
    interactions = set(get_args(Interaction.model_fields["kind"].annotation))
    if set(_MECHANISMS) != numeric | interactions | {"sorting"}:
        raise ValueError(
            "Update teaching capability guidance for the schema's mechanisms"
        )
    data = {
        "revision": CAPABILITY_REVISION,
        "scene_types": list(get_args(Scene.model_fields["type"].annotation)),
        "mechanisms": [
            {"id": name, "scene_field": field, "behavior": behavior}
            for name, (field, behavior) in _MECHANISMS.items()
        ],
        "delivery": {
            "slide": "Responsive prose and key points, plus an optional responsive visual reading view. No fixed visual canvas or arbitrary HTML.",
            "project": "Materials, ordered steps and saved text work; no file/audio upload is provided by this player.",
            "quiz": "One single-choice question per scene, with server-side answer and explanation.",
            "sources": "Attached text, source links and images; do not promise an attachment unless actually provided.",
        },
        "narration": {
            "fields": list(Speech.model_fields),
            "behavior": "Device speech, one part at a time, or the same parts stepped through as text. Pause, resume, stop, and manual continuation. Text remains available.",
            "targets": "speak, focus, annotate, pause, and clear. Optional content/activity/task/visual focus. target_id must be an existing visual element or diagram node. No widget writes into learner trials.",
        },
        "evidence": {
            "activity": "Save prediction before exploration; observations include recorded trials. Server recomputes model outputs.",
            "assessment": "Saved work may be reviewed against supplied curriculum targets. Provider failure must not lose work.",
            "credit": "Existing parent-reviewed course approval only; no automatic credit from generation, scores, clicks or narration.",
        },
        "not_available": [
            "generated_html_or_javascript_execution",
            "fixed_canvas_slide_rendering",
            "generic_game_engine",
            "code_execution",
            "3d_scene_renderer",
            "pre_generated_audio_or_video",
            "automatic_cross_unit_revisit_scheduler",
        ],
    }
    # Include shapes as well as prose, so changing supported fields cannot reuse
    # a previously authored canonical under an incompatible new runtime boundary.
    fingerprint_input = {
        "capabilities": data,
        "scene_schema": Scene.model_json_schema(),
    }
    data["fingerprint"] = hashlib.sha256(
        json.dumps(fingerprint_input, sort_keys=True).encode()
    ).hexdigest()[:20]
    return data
