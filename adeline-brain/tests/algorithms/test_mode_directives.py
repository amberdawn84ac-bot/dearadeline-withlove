from app.algorithms.pedagogical_directives import get_mode_directives, TRACK_TO_MODE

def test_single_track_returns_one_mode():
    result = get_mode_directives(["TRUTH_HISTORY"])
    assert "INVESTIGATOR" in result
    assert "LAB" not in result

def test_multi_track_blends_modes():
    result = get_mode_directives(["CREATIVE_ECONOMY", "HOMESTEADING"])
    assert "WORKSHOP" in result
    assert "LAB" in result

def test_all_10_tracks_map():
    all_tracks = [
        "TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "CREATION_SCIENCE",
        "HOMESTEADING", "HEALTH_NATUROPATHY", "GOVERNMENT_ECONOMICS",
        "DISCIPLESHIP", "ENGLISH_LITERATURE", "APPLIED_MATHEMATICS",
        "CREATIVE_ECONOMY",
    ]
    for track in all_tracks:
        assert track in TRACK_TO_MODE, f"{track} missing from TRACK_TO_MODE"

def test_unknown_track_returns_empty():
    result = get_mode_directives(["NOT_A_TRACK"])
    assert result == ""

def test_empty_tracks_returns_empty():
    assert get_mode_directives([]) == ""
