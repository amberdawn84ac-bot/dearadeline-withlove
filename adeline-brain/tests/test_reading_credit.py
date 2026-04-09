"""Tests for app.services.reading_credit — pure function tests only (no DB)."""
import pytest
from app.services.reading_credit import (
    calculate_reading_credit,
    get_reading_standards,
    TRACK_TO_GRADUATION_BUCKET,
)


# ── calculate_reading_credit ─────────────────────────────────────────────────

class TestCalculateReadingCredit:
    """Formula: (minutes / 60) / 120 * multiplier."""

    def test_grade_level_book_10h(self):
        """10 hours at grade level (multiplier 1.0) → 10/120 ≈ 0.0833."""
        result = calculate_reading_credit(
            reading_minutes=600,  # 10 hours
            book_lexile=750,      # grade 6 range is 700-800
            grade_level=6,
        )
        assert result == pytest.approx(0.0833, abs=0.001)

    def test_above_grade_12h(self):
        """12 hours above grade max (multiplier 1.2) → 12/120*1.2 = 0.12."""
        result = calculate_reading_credit(
            reading_minutes=720,  # 12 hours
            book_lexile=950,      # above grade 6 max of 800
            grade_level=6,
        )
        assert result == pytest.approx(0.12, abs=0.001)

    def test_below_grade_12h(self):
        """12 hours below grade min (multiplier 0.8) → 12/120*0.8 = 0.08."""
        result = calculate_reading_credit(
            reading_minutes=720,  # 12 hours
            book_lexile=500,      # below grade 6 min of 700
            grade_level=6,
        )
        assert result == pytest.approx(0.08, abs=0.001)

    def test_zero_time(self):
        """Zero reading minutes → 0.0 credit."""
        assert calculate_reading_credit(0, 750, 6) == 0.0

    def test_negative_time(self):
        """Negative reading minutes → 0.0 credit."""
        assert calculate_reading_credit(-30, 750, 6) == 0.0

    def test_kindergarten(self):
        """Kindergarten (grade 0) at grade level: 5h → 5/120*1.0 ≈ 0.0417."""
        result = calculate_reading_credit(
            reading_minutes=300,  # 5 hours
            book_lexile=300,      # K range is 250-350
            grade_level=0,
        )
        assert result == pytest.approx(0.0417, abs=0.001)

    def test_kindergarten_above_grade(self):
        """Kindergarten above grade max (350) gets 1.2 multiplier."""
        result = calculate_reading_credit(
            reading_minutes=300,
            book_lexile=400,      # above K max of 350
            grade_level=0,
        )
        expected = (300 / 60) / 120 * 1.2
        assert result == pytest.approx(expected, abs=0.001)


# ── TRACK_TO_GRADUATION_BUCKET ───────────────────────────────────────────────

class TestTrackToGraduationBucket:
    """All 10 tracks must map to the correct graduation bucket."""

    EXPECTED = {
        "ENGLISH_LITERATURE":   "ENGLISH_CORE",
        "TRUTH_HISTORY":        "SOCIAL_STUDIES",
        "JUSTICE_CHANGEMAKING": "SOCIAL_STUDIES",
        "GOVERNMENT_ECONOMICS": "SOCIAL_STUDIES",
        "CREATION_SCIENCE":     "SCIENCE_CORE",
        "HOMESTEADING":         "SCIENCE_CORE",
        "HEALTH_NATUROPATHY":   "SCIENCE_CORE",
        "APPLIED_MATHEMATICS":  "MATH_CORE",
        "DISCIPLESHIP":         "ELECTIVES",
        "CREATIVE_ECONOMY":     "FINE_ARTS",
    }

    def test_all_10_tracks_present(self):
        assert len(TRACK_TO_GRADUATION_BUCKET) == 10

    @pytest.mark.parametrize("track,bucket", EXPECTED.items())
    def test_mapping(self, track, bucket):
        assert TRACK_TO_GRADUATION_BUCKET[track] == bucket


# ── get_reading_standards ────────────────────────────────────────────────────

class TestGetReadingStandards:
    """K-8 returns 1-2 standards; 9+ returns empty list."""

    def test_literature_track_uses_rl(self):
        standards = get_reading_standards("ENGLISH_LITERATURE", 5)
        assert standards == ["RL.5.2", "RL.5.10"]

    def test_discipleship_uses_rl(self):
        standards = get_reading_standards("DISCIPLESHIP", 3)
        assert standards == ["RL.3.2", "RL.3.10"]

    def test_informational_track_uses_ri(self):
        standards = get_reading_standards("TRUTH_HISTORY", 7)
        assert standards == ["RI.7.2", "RI.7.10"]

    def test_science_track_uses_ri(self):
        standards = get_reading_standards("CREATION_SCIENCE", 4)
        assert standards == ["RI.4.2", "RI.4.10"]

    def test_grade_9_returns_empty(self):
        assert get_reading_standards("ENGLISH_LITERATURE", 9) == []

    def test_grade_12_returns_empty(self):
        assert get_reading_standards("TRUTH_HISTORY", 12) == []

    def test_returns_two_standards_for_k8(self):
        for grade in range(0, 9):
            standards = get_reading_standards("ENGLISH_LITERATURE", grade)
            assert len(standards) == 2, f"Expected 2 standards for grade {grade}"

    def test_kindergarten(self):
        standards = get_reading_standards("ENGLISH_LITERATURE", 0)
        assert standards == ["RL.0.2", "RL.0.10"]
