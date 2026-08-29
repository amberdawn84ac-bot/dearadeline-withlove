import json
from pathlib import Path

from app.curriculum.progression_placement import build_progression_placements


SEED = Path(__file__).resolve().parents[1] / "data" / "seeds" / "oas_to_8track.json"


def _mappings() -> list[dict]:
    return json.loads(SEED.read_text(encoding="utf-8"))["mappings"]


def test_every_standard_has_a_provenance_backed_progression_place():
    mappings = _mappings()
    placements = build_progression_placements(mappings)

    assert len(mappings) == 3043
    assert len(placements) == len(mappings)
    assert all(item["progression_lane"] for item in placements.values())
    assert all(item["progression_ordinal"] > 0 for item in placements.values())
    assert all(item["progression_source_title"] for item in placements.values())
    assert all(item["progression_source_url"].startswith("https://") for item in placements.values())
    assert {item["progression_review_status"] for item in placements.values()} == {"PLACED"}
    assert any(not item["progression_is_terminal"] for item in placements.values())
    assert any(item["progression_parent_id"] for item in placements.values())


def test_math_and_literacy_are_sequential_while_family_tracks_keep_honest_modes():
    mappings = _mappings()
    placements = build_progression_placements(mappings)
    by_track: dict[str, set[str]] = {}
    for mapping in mappings:
        standard_id = (
            mapping.get("standard_node", {}).get("properties", {}).get("id")
            or mapping.get("neo4j_node", {}).get("properties", {}).get("id")
            or mapping["standard_id"]
        )
        by_track.setdefault(mapping["track"], set()).add(placements[standard_id]["progression_mode"])

    assert by_track["APPLIED_MATHEMATICS"] == {"SEQUENTIAL"}
    assert by_track["ENGLISH_LITERATURE"] == {"SEQUENTIAL"}
    assert by_track["CREATION_SCIENCE"] == {"SCAFFOLDED"}
    assert by_track["TRUTH_HISTORY"] == {"OPEN"}
    assert set(by_track) == {
        "CREATION_SCIENCE", "HEALTH_NATUROPATHY", "HOMESTEADING",
        "GOVERNMENT_ECONOMICS", "JUSTICE_CHANGEMAKING", "DISCIPLESHIP",
        "TRUTH_HISTORY", "ENGLISH_LITERATURE", "APPLIED_MATHEMATICS",
        "CREATIVE_ECONOMY",
    }


def test_ordinals_are_unique_inside_each_lane():
    placements = build_progression_placements(_mappings())
    lanes: dict[str, list[int]] = {}
    for item in placements.values():
        lanes.setdefault(item["progression_lane"], []).append(item["progression_ordinal"])
    assert all(sorted(ordinals) == list(range(1, len(ordinals) + 1)) for ordinals in lanes.values())
