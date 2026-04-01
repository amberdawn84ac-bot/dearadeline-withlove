"""
Tests for Credits API endpoints.
"""
import json
import os
import pytest
from app.api.credits import load_oklahoma_profiles, ProfileResponse


def test_load_oklahoma_profiles():
    """Test that Oklahoma profiles load correctly from JSON."""
    profiles = load_oklahoma_profiles()

    assert isinstance(profiles, dict)
    assert "oklahoma_flexible_homeschool" in profiles
    assert "oklahoma_college_prep" in profiles
    assert "oklahoma_public_school_parity" in profiles


def test_profile_response_model():
    """Test that ProfileResponse correctly models profile data."""
    profiles = load_oklahoma_profiles()

    for profile_key, profile_data in profiles.items():
        profile_response = ProfileResponse(
            profile_key=profile_key,
            name=profile_data.get("name", ""),
            description=profile_data.get("description", ""),
            oasOptional=profile_data.get("oasOptional", False),
            creditHourWeighting=profile_data.get("creditHourWeighting", {}),
        )

        assert profile_response.profile_key == profile_key
        assert profile_response.name == profile_data["name"]
        assert profile_response.description == profile_data["description"]
        assert profile_response.oasOptional == profile_data["oasOptional"]
        assert isinstance(profile_response.creditHourWeighting, dict)
