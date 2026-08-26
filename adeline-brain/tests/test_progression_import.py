import json

import pytest

from app.curriculum.progression_import import (
    ProgressionEdge,
    edge_from_row,
    load_progression_file,
    prerequisite_cycles,
    validate_known_standards,
)


def verified_edge(**updates):
    values = {
        "from_standard_id": "MATH_G4_FOUNDATION",
        "relation_type": "PREREQUISITE_FOR",
        "to_standard_id": "MATH_G4_FRACTIONS",
        "weight": 1,
        "source_title": "Official vertical progression",
        "source_url": "https://example.gov/progression.pdf",
        "source_version": "2026",
        "evidence_note": "Page 14 explicitly places the foundation before fraction equivalence.",
        "review_status": "VERIFIED",
    }
    values.update(updates)
    return edge_from_row(values)


def test_verified_edge_requires_complete_provenance():
    with pytest.raises(ValueError, match="source_url"):
        verified_edge(source_url="")


def test_unknown_standard_ids_are_rejected():
    errors = validate_known_standards([verified_edge()], {"MATH_G4_FOUNDATION"})
    assert errors == ["unknown to_standard_id: MATH_G4_FRACTIONS"]


def test_verified_prerequisite_cycle_is_rejected():
    first = verified_edge()
    second = verified_edge(
        from_standard_id="MATH_G4_FRACTIONS",
        to_standard_id="MATH_G4_FOUNDATION",
    )
    assert prerequisite_cycles([first, second])


def test_pending_research_edge_cannot_create_a_hard_gate_cycle():
    first = verified_edge()
    pending = ProgressionEdge(
        from_standard_id="MATH_G4_FRACTIONS",
        relation_type="PREREQUISITE_FOR",
        to_standard_id="MATH_G4_FOUNDATION",
        weight=1,
        source_title="", source_url="", source_version="", evidence_note="",
        review_status="PENDING",
    )
    assert prerequisite_cycles([first, pending]) == []


def test_json_progression_file_loads(tmp_path):
    path = tmp_path / "progression.json"
    path.write_text(json.dumps({"edges": [verified_edge().as_row()]}), encoding="utf-8")
    assert load_progression_file(path) == [verified_edge()]
