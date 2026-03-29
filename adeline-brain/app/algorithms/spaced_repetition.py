"""SM-2 Spaced Repetition Algorithm.

Ported from cascade-adeline/src/lib/spaced-repetition.ts
Pure computation — no DB calls.

Quality scale 0–5:
  0=blackout  1=wrong(easy after)  2=wrong  3=hard-correct  4=hesitation  5=perfect
Quality >= 3 = pass (interval grows). Quality < 3 = fail (resets to 1 day).
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class SM2Result:
    interval:    int      # days until next review
    ease_factor: float    # updated ease factor (min 1.3)
    repetitions: int      # consecutive successful review count
    next_due_at: datetime


def sm2(
    quality: int,
    prev_interval: int,
    prev_ease: float,
    prev_reps: int,
) -> SM2Result:
    """Core SM-2 scheduling. EF' = EF + (0.1 - (5-q)*(0.08 + (5-q)*0.02))"""
    q = max(0, min(5, quality))
    if q >= 3:
        reps     = prev_reps + 1
        interval = 1 if reps == 1 else 6 if reps == 2 else round(prev_interval * prev_ease)
        ef       = prev_ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    else:
        reps, interval, ef = 0, 1, prev_ease
    ef = max(1.3, ef)
    return SM2Result(
        interval=interval, ease_factor=ef, repetitions=reps,
        next_due_at=datetime.now(timezone.utc) + timedelta(days=interval),
    )


def quality_to_mastery_delta(quality: int) -> float:
    """Map SM-2 quality (0–5) to a mastery delta for BKT blending."""
    return {5: 0.15, 4: 0.10, 3: 0.05, 2: -0.02, 1: -0.05, 0: -0.08}.get(
        max(0, min(5, quality)), 0.0
    )


def is_due(due_at: datetime) -> bool:
    now = datetime.now(timezone.utc)
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    return now >= due_at


def overdue_days(due_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    return max(0.0, (now - due_at).total_seconds() / 86_400)


def format_due_reviews_for_prompt(reviews: list) -> str:
    """Format due review list for agent prompt injection.
    Each dict: {concept_name, track, repetitions, due_at}
    """
    if not reviews:
        return "No concept reviews currently due."
    lines = []
    for i, r in enumerate(reviews[:5], 1):
        od     = overdue_days(r["due_at"]) if isinstance(r.get("due_at"), datetime) else 0
        suffix = f" ({od:.0f}d overdue)" if od > 0 else ""
        lines.append(f"{i}. **{r['concept_name']}** ({r['track']}) — Review #{r['repetitions']+1}{suffix}")
    return f"Due for review ({len(reviews)}):\n" + "\n".join(lines)
