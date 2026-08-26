"""Authoritative sequencing contract for learning-plan suggestions.

The prerequisite graph answers whether a curriculum concept is ready.  This
module answers the broader product question: what should happen when a mission
comes from somewhere else (an interest, a required standard, or an open
exploration) and therefore cannot honestly claim graph-verified readiness?

HARD       — a graph concept; its prerequisites must be ready before assignment.
SUPPORTED  — curiosity/coverage may begin now, but the experience must diagnose
             and bridge missing foundations before dependent work.
OPEN       — genuinely non-sequential exploration; no prerequisite claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.algorithms.zpd_engine import PREREQ_READINESS


class SequencePolicy(str, Enum):
    HARD = "HARD"
    SUPPORTED = "SUPPORTED"
    OPEN = "OPEN"


class SequenceState(str, Enum):
    READY = "READY"
    BRIDGE_REQUIRED = "BRIDGE_REQUIRED"
    OPEN = "OPEN"
    LOCKED = "LOCKED"


@dataclass(frozen=True)
class SequenceContract:
    policy: SequencePolicy
    state: SequenceState
    assignable: bool
    bridge_required: bool
    rationale: str


def policy_for_suggestion(source: str, concept_id: str | None) -> SequencePolicy:
    """Classify a mission without pretending that topic similarity is mastery."""
    normalized = (source or "").strip().lower()
    if normalized == "zpd" or (concept_id and normalized == "continue"):
        return SequencePolicy.HARD
    if normalized in {"standard", "interest", "cross_track", "continue", "explore"}:
        return SequencePolicy.SUPPORTED
    return SequencePolicy.OPEN


def build_sequence_contract(
    *,
    source: str,
    concept_id: str | None = None,
    prerequisite_readiness: float | None = None,
) -> SequenceContract:
    policy = policy_for_suggestion(source, concept_id)
    readiness = 0.0 if prerequisite_readiness is None else prerequisite_readiness

    if policy is SequencePolicy.HARD:
        ready = bool(concept_id) and readiness >= PREREQ_READINESS
        return SequenceContract(
            policy=policy,
            state=SequenceState.READY if ready else SequenceState.LOCKED,
            assignable=ready,
            bridge_required=False,
            rationale=(
                "The prerequisite graph confirms this concept is ready."
                if ready
                else "This concept stays locked until its prerequisite concepts are demonstrated."
            ),
        )

    if policy is SequencePolicy.SUPPORTED:
        return SequenceContract(
            policy=policy,
            state=SequenceState.BRIDGE_REQUIRED,
            assignable=True,
            bridge_required=True,
            rationale=(
                "This meaningful investigation may begin now, but it starts with a readiness check "
                "and supplies any missing foundation before dependent work."
            ),
        )

    return SequenceContract(
        policy=policy,
        state=SequenceState.OPEN,
        assignable=True,
        bridge_required=False,
        rationale="This exploration does not claim a prerequisite-dependent skill progression.",
    )


def suggestion_is_assignable(suggestion: object) -> bool:
    """Final fail-closed gate used immediately before Today missions are chosen."""
    policy = str(getattr(suggestion, "sequence_policy", SequencePolicy.OPEN.value))
    state = str(getattr(suggestion, "sequence_state", SequenceState.OPEN.value))
    if policy == SequencePolicy.HARD.value:
        target_id = getattr(suggestion, "sequence_target_id", None) or getattr(suggestion, "concept_id", None)
        return state == SequenceState.READY.value and bool(target_id)
    return state != SequenceState.LOCKED.value
