import json
from pathlib import Path


def test_oklahoma_profiles_valid_json():
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    assert profiles_path.exists(), f"not found at {profiles_path}"
    with open(profiles_path) as f:
        profiles = json.load(f)
    assert "oklahoma_flexible_homeschool" in profiles
    assert "oklahoma_college_prep" in profiles
    assert "oklahoma_public_school_parity" in profiles


def test_oklahoma_profiles_required_keys():
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    with open(profiles_path) as f:
        profiles = json.load(f)
    required_keys = {
        "name", "description", "oasOptional", "requiresApprovalForTranscript",
        "creditHourWeighting", "creditThresholds", "transcript",
    }
    for profile_key, profile in profiles.items():
        assert required_keys.issubset(profile.keys()), \
            f"{profile_key} missing: {required_keys - set(profile.keys())}"
        assert profile["creditThresholds"]["full_credit"] == 120
        assert profile["creditThresholds"]["half_credit"] == 60


def test_artifact_type_weighting_consistent():
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    with open(profiles_path) as f:
        profiles = json.load(f)
    artifact_types = {"essay", "quiz", "lab", "project", "discussion", "fieldwork", "presentation"}
    for profile_key, profile in profiles.items():
        weights = set(profile["creditHourWeighting"].keys())
        assert weights == artifact_types, f"{profile_key} mismatch: {weights} vs {artifact_types}"
        for weight in profile["creditHourWeighting"].values():
            assert weight > 0
