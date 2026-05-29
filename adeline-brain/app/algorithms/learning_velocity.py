"""
Learning Velocity Tracker — measures mastery acquisition rate against
grade-level expectations and integrates Forgetting Curve (SM-2) signals
for adaptive pacing decisions.

Velocity = (end_mastery − start_mastery) / elapsed_hours

Forgetting Curve integration: counts SM-2 cards coming due within a
configurable horizon (default 24 h) to determine review component urgency.

Pure computation — no DB calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ── Expected mastery-gain rate by grade band (mastery points per hour) ────────
# Lower for older students: deeper concepts, slower but more durable encoding.

EXPECTED_VELOCITY: dict[str, float] = {
    "k2":  0.08,
    "35":  0.06,
    "68":  0.04,
    "912": 0.03,
}

_BAND_ALIASES: dict[str, str] = {
    "k-2": "k2", "k_2": "k2",
    "3-5": "35", "3_5": "35",
    "6-8": "68", "6_8": "68",
    "9-12": "912", "9_12": "912",
}


class VelocityStatus(str, Enum):
    ACCELERATING = "ACCELERATING"   # velocity_ratio > 1.5
    ON_PACE      = "ON_PACE"        # 0.8 – 1.5
    SLOWING      = "SLOWING"        # 0.5 – 0.8
    STALLED      = "STALLED"        # < 0.5


@dataclass
class MasteryCheckpoint:
    """One mastery observation timestamped at a point in time."""
    timestamp: datetime
    mastery_score: float
    track: str


@dataclass
class PacingRecommendation:
    status: VelocityStatus
    velocity: float                        # Actual mastery points / hour
    velocity_ratio: float                  # actual / expected
    pacing_factor: float                   # Attention-span multiplier (0.70 – 1.30)
    review_component_priority: float       # 0.0 – 1.0 urgency for SM-2 review blocks
    suggested_block_categories: list[str]  # Ordered preference list
    message: str


def _normalize_band(grade_band: str) -> str:
    key = grade_band.lower().replace(" ", "")
    return _BAND_ALIASES.get(key, key)


def compute_velocity(
    checkpoints: list[MasteryCheckpoint],
    min_checkpoints: int = 2,
) -> Optional[float]:
    """
    Compute mastery-acquisition velocity (mastery points / hour).
    Returns None when there is insufficient data.
    """
    if len(checkpoints) < min_checkpoints:
        return None

    def _utc(cp: MasteryCheckpoint) -> MasteryCheckpoint:
        if cp.timestamp.tzinfo is None:
            return MasteryCheckpoint(cp.timestamp.replace(tzinfo=timezone.utc), cp.mastery_score, cp.track)
        return cp

    ordered = sorted((_utc(c) for c in checkpoints), key=lambda c: c.timestamp)
    elapsed_hours = (ordered[-1].timestamp - ordered[0].timestamp).total_seconds() / 3_600.0
    if elapsed_hours < 1 / 60:  # Less than 1 minute — not meaningful
        return None

    return (ordered[-1].mastery_score - ordered[0].mastery_score) / elapsed_hours


def compute_due_review_count(
    sm2_cards: list[dict],
    horizon_hours: int = 24,
) -> int:
    """
    Count SM-2 cards whose next_due_at falls within the next horizon_hours.
    Integrates the Forgetting Curve: more imminent reviews → prioritize review blocks.

    Each card dict must contain a `next_due_at` key (datetime or ISO string).
    """
    now = datetime.now(timezone.utc)
    count = 0
    for card in sm2_cards:
        due = card.get("next_due_at")
        if due is None:
            continue
        if isinstance(due, str):
            due = datetime.fromisoformat(due.replace("Z", "+00:00"))
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if (due - now).total_seconds() / 3_600.0 <= horizon_hours:
            count += 1
    return count


def get_pacing_recommendation(
    checkpoints: list[MasteryCheckpoint],
    grade_band: str,
    sm2_cards: list[dict],
    sm2_horizon_hours: int = 24,
) -> PacingRecommendation:
    """
    Combine velocity analysis and forgetting curve signals into a pacing recommendation.
    """
    band = _normalize_band(grade_band)
    expected = EXPECTED_VELOCITY.get(band, 0.05)
    velocity = compute_velocity(checkpoints)
    due_reviews = compute_due_review_count(sm2_cards, horizon_hours=sm2_horizon_hours)

    # Review urgency: 5+ due cards = maximum priority
    review_priority = round(min(1.0, due_reviews / 5.0), 3)

    if velocity is None:
        return PacingRecommendation(
            status=VelocityStatus.ON_PACE,
            velocity=0.0,
            velocity_ratio=1.0,
            pacing_factor=1.0,
            review_component_priority=review_priority,
            suggested_block_categories=_categories_with_review(["multimodal"], due_reviews),
            message="Calibrating velocity — maintaining standard pace.",
        )

    ratio = velocity / expected if expected > 0 else 1.0

    if ratio > 1.5:
        status = VelocityStatus.ACCELERATING
        pacing_factor = round(min(1.30, 1.0 + (ratio - 1.5) * 0.20), 3)
        categories = ["assessment", "multimodal"]
        message = "Student is advancing quickly. Safe to increase challenge."
    elif ratio >= 0.8:
        status = VelocityStatus.ON_PACE
        pacing_factor = 1.0
        categories = ["multimodal", "assessment"]
        message = "Learning velocity on target. Maintain current pacing."
    elif ratio >= 0.5:
        status = VelocityStatus.SLOWING
        pacing_factor = round(max(0.85, 1.0 - (0.8 - ratio) * 0.50), 3)
        categories = ["feedback", "multimodal"]
        message = "Mastery acquisition slowing. Increase scaffolding and review."
    else:
        status = VelocityStatus.STALLED
        pacing_factor = 0.70
        categories = ["feedback"]
        message = "Student appears stalled. Switch modality or suggest a break."

    return PacingRecommendation(
        status=status,
        velocity=round(velocity, 4),
        velocity_ratio=round(ratio, 3),
        pacing_factor=pacing_factor,
        review_component_priority=review_priority,
        suggested_block_categories=_categories_with_review(categories, due_reviews),
        message=message,
    )


def _categories_with_review(base: list[str], due_reviews: int) -> list[str]:
    """Prepend 'assessment' when reviews are urgently due."""
    if due_reviews >= 3 and "assessment" not in base:
        return ["assessment"] + base
    return base[:3]
