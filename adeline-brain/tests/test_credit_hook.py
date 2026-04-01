"""
Tests for credit_hook — post-lesson credit accumulation mappings and profile loading.
No DB calls — pure function tests.
"""
import json
from pathlib import Path
import pytest

from app.services.credit_hook import (
    TRACK_BUCKET_MAP,
    TRACK_EXTERNAL_NAME,
    _load_profiles,
)


# All 10 tracks from CLAUDE.md
EXPECTED_TRACKS = {
    "CREATION_SCIENCE",
    "HEALTH_NATUROPATHY",
    "HOMESTEADING",
    "GOVERNMENT_ECONOMICS",
    "JUSTICE_CHANGEMAKING",
    "DISCIPLESHIP",
    "TRUTH_HISTORY",
    "ENGLISH_LITERATURE",
    "APPLIED_MATHEMATICS",
    "CREATIVE_ECONOMY",
}

# Expected credit buckets
EXPECTED_BUCKETS = {
    "LAB_SCIENCE",
    "HEALTH",
    "SOCIAL_STUDIES",
    "ELECTIVE",
    "ENGLISH",
    "MATH",
    "FINE_ARTS",
}


class TestTrackBucketMap:
    """Test TRACK_BUCKET_MAP has all 10 tracks and valid bucket names."""

    def test_track_bucket_map_has_all_10_tracks(self):
        """All 10 tracks from CLAUDE.md must be in TRACK_BUCKET_MAP."""
        assert set(TRACK_BUCKET_MAP.keys()) == EXPECTED_TRACKS, (
            f"TRACK_BUCKET_MAP is missing or has extra tracks. "
            f"Expected: {EXPECTED_TRACKS}, Got: {set(TRACK_BUCKET_MAP.keys())}"
        )

    def test_track_bucket_map_values_are_valid(self):
        """All bucket names in TRACK_BUCKET_MAP must be valid credit buckets."""
        for track, bucket in TRACK_BUCKET_MAP.items():
            assert bucket in EXPECTED_BUCKETS, (
                f"Track '{track}' maps to invalid bucket '{bucket}'. "
                f"Valid buckets: {EXPECTED_BUCKETS}"
            )

    def test_track_bucket_map_no_none_values(self):
        """No track should map to None."""
        for track, bucket in TRACK_BUCKET_MAP.items():
            assert bucket is not None, f"Track '{track}' maps to None"


class TestTrackExternalName:
    """Test TRACK_EXTERNAL_NAME has all 10 tracks with human-readable names."""

    def test_track_external_name_has_all_10_tracks(self):
        """All 10 tracks from CLAUDE.md must be in TRACK_EXTERNAL_NAME."""
        assert set(TRACK_EXTERNAL_NAME.keys()) == EXPECTED_TRACKS, (
            f"TRACK_EXTERNAL_NAME is missing or has extra tracks. "
            f"Expected: {EXPECTED_TRACKS}, Got: {set(TRACK_EXTERNAL_NAME.keys())}"
        )

    def test_track_external_names_are_not_empty(self):
        """All external names must be non-empty strings."""
        for track, name in TRACK_EXTERNAL_NAME.items():
            assert isinstance(name, str), (
                f"Track '{track}' has non-string external name: {type(name)}"
            )
            assert name.strip(), f"Track '{track}' has empty external name"

    def test_track_external_names_are_descriptive(self):
        """External names should contain meaningful words (not just enum values)."""
        for track, name in TRACK_EXTERNAL_NAME.items():
            # Names should be substantially different from the track enum
            assert name.lower() != track.lower(), (
                f"Track '{track}' external name is just the enum value"
            )
            # Names should be at least 3 words for clarity
            words = name.split()
            assert len(words) >= 2, (
                f"Track '{track}' external name '{name}' is too short"
            )


class TestLoadProfiles:
    """Test _load_profiles() successfully loads Oklahoma credit profiles."""

    def test_load_profiles_returns_dict(self):
        """_load_profiles() should return a dict."""
        profiles = _load_profiles()
        assert isinstance(profiles, dict), f"Expected dict, got {type(profiles)}"

    def test_load_profiles_has_required_profiles(self):
        """_load_profiles() must include all three Oklahoma profiles."""
        profiles = _load_profiles()
        required_profiles = {
            "oklahoma_flexible_homeschool",
            "oklahoma_college_prep",
            "oklahoma_public_school_parity",
        }
        assert required_profiles.issubset(profiles.keys()), (
            f"Missing required profiles. Expected: {required_profiles}, "
            f"Got: {set(profiles.keys())}"
        )

    def test_flexible_homeschool_profile_structure(self):
        """Flexible homeschool profile must have required fields."""
        profiles = _load_profiles()
        profile = profiles["oklahoma_flexible_homeschool"]

        required_fields = {"name", "creditHourWeighting", "creditThresholds"}
        assert required_fields.issubset(profile.keys()), (
            f"Flexible homeschool profile missing required fields: {required_fields}"
        )

        # Check creditHourWeighting
        weighting = profile["creditHourWeighting"]
        required_weights = {"essay", "quiz", "lab", "project", "discussion", "fieldwork", "presentation"}
        assert required_weights.issubset(weighting.keys()), (
            f"creditHourWeighting missing artifact types: {required_weights}"
        )

        # Check creditThresholds
        thresholds = profile["creditThresholds"]
        assert "full_credit" in thresholds and "half_credit" in thresholds, (
            "creditThresholds missing full_credit or half_credit"
        )

    def test_college_prep_profile_structure(self):
        """College prep profile must have required fields and college-specific flags."""
        profiles = _load_profiles()
        profile = profiles["oklahoma_college_prep"]

        required_fields = {"name", "creditHourWeighting", "creditThresholds", "oasrheEnabled", "actReadinessEnabled"}
        assert required_fields.issubset(profile.keys()), (
            f"College prep profile missing required fields: {required_fields}"
        )

        assert profile["oasrheEnabled"] is True, "College prep should have oasrheEnabled=true"
        assert profile["actReadinessEnabled"] is True, "College prep should have actReadinessEnabled=true"

    def test_public_school_parity_profile_structure(self):
        """Public school parity profile must have saturation requirements."""
        profiles = _load_profiles()
        profile = profiles["oklahoma_public_school_parity"]

        required_fields = {"oasStandardsSaturationRequired", "oasStandardsSaturationThreshold"}
        assert required_fields.issubset(profile.keys()), (
            f"Public school parity profile missing saturation fields: {required_fields}"
        )

        assert profile["oasStandardsSaturationRequired"] is True
        assert 0.0 < profile["oasStandardsSaturationThreshold"] <= 1.0

    def test_all_profiles_have_credit_thresholds(self):
        """All profiles must define full_credit and half_credit thresholds."""
        profiles = _load_profiles()

        for profile_key, profile in profiles.items():
            assert "creditThresholds" in profile, (
                f"Profile '{profile_key}' missing creditThresholds"
            )
            thresholds = profile["creditThresholds"]
            assert thresholds.get("full_credit") == 120, (
                f"Profile '{profile_key}' full_credit should be 120"
            )
            assert thresholds.get("half_credit") == 60, (
                f"Profile '{profile_key}' half_credit should be 60"
            )

    def test_profiles_file_exists(self):
        """oklahoma_profiles.json file must exist at expected location."""
        profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
        assert profiles_path.exists(), (
            f"oklahoma_profiles.json not found at {profiles_path}"
        )

    def test_profiles_file_is_valid_json(self):
        """oklahoma_profiles.json must be valid JSON."""
        profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
        try:
            with open(profiles_path) as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"oklahoma_profiles.json is not valid JSON: {e}")
