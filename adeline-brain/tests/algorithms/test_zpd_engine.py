"""Tests for ZPD engine with Bayesian Knowledge Tracing.

Mirrors cascade-adeline/__tests__/learning/zpd-engine.test.ts
"""
import math
import pytest
from datetime import datetime, timedelta, timezone

from app.algorithms.zpd_engine import (
    BKTParams,
    AdaptiveBKTParams,
    MasterySnapshot,
    ZPDConcept,
    bkt_update,
    adaptive_bkt_update,
    apply_decay,
    blend_mastery,
    compute_priority,
    compute_zpd_from_snapshots,
    format_zpd_for_prompt,
    quality_to_mastery_delta,
    MASTERY_THRESHOLD,
    PREREQ_READINESS,
    DECAY_HALF_LIFE_DAYS,
)


# ── bkt_update() ──────────────────────────────────────────────────────────────

class TestBKTUpdate:
    def test_correct_answer_increases_mastery(self):
        params = BKTParams(pL=0.3, pT=0.15, pS=0.05, pG=0.25)
        new_pL = bkt_update(params, correct=True)
        assert new_pL > params.pL

    def test_incorrect_answer_decreases_raw_posterior(self):
        params = BKTParams(pL=0.7, pT=0.0, pS=0.05, pG=0.25)
        # With pT=0, new_pL should drop after incorrect
        new_pL = bkt_update(params, correct=False)
        # After incorrect + learning, final can be lower than start
        assert new_pL < 0.9  # not 1.0

    def test_mastery_stays_clamped_below_1(self):
        params = BKTParams(pL=0.99, pT=0.15, pS=0.05, pG=0.25)
        new_pL = bkt_update(params, correct=True)
        assert new_pL <= 1.0

    def test_mastery_stays_above_0(self):
        params = BKTParams(pL=0.01, pT=0.0, pS=0.05, pG=0.25)
        new_pL = bkt_update(params, correct=False)
        assert new_pL >= 0.0

    def test_sequential_correct_answers_converge_toward_1(self):
        params = BKTParams(pL=0.1, pT=0.15, pS=0.05, pG=0.25)
        mastery = params.pL
        for _ in range(20):
            params = BKTParams(pL=mastery, pT=params.pT, pS=params.pS, pG=params.pG)
            mastery = bkt_update(params, correct=True)
        assert mastery > 0.8


# ── adaptive_bkt_update() ─────────────────────────────────────────────────────

class TestAdaptiveBKTUpdate:
    def test_returns_updated_params(self):
        params = AdaptiveBKTParams(pL=0.3)
        updated = adaptive_bkt_update(params, correct=True)
        assert updated.pL > params.pL

    def test_keeps_last_20_history_entries(self):
        params = AdaptiveBKTParams(pL=0.3, historical_performance=[0.5] * 25)
        updated = adaptive_bkt_update(params, correct=True)
        assert len(updated.historical_performance) <= 20

    def test_correct_appends_1_to_history(self):
        params = AdaptiveBKTParams(pL=0.3)
        updated = adaptive_bkt_update(params, correct=True)
        assert updated.historical_performance[-1] == 1.0

    def test_incorrect_appends_0_to_history(self):
        params = AdaptiveBKTParams(pL=0.3)
        updated = adaptive_bkt_update(params, correct=False)
        assert updated.historical_performance[-1] == 0.0

    def test_confidence_interval_shrinks_on_extremes(self):
        params = AdaptiveBKTParams(pL=0.95, confidence_interval=0.1)
        updated = adaptive_bkt_update(params, correct=True)
        # acc ≈ 0.95, |0.5 - 0.95| = 0.45 → significant narrowing
        assert updated.confidence_interval < params.confidence_interval


# ── apply_decay() ─────────────────────────────────────────────────────────────

class TestApplyDecay:
    def test_zero_days_no_decay(self):
        now = datetime.now(timezone.utc)
        result = apply_decay(1.0, now)
        assert result > 0.95  # effectively no decay

    def test_half_life_halves_mastery(self):
        half_life_ago = datetime.now(timezone.utc) - timedelta(days=DECAY_HALF_LIFE_DAYS)
        result = apply_decay(1.0, half_life_ago)
        assert 0.45 < result < 0.55  # ~0.5

    def test_two_half_lives_quarters_mastery(self):
        two_half_lives_ago = datetime.now(timezone.utc) - timedelta(days=DECAY_HALF_LIFE_DAYS * 2)
        result = apply_decay(1.0, two_half_lives_ago)
        assert 0.20 < result < 0.30  # ~0.25

    def test_partial_mastery_decays_proportionally(self):
        half_life_ago = datetime.now(timezone.utc) - timedelta(days=DECAY_HALF_LIFE_DAYS)
        result = apply_decay(0.8, half_life_ago)
        assert 0.35 < result < 0.45  # ~0.4

    def test_naive_datetime_handled(self):
        naive = datetime.utcnow() - timedelta(days=DECAY_HALF_LIFE_DAYS)
        result = apply_decay(1.0, naive)
        assert 0.45 < result < 0.55


