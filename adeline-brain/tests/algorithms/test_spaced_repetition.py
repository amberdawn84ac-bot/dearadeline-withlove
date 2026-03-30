"""Tests for SM-2 spaced repetition algorithm.

Mirrors cascade-adeline/__tests__/learning/spaced-repetition.test.ts
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.algorithms.spaced_repetition import (
    sm2,
    quality_to_mastery_delta,
    is_due,
    overdue_days,
    format_due_reviews_for_prompt,
)

DEFAULT_EF = 2.5


# ── sm2() core algorithm ──────────────────────────────────────────────────────

class TestSM2:
    def test_first_successful_review_gives_interval_of_1_day(self):
        result = sm2(quality=4, prev_interval=0, prev_ease=DEFAULT_EF, prev_reps=0)
        assert result.interval == 1
        assert result.repetitions == 1

    def test_second_successful_review_gives_interval_of_6_days(self):
        result = sm2(quality=4, prev_interval=1, prev_ease=DEFAULT_EF, prev_reps=1)
        assert result.interval == 6
        assert result.repetitions == 2

    def test_third_successful_review_multiplies_interval_by_ease_factor(self):
        result = sm2(quality=4, prev_interval=6, prev_ease=DEFAULT_EF, prev_reps=2)
        assert result.interval == round(6 * DEFAULT_EF)
        assert result.repetitions == 3

    def test_perfect_quality_increases_ease_factor(self):
        result = sm2(quality=5, prev_interval=6, prev_ease=DEFAULT_EF, prev_reps=2)
        assert result.ease_factor > DEFAULT_EF

    def test_quality_3_decreases_ease_factor(self):
        result = sm2(quality=3, prev_interval=6, prev_ease=DEFAULT_EF, prev_reps=2)
        assert result.ease_factor < DEFAULT_EF

    def test_failed_recall_resets_repetitions_and_interval(self):
        result = sm2(quality=2, prev_interval=15, prev_ease=2.3, prev_reps=5)
        assert result.interval == 1
        assert result.repetitions == 0

    def test_ease_factor_never_drops_below_1_3(self):
        ef = DEFAULT_EF
        for _ in range(20):
            result = sm2(quality=0, prev_interval=1, prev_ease=ef, prev_reps=0)
            ef = result.ease_factor
        assert ef >= 1.3

    def test_clamps_quality_above_5_to_5(self):
        high = sm2(quality=10, prev_interval=1, prev_ease=DEFAULT_EF, prev_reps=1)
        assert high.repetitions == 2  # treated as quality=5, passes

    def test_clamps_quality_below_0_to_0(self):
        low = sm2(quality=-3, prev_interval=6, prev_ease=DEFAULT_EF, prev_reps=3)
        assert low.repetitions == 0  # treated as 0, fails

    def test_next_due_at_is_in_the_future(self):
        now = datetime.now(timezone.utc)
        result = sm2(quality=4, prev_interval=0, prev_ease=DEFAULT_EF, prev_reps=0)
        assert result.next_due_at > now

    def test_next_due_at_matches_interval(self):
        result = sm2(quality=4, prev_interval=1, prev_ease=DEFAULT_EF, prev_reps=1)
        # Should be ~6 days from now
        assert result.interval == 6
        expected = datetime.now(timezone.utc) + timedelta(days=6)
        delta = abs((result.next_due_at - expected).total_seconds())
        assert delta < 5  # within 5 seconds

    def test_quality_4_gives_stable_ease_factor(self):
        # q=4: EF change = 0.1 - (5-4)*(0.08 + (5-4)*0.02) = 0.1 - 0.10 = 0.0
        result = sm2(quality=4, prev_interval=6, prev_ease=DEFAULT_EF, prev_reps=2)
        assert abs(result.ease_factor - DEFAULT_EF) < 0.001


# ── quality_to_mastery_delta() ────────────────────────────────────────────────

class TestQualityToMasteryDelta:
    def test_perfect_recall_gives_positive_delta(self):
        assert quality_to_mastery_delta(5) == 0.15

    def test_good_recall_gives_positive_delta(self):
        assert quality_to_mastery_delta(4) == 0.10

    def test_barely_passing_gives_small_positive_delta(self):
        assert quality_to_mastery_delta(3) == 0.05

    def test_failed_recall_2_gives_negative_delta(self):
        assert quality_to_mastery_delta(2) == -0.02

    def test_failed_recall_1_gives_negative_delta(self):
        assert quality_to_mastery_delta(1) == -0.05

    def test_blackout_0_gives_most_negative_delta(self):
        assert quality_to_mastery_delta(0) == -0.08

    def test_out_of_range_above_clamps_to_5(self):
        assert quality_to_mastery_delta(9) == 0.15

    def test_out_of_range_below_clamps_to_0(self):
        assert quality_to_mastery_delta(-1) == -0.08


# ── is_due() ──────────────────────────────────────────────────────────────────

class TestIsDue:
    def test_past_date_is_due(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        assert is_due(past) is True

    def test_future_date_is_not_due(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        assert is_due(future) is False

    def test_naive_datetime_treated_as_utc(self):
        past_naive = datetime.utcnow() - timedelta(hours=1)
        assert is_due(past_naive) is True


# ── overdue_days() ────────────────────────────────────────────────────────────

class TestOverdueDays:
    def test_past_date_returns_positive_days(self):
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        result = overdue_days(two_days_ago)
        assert 1.9 < result < 2.1

    def test_future_date_returns_zero(self):
        future = datetime.now(timezone.utc) + timedelta(days=5)
        assert overdue_days(future) == 0.0

    def test_naive_datetime_treated_as_utc(self):
        half_day_ago = datetime.utcnow() - timedelta(hours=12)
        result = overdue_days(half_day_ago)
        assert 0.4 < result < 0.6


# ── format_due_reviews_for_prompt() ──────────────────────────────────────────

class TestFormatDueReviewsForPrompt:
    def test_empty_list_returns_no_reviews_message(self):
        result = format_due_reviews_for_prompt([])
        assert "No concept reviews" in result

    def test_formats_basic_review(self):
        reviews = [
            {
                "concept_name": "Fractions",
                "track": "APPLIED_MATHEMATICS",
                "repetitions": 2,
                "due_at": datetime.now(timezone.utc) - timedelta(days=1),
            }
        ]
        result = format_due_reviews_for_prompt(reviews)
        assert "Fractions" in result
        assert "APPLIED_MATHEMATICS" in result

    def test_shows_overdue_suffix(self):
        reviews = [
            {
                "concept_name": "Soil pH",
                "track": "HOMESTEADING",
                "repetitions": 1,
                "due_at": datetime.now(timezone.utc) - timedelta(days=3),
            }
        ]
        result = format_due_reviews_for_prompt(reviews)
        assert "overdue" in result

    def test_caps_at_5_reviews(self):
        reviews = [
            {
                "concept_name": f"Concept {i}",
                "track": "TRUTH_HISTORY",
                "repetitions": 0,
                "due_at": datetime.now(timezone.utc) - timedelta(days=1),
            }
            for i in range(10)
        ]
        result = format_due_reviews_for_prompt(reviews)
        # Only first 5 formatted (lines 1-5)
        assert "6." not in result
