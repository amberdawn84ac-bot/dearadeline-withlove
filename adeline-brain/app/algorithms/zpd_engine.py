"""ZPD engine with Bayesian Knowledge Tracing.

Ported from cascade-adeline/src/lib/zpd-engine.ts
Pure computation — no DB calls. API routes fetch data and pass it in.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

MASTERY_THRESHOLD    = 0.7
PREREQ_READINESS     = 0.7
DECAY_HALF_LIFE_DAYS = 30


@dataclass
class BKTParams:
    """4-parameter Bayesian Knowledge Tracing model."""
    pL: float = 0.1   # P(L)  current mastery probability
    pT: float = 0.15  # P(T)  learning rate per opportunity
    pS: float = 0.05  # P(S)  slip rate
    pG: float = 0.25  # P(G)  guess rate


@dataclass
class AdaptiveBKTParams(BKTParams):
    student_learning_rate:  float = 0.15
    concept_difficulty:     float = 0.5
    historical_performance: list  = field(default_factory=list)
    confidence_interval:    float = 0.1


def bkt_update(params: BKTParams, correct: bool) -> float:
    """Bayesian update of mastery probability after one observation."""
    pL, pT, pS, pG = params.pL, params.pT, params.pS, params.pG
    if correct:
        p_c  = pL * (1 - pS) + (1 - pL) * pG
        post = (pL * (1 - pS)) / p_c
    else:
        p_i  = pL * pS + (1 - pL) * (1 - pG)
        post = (pL * pS) / p_i
    return post + (1 - post) * pT


def adaptive_bkt_update(params: AdaptiveBKTParams, correct: bool) -> AdaptiveBKTParams:
    new_pL = bkt_update(params, correct)
    acc    = params.pL if correct else (1 - params.pL)
    ci     = max(0.05, params.confidence_interval - abs(0.5 - acc) * 0.1)
    return AdaptiveBKTParams(
        pL=new_pL, pT=params.pT, pS=params.pS, pG=params.pG,
        student_learning_rate=params.student_learning_rate,
        concept_difficulty=params.concept_difficulty,
        historical_performance=params.historical_performance[-19:] + [1.0 if correct else 0.0],
        confidence_interval=ci,
    )


def apply_decay(mastery: float, last_practiced: datetime) -> float:
    """Exponential forgetting-curve decay (halves every DECAY_HALF_LIFE_DAYS days)."""
    now = datetime.now(timezone.utc)
    if last_practiced.tzinfo is None:
        last_practiced = last_practiced.replace(tzinfo=timezone.utc)
    days = (now - last_practiced).total_seconds() / 86_400
    return mastery * math.pow(0.5, max(0, days) / DECAY_HALF_LIFE_DAYS)


def compute_priority(prereq: float, mastery: float, deps: int, max_deps: int) -> float:
    """ZPD priority: 0.6*readiness + 0.3*gap + 0.1*leverage."""
    leverage = (deps / max_deps) if max_deps > 0 else 0
    return 0.6 * prereq + 0.3 * (1 - mastery) + 0.1 * leverage


def blend_mastery(bkt: float, delta: float) -> float:
    """80% BKT + 20% delta, clamped to [0, 1]."""
    return max(0.0, min(1.0, 0.8 * bkt + 0.2 * delta))


def quality_to_mastery_delta(quality: int) -> float:
    return {5: 0.15, 4: 0.10, 3: 0.05, 2: -0.02, 1: -0.05, 0: -0.08}.get(
        max(0, min(5, quality)), 0.0
    )


@dataclass
class ZPDConcept:
    concept_id:             str
    name:                   str
    description:            str
    track:                  str
    standard_code:          Optional[str]
    grade_band:             Optional[str]
    current_mastery:        float
    prerequisite_readiness: float
    priority:               float


@dataclass
class MasterySnapshot:
    concept_id:      str
    name:            str
    mastery_level:   float
    decay_adjusted:  float
    bkt_probability: float
    last_practiced:  Optional[datetime]
    status:          str  # mastered | in_zpd | not_ready | unknown


def compute_zpd_from_snapshots(snapshots: dict, concept_graph: list) -> list:
    """Identify ZPD concepts from pre-fetched mastery snapshots.

    concept_graph entries must have keys:
    id, name, description, track, standard_code, grade_band,
    prerequisite_ids (list[str]), dependent_count (int)
    """
    max_deps = max((c["dependent_count"] for c in concept_graph), default=1)
    result: list[ZPDConcept] = []

    for c in concept_graph:
        snap    = snapshots.get(c["id"])
        mastery = snap.decay_adjusted if snap else 0.0

        if mastery >= MASTERY_THRESHOLD:
            if snap: snap.status = "mastered"
            continue

        prereq_ids = c.get("prerequisite_ids", [])
        if not prereq_ids:
            readiness = 1.0
        else:
            readiness = sum(
                snapshots[p].decay_adjusted if p in snapshots else 0.0
                for p in prereq_ids
            ) / len(prereq_ids)

        if readiness < PREREQ_READINESS:
            if snap: snap.status = "not_ready"
            continue

        if snap: snap.status = "in_zpd"

        result.append(ZPDConcept(
            concept_id=c["id"], name=c["name"], description=c["description"],
            track=c["track"], standard_code=c.get("standard_code"),
            grade_band=c.get("grade_band"), current_mastery=mastery,
            prerequisite_readiness=readiness,
            priority=compute_priority(readiness, mastery, c["dependent_count"], max_deps),
        ))

    result.sort(key=lambda x: x.priority, reverse=True)
    return result


def format_zpd_for_prompt(zpd: list, snapshots: dict) -> str:
    if not zpd:
        return "No concepts currently in the student's Zone of Proximal Development."
    lines = []
    for i, c in enumerate(zpd[:5], 1):
        snap = snapshots.get(c.concept_id)
        bkt  = snap.bkt_probability if snap else c.current_mastery
        g    = f", {c.grade_band}" if c.grade_band else ""
        lines.append(
            f"{i}. **{c.name}** ({c.track}{g}) — "
            f"BKT P(L)={bkt:.2f}, Mastery={c.current_mastery*100:.0f}%, "
            f"Prereq={c.prerequisite_readiness*100:.0f}%, Priority={c.priority*100:.0f}%"
        )
    return "ZPD (top concepts):\n" + "\n".join(lines)
