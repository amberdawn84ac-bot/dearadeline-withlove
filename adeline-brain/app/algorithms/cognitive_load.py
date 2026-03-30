"""Cognitive load estimation from student interaction metrics.

Ported from cascade-adeline/src/lib/cognitive-load.ts
Pure computation — no DB calls.

Estimates cognitive effort from:
  - Response time deviation from personal baseline
  - Edit distance deviation (backspace/rethink frequency)
  - Sentiment score from student text
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

MIN_HISTORY = 10


@dataclass
class Baseline:
    avg_response_time: float
    std_response_time: float
    avg_edit_distance: float
    std_edit_distance: float


@dataclass
class CognitiveLoadResult:
    score: float  # 0.0 (low) – 1.0 (critical)
    level: str    # LOW | MEDIUM | HIGH | CRITICAL


def compute_baseline(interactions: list) -> Optional[Baseline]:
    """Compute personal baseline from interaction history.
    Each item must have: {response_time_ms: int, edit_distance: int}
    Returns None if fewer than MIN_HISTORY records.
    """
    if len(interactions) < MIN_HISTORY:
        return None
    rts = [i["response_time_ms"] for i in interactions]
    eds = [i["edit_distance"]     for i in interactions]

    def mean(a: list) -> float:
        return sum(a) / len(a)

    def std(a: list, m: float) -> float:
        return math.sqrt(sum((x - m) ** 2 for x in a) / len(a))

    avg_rt = mean(rts)
    avg_ed = mean(eds)
    return Baseline(avg_rt, std(rts, avg_rt), avg_ed, std(eds, avg_ed))


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def _level(score: float) -> str:
    if score > 0.8: return "CRITICAL"
    if score > 0.6: return "HIGH"
    if score > 0.3: return "MEDIUM"
    return "LOW"


def calculate_cognitive_load(
    response_time_ms: int,
    edit_distance: int,
    sentiment_score: float,    # -1.0 (very negative) to 1.0 (very positive)
    baseline: Optional[Baseline],
) -> CognitiveLoadResult:
    """Estimate cognitive load from a single interaction.

    Weights: 0.5 response-time, 0.3 edit-distance, 0.8 sentiment.
    Without baseline, uses sentiment as the only signal.
    """
    if baseline is None:
        score = max(0.0, min(1.0, 1 - (sentiment_score + 1) / 2))
        return CognitiveLoadResult(score=score, level=_level(score))

    def z(v: float, m: float, s: float) -> float:
        return 0.0 if s == 0 else (v - m) / s

    combined = (
        0.5 * _sigmoid(z(response_time_ms, baseline.avg_response_time, baseline.std_response_time))
        + 0.3 * _sigmoid(z(edit_distance,  baseline.avg_edit_distance,  baseline.std_edit_distance))
        + 0.8 * (1 - (sentiment_score + 1) / 2)
    )
    score = max(0.0, min(1.0, combined / 1.6))  # 1.6 = sum of weights
    return CognitiveLoadResult(score=score, level=_level(score))


def should_simplify_content(load: CognitiveLoadResult) -> bool:
    return load.level in ("HIGH", "CRITICAL")


def get_pacing_recommendation(load: CognitiveLoadResult) -> str:
    return {
        "CRITICAL": "Student appears overwhelmed. Switch to a single simple concept. Pause new material.",
        "HIGH":     "Student shows signs of strain. Simplify vocabulary. Reduce block count.",
        "MEDIUM":   "Moderate load. Maintain pacing. Check for understanding before advancing.",
        "LOW":      "Low load. Student is engaged. Safe to advance complexity.",
    }[load.level]