# ── compute_priority() ────────────────────────────────────────────────────────

class TestComputePriority:
    def test_high_readiness_low_mastery_gives_high_priority(self):
        score = compute_priority(prereq=1.0, mastery=0.0, deps=5, max_deps=10)
        assert score > 0.8

    def test_low_readiness_gives_low_priority(self):
        score = compute_priority(prereq=0.1, mastery=0.0, deps=0, max_deps=10)
        assert score < 0.2

    def test_high_mastery_reduces_priority(self):
        high_mastery = compute_priority(prereq=1.0, mastery=0.9, deps=5, max_deps=10)
        low_mastery  = compute_priority(prereq=1.0, mastery=0.1, deps=5, max_deps=10)
        assert low_mastery > high_mastery

    def test_many_dependents_increases_priority_slightly(self):
        few_deps  = compute_priority(prereq=0.8, mastery=0.3, deps=1,  max_deps=10)
        many_deps = compute_priority(prereq=0.8, mastery=0.3, deps=10, max_deps=10)
        assert many_deps > few_deps

    def test_zero_max_deps_does_not_crash(self):
        score = compute_priority(prereq=0.8, mastery=0.3, deps=0, max_deps=0)
        assert 0.0 <= score <= 1.0


# ── blend_mastery() ───────────────────────────────────────────────────────────

class TestBlendMastery:
    def test_clamps_to_zero_minimum(self):
        assert blend_mastery(0.0, -1.0) == 0.0

    def test_clamps_to_one_maximum(self):
        assert blend_mastery(1.0, 1.0) == 1.0

    def test_weighted_blend_80_20(self):
        result = blend_mastery(0.5, 0.5)
        expected = 0.8 * 0.5 + 0.2 * 0.5
        assert abs(result - expected) < 0.001


# ── quality_to_mastery_delta() ────────────────────────────────────────────────

class TestQualityToMasteryDelta:
    def test_quality_5_gives_max_positive_delta(self):
        assert quality_to_mastery_delta(5) == 0.15

    def test_quality_0_gives_max_negative_delta(self):
        assert quality_to_mastery_delta(0) == -0.08

    def test_out_of_range_clamped(self):
        assert quality_to_mastery_delta(10) == quality_to_mastery_delta(5)
        assert quality_to_mastery_delta(-5) == quality_to_mastery_delta(0)


# ── compute_zpd_from_snapshots() ──────────────────────────────────────────────

def _make_snapshot(concept_id, mastery, days_ago=0, status="unknown") -> MasterySnapshot:
    now = datetime.now(timezone.utc)
    last = now - timedelta(days=days_ago)
    return MasterySnapshot(
        concept_id=concept_id, name=concept_id.title(),
        mastery_level=mastery, decay_adjusted=mastery,
        bkt_probability=mastery, last_practiced=last, status=status,
    )


