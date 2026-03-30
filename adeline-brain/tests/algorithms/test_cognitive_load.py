"""Tests for cognitive load estimation algorithm."""
import pytest

from app.algorithms.cognitive_load import (
    Baseline,
    CognitiveLoadResult,
    calculate_cognitive_load,
    compute_baseline,
    get_pacing_recommendation,
    should_simplify_content,
    MIN_HISTORY,
)


# ── compute_baseline() ────────────────────────────────────────────────────────

class TestComputeBaseline:
    def _make_interactions(self, n: int, rt: int = 3000, ed: int = 10) -> list:
        return [{"response_time_ms": rt, "edit_distance": ed} for _ in range(n)]

    def test_returns_none_if_fewer_than_min_history(self):
        interactions = self._make_interactions(MIN_HISTORY - 1)
        assert compute_baseline(interactions) is None

    def test_returns_baseline_at_min_history(self):
        interactions = self._make_interactions(MIN_HISTORY)
        result = compute_baseline(interactions)
        assert result is not None
        assert result.avg_response_time == 3000
        assert result.avg_edit_distance == 10

    def test_std_is_zero_for_uniform_data(self):
        interactions = self._make_interactions(20)
        baseline = compute_baseline(interactions)
        assert baseline.std_response_time == 0.0
        assert baseline.std_edit_distance == 0.0

    def test_computes_correct_mean(self):
        interactions = [
            {"response_time_ms": 1000, "edit_distance": 5},
            {"response_time_ms": 3000, "edit_distance": 15},
            {"response_time_ms": 2000, "edit_distance": 10},
        ] * 5  # 15 records
        baseline = compute_baseline(interactions)
        assert abs(baseline.avg_response_time - 2000) < 0.01
        assert abs(baseline.avg_edit_distance - 10) < 0.01

    def test_computes_nonzero_std_for_varied_data(self):
        interactions = [
            {"response_time_ms": rt, "edit_distance": 5}
            for rt in [1000, 2000, 3000, 4000, 5000] * 3  # 15 records
        ]
        baseline = compute_baseline(interactions)
        assert baseline.std_response_time > 0


# ── calculate_cognitive_load() ────────────────────────────────────────────────

class TestCalculateCognitiveLoad:
    def test_no_baseline_uses_sentiment_only(self):
        # Positive sentiment → low load
        result = calculate_cognitive_load(
            response_time_ms=3000, edit_distance=5,
            sentiment_score=0.8, baseline=None,
        )
        assert result.level == "LOW"

    def test_no_baseline_negative_sentiment_gives_high_load(self):
        result = calculate_cognitive_load(
            response_time_ms=3000, edit_distance=5,
            sentiment_score=-0.9, baseline=None,
        )
        assert result.level in ("HIGH", "CRITICAL")

    def test_score_is_clamped_between_0_and_1(self):
        baseline = Baseline(
            avg_response_time=2000, std_response_time=500,
            avg_edit_distance=10, std_edit_distance=3,
        )
        result = calculate_cognitive_load(
            response_time_ms=100, edit_distance=1,
            sentiment_score=1.0, baseline=baseline,
        )
        assert 0.0 <= result.score <= 1.0

    def test_slow_response_with_negative_sentiment_gives_high_load(self):
        baseline = Baseline(
            avg_response_time=2000, std_response_time=500,
            avg_edit_distance=10, std_edit_distance=3,
        )
        result = calculate_cognitive_load(
            response_time_ms=5000, edit_distance=30,
            sentiment_score=-0.8, baseline=baseline,
        )
        assert result.level in ("HIGH", "CRITICAL")

    def test_average_response_with_positive_sentiment_gives_low_medium_load(self):
        baseline = Baseline(
            avg_response_time=2000, std_response_time=500,
            avg_edit_distance=10, std_edit_distance=3,
        )
        result = calculate_cognitive_load(
            response_time_ms=2000, edit_distance=10,
            sentiment_score=0.5, baseline=baseline,
        )
        assert result.level in ("LOW", "MEDIUM")

    def test_zero_std_does_not_crash(self):
        baseline = Baseline(
            avg_response_time=2000, std_response_time=0,
            avg_edit_distance=10, std_edit_distance=0,
        )
        result = calculate_cognitive_load(
            response_time_ms=2000, edit_distance=10,
            sentiment_score=0.0, baseline=baseline,
        )
        assert result is not None


# ── Level thresholds ──────────────────────────────────────────────────────────

class TestCognitiveLoadLevels:
    def _result_for_score(self, score: float) -> CognitiveLoadResult:
        from app.algorithms.cognitive_load import _level
        return CognitiveLoadResult(score=score, level=_level(score))

    def test_above_0_8_is_critical(self):
        r = self._result_for_score(0.9)
        assert r.level == "CRITICAL"

    def test_between_0_6_and_0_8_is_high(self):
        r = self._result_for_score(0.7)
        assert r.level == "HIGH"

    def test_between_0_3_and_0_6_is_medium(self):
        r = self._result_for_score(0.45)
        assert r.level == "MEDIUM"

    def test_below_0_3_is_low(self):
        r = self._result_for_score(0.1)
        assert r.level == "LOW"


# ── should_simplify_content() ─────────────────────────────────────────────────

class TestShouldSimplifyContent:
    def test_critical_should_simplify(self):
        assert should_simplify_content(CognitiveLoadResult(0.9, "CRITICAL")) is True

    def test_high_should_simplify(self):
        assert should_simplify_content(CognitiveLoadResult(0.7, "HIGH")) is True

    def test_medium_should_not_simplify(self):
        assert should_simplify_content(CognitiveLoadResult(0.45, "MEDIUM")) is False

    def test_low_should_not_simplify(self):
        assert should_simplify_content(CognitiveLoadResult(0.1, "LOW")) is False


# ── get_pacing_recommendation() ───────────────────────────────────────────────

class TestGetPacingRecommendation:
    def test_critical_recommends_pause(self):
        rec = get_pacing_recommendation(CognitiveLoadResult(0.9, "CRITICAL"))
        assert "overwhelmed" in rec.lower() or "pause" in rec.lower()

    def test_high_recommends_simplify(self):
        rec = get_pacing_recommendation(CognitiveLoadResult(0.7, "HIGH"))
        assert "simplify" in rec.lower() or "strain" in rec.lower()

    def test_medium_recommends_maintain(self):
        rec = get_pacing_recommendation(CognitiveLoadResult(0.45, "MEDIUM"))
        assert "maintain" in rec.lower() or "moderate" in rec.lower()

    def test_low_recommends_advance(self):
        rec = get_pacing_recommendation(CognitiveLoadResult(0.1, "LOW"))
        assert "advance" in rec.lower() or "engaged" in rec.lower()
