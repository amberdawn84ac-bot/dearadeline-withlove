"""
Learner Profile Classifier — supervised ML (decision tree) for categorizing
learner archetypes from interaction signals.

Features used (mirrors SVM feature space):
  - correct_rate:           fraction of correct answers (BKT performance)
  - avg_response_velocity:  normalized inverse of response time (faster = higher)
  - modality_entropy:       Shannon entropy of modality engagement (higher = explorer)
  - struggle_ratio:         consecutive struggles / total interactions
  - preferred_modality:     most-used engagement channel

Pure computation — no DB calls.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class LearnerProfileType(str, Enum):
    EXPLORER     = "EXPLORER"      # Broad, curious, prefers discovery
    BUILDER      = "BUILDER"       # Kinesthetic, step-by-step, hands-on
    PRACTITIONER = "PRACTITIONER"  # Mastery-driven, quiz-oriented, precise
    REFLECTOR    = "REFLECTOR"     # Deep reader, slow + thorough, text-first


# Component affinity per profile — informs content-based and RL layers
PROFILE_COMPONENT_AFFINITY: dict[LearnerProfileType, list[str]] = {
    LearnerProfileType.EXPLORER:     ["SimulationEmbed", "RealWorldApplication", "AutoDiagram"],
    LearnerProfileType.BUILDER:      ["VirtualManipulative", "MultiCompetencyWorkspace", "RealWorldApplication"],
    LearnerProfileType.PRACTITIONER: ["AdaptiveQuiz", "StealthAssessment", "MultiCompetencyWorkspace"],
    LearnerProfileType.REFLECTOR:    ["TextExplanation", "VideoExplanation", "CorrectiveOverlay"],
}


@dataclass
class InteractionRecord:
    response_time_ms: int
    edit_distance: int
    correct: bool
    component_used: str
    modality: str  # "visual" | "auditory" | "kinesthetic" | "reading"


@dataclass
class LearnerProfileFeatures:
    correct_rate: float           # 0.0 – 1.0
    avg_response_velocity: float  # 0.0 – 1.0 (normalized)
    modality_entropy: float       # 0.0 – 1.0 (normalized Shannon entropy)
    struggle_ratio: float         # 0.0 – 1.0
    preferred_modality: str


@dataclass
class LearnerProfile:
    profile_type: LearnerProfileType
    confidence: float
    features: LearnerProfileFeatures
    preferred_components: list[str] = field(default_factory=list)


def _normalized_entropy(counts: dict[str, int]) -> float:
    """Shannon entropy normalized to [0, 1] by log2(|categories|)."""
    total = sum(counts.values())
    if total == 0 or len(counts) <= 1:
        return 0.0
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)
    return entropy / math.log2(len(counts))


def extract_features(
    interactions: list[InteractionRecord],
    consecutive_struggles: int = 0,
) -> LearnerProfileFeatures:
    """Extract classification features from raw interaction records."""
    if not interactions:
        return LearnerProfileFeatures(
            correct_rate=0.5,
            avg_response_velocity=0.5,
            modality_entropy=0.5,
            struggle_ratio=0.0,
            preferred_modality="visual",
        )

    n = len(interactions)
    correct_rate = sum(1 for i in interactions if i.correct) / n

    avg_rt = sum(i.response_time_ms for i in interactions) / n
    # Normalize: 3 000 ms → velocity = 1.0; faster responses score higher
    avg_response_velocity = min(1.0, 3_000.0 / max(avg_rt, 100))

    modality_counts: dict[str, int] = {}
    for rec in interactions:
        modality_counts[rec.modality] = modality_counts.get(rec.modality, 0) + 1

    modality_entropy = _normalized_entropy(modality_counts)
    preferred_modality = max(modality_counts, key=lambda k: modality_counts[k])

    struggle_ratio = min(1.0, consecutive_struggles / max(n, 1))

    return LearnerProfileFeatures(
        correct_rate=correct_rate,
        avg_response_velocity=avg_response_velocity,
        modality_entropy=modality_entropy,
        struggle_ratio=struggle_ratio,
        preferred_modality=preferred_modality,
    )


def classify_learner_profile(features: LearnerProfileFeatures) -> LearnerProfile:
    """
    Decision tree classifier for learner archetype.

    Depth-2 tree:
    ├── correct_rate >= 0.72
    │   ├── struggle_ratio < 0.10  → PRACTITIONER
    │   └── struggle_ratio >= 0.10 → BUILDER
    └── correct_rate < 0.72
        ├── modality_entropy >= 0.50 → EXPLORER
        └── modality_entropy < 0.50  → REFLECTOR

    Confidence is the margin from the decision boundary, clamped to [0.5, 1.0].
    """
    f = features

    if f.correct_rate >= 0.72:
        margin_accuracy = (f.correct_rate - 0.72) / 0.28   # 0 – 1
        if f.struggle_ratio < 0.10:
            profile_type = LearnerProfileType.PRACTITIONER
            margin_struggle = (0.10 - f.struggle_ratio) / 0.10  # 0 – 1
            confidence = 0.5 + 0.25 * margin_accuracy + 0.25 * margin_struggle
        else:
            profile_type = LearnerProfileType.BUILDER
            margin_struggle = min(1.0, (f.struggle_ratio - 0.10) / 0.30)
            confidence = 0.5 + 0.25 * margin_accuracy + 0.25 * margin_struggle
    else:
        margin_accuracy = (0.72 - f.correct_rate) / 0.72   # 0 – 1
        if f.modality_entropy >= 0.50:
            profile_type = LearnerProfileType.EXPLORER
            margin_entropy = (f.modality_entropy - 0.50) / 0.50  # 0 – 1
            confidence = 0.5 + 0.25 * margin_entropy + 0.25 * margin_accuracy
        else:
            profile_type = LearnerProfileType.REFLECTOR
            # Reflectors are slow, deliberate, low entropy
            margin_entropy = (0.50 - f.modality_entropy) / 0.50
            margin_velocity = 1.0 - f.avg_response_velocity
            confidence = 0.5 + 0.15 * margin_entropy + 0.20 * margin_velocity + 0.15 * margin_accuracy

    return LearnerProfile(
        profile_type=profile_type,
        confidence=round(max(0.5, min(1.0, confidence)), 3),
        features=features,
        preferred_components=PROFILE_COMPONENT_AFFINITY[profile_type],
    )