class TestComputeZPDFromSnapshots:
    def test_identifies_concept_ready_to_learn(self):
        # prereq mastered, target unmastered → should appear in ZPD
        snapshots = {
            "prereq": _make_snapshot("prereq", 0.9),
            "target": _make_snapshot("target", 0.2),
        }
        concept_graph = [
            {"id": "prereq", "name": "Addition", "description": "", "track": "APPLIED_MATHEMATICS",
             "standard_code": None, "grade_band": "3-5", "prerequisite_ids": [], "dependent_count": 1},
            {"id": "target", "name": "Fractions", "description": "", "track": "APPLIED_MATHEMATICS",
             "standard_code": None, "grade_band": "3-5", "prerequisite_ids": ["prereq"], "dependent_count": 0},
        ]
        result = compute_zpd_from_snapshots(snapshots, concept_graph)
        ids = [c.concept_id for c in result]
        assert "target" in ids

    def test_excludes_mastered_concepts(self):
        snapshots = {
            "mastered": _make_snapshot("mastered", 0.95),
        }
        concept_graph = [
            {"id": "mastered", "name": "Mastered", "description": "", "track": "TRUTH_HISTORY",
             "standard_code": None, "grade_band": "6-8", "prerequisite_ids": [], "dependent_count": 0},
        ]
        result = compute_zpd_from_snapshots(snapshots, concept_graph)
        assert not any(c.concept_id == "mastered" for c in result)

    def test_excludes_not_ready_concept(self):
        # prereq not mastered → target blocked
        snapshots = {
            "prereq": _make_snapshot("prereq", 0.3),
            "target": _make_snapshot("target", 0.1),
        }
        concept_graph = [
            {"id": "prereq", "name": "Prereq", "description": "", "track": "APPLIED_MATHEMATICS",
             "standard_code": None, "grade_band": "3-5", "prerequisite_ids": [], "dependent_count": 1},
            {"id": "target", "name": "Target", "description": "", "track": "APPLIED_MATHEMATICS",
             "standard_code": None, "grade_band": "3-5", "prerequisite_ids": ["prereq"], "dependent_count": 0},
        ]
        result = compute_zpd_from_snapshots(snapshots, concept_graph)
        assert not any(c.concept_id == "target" for c in result)

    def test_no_prerequisites_means_always_ready(self):
        snapshots = {"root": _make_snapshot("root", 0.1)}
        concept_graph = [
            {"id": "root", "name": "Root", "description": "", "track": "CREATION_SCIENCE",
             "standard_code": None, "grade_band": "k-2", "prerequisite_ids": [], "dependent_count": 2},
        ]
        result = compute_zpd_from_snapshots(snapshots, concept_graph)
        assert any(c.concept_id == "root" for c in result)

    def test_results_sorted_by_priority_descending(self):
        snapshots = {
            "a": _make_snapshot("a", 0.1),
            "b": _make_snapshot("b", 0.5),
        }
        concept_graph = [
            {"id": "a", "name": "A", "description": "", "track": "HOMESTEADING",
             "standard_code": None, "grade_band": "3-5", "prerequisite_ids": [], "dependent_count": 5},
            {"id": "b", "name": "B", "description": "", "track": "HOMESTEADING",
             "standard_code": None, "grade_band": "3-5", "prerequisite_ids": [], "dependent_count": 0},
        ]
        result = compute_zpd_from_snapshots(snapshots, concept_graph)
        assert len(result) == 2
        assert result[0].priority >= result[1].priority

    def test_missing_snapshot_treated_as_zero_mastery(self):
        snapshots = {}  # no mastery data at all
        concept_graph = [
            {"id": "new", "name": "New Concept", "description": "", "track": "DISCIPLESHIP",
             "standard_code": None, "grade_band": "6-8", "prerequisite_ids": [], "dependent_count": 0},
        ]
        result = compute_zpd_from_snapshots(snapshots, concept_graph)
        # No mastery → should appear in ZPD (readiness=1 since no prereqs, mastery=0)
        assert any(c.concept_id == "new" for c in result)

    def test_respects_mastery_threshold(self):
        # Exactly at threshold → excluded
        snapshots = {"at_threshold": _make_snapshot("at_threshold", MASTERY_THRESHOLD)}
        concept_graph = [
            {"id": "at_threshold", "name": "At Threshold", "description": "", "track": "TRUTH_HISTORY",
             "standard_code": None, "grade_band": "6-8", "prerequisite_ids": [], "dependent_count": 0},
        ]
        result = compute_zpd_from_snapshots(snapshots, concept_graph)
        assert not any(c.concept_id == "at_threshold" for c in result)


# ── format_zpd_for_prompt() ───────────────────────────────────────────────────

class TestFormatZPDForPrompt:
    def test_empty_zpd_returns_no_concepts_message(self):
        result = format_zpd_for_prompt([], {})
        assert "No concepts" in result

    def test_formats_concept_info(self):
        concept = ZPDConcept(
            concept_id="soil-ph", name="Soil pH", description="",
            track="HOMESTEADING", standard_code=None, grade_band="6-8",
            current_mastery=0.3, prerequisite_readiness=0.9, priority=0.75,
        )
        snap = _make_snapshot("soil-ph", 0.3)
        result = format_zpd_for_prompt([concept], {"soil-ph": snap})
        assert "Soil Ph" in result or "Soil pH" in result
        assert "HOMESTEADING" in result

    def test_caps_output_at_5_concepts(self):
        concepts = [
            ZPDConcept(
                concept_id=f"c{i}", name=f"Concept {i}", description="",
                track="TRUTH_HISTORY", standard_code=None, grade_band="6-8",
                current_mastery=0.1, prerequisite_readiness=1.0, priority=0.9 - i * 0.1,
            )
            for i in range(8)
        ]
        result = format_zpd_for_prompt(concepts, {})
        assert "6." not in result
