"""
Component Selector Algorithm — picks optimal GenUI components for a learner.

Uses learner state (mastery, modality preference, recent struggle patterns)
to select the best component(s) from the registry for the next content block.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── Component Registry (mirrors frontend registry) ─────────────────────────────

COMPONENT_REGISTRY = {
    "SimulationEmbed": {
        "category": "multimodal",
        "modalities": ["visual", "kinesthetic"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 5,
        "stealth_assessment": False,
        "tags": ["science", "math", "exploration", "hands-on"],
    },
    "VirtualManipulative": {
        "category": "multimodal",
        "modalities": ["kinesthetic", "visual"],
        "difficulties": ["EMERGING", "DEVELOPING"],
        "estimated_minutes": 4,
        "stealth_assessment": False,
        "tags": ["math", "concrete", "hands-on", "spatial"],
    },
    "VideoExplanation": {
        "category": "multimodal",
        "modalities": ["visual", "auditory"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 6,
        "stealth_assessment": False,
        "tags": ["explanation", "lecture", "visual-learner", "passive"],
    },
    "TextExplanation": {
        "category": "multimodal",
        "modalities": ["reading"],
        "difficulties": ["DEVELOPING", "MASTERING"],
        "estimated_minutes": 4,
        "stealth_assessment": False,
        "tags": ["reading", "text", "reference", "key-terms"],
    },
    "RealWorldApplication": {
        "category": "multimodal",
        "modalities": ["reading", "kinesthetic"],
        "difficulties": ["DEVELOPING", "MASTERING"],
        "estimated_minutes": 7,
        "stealth_assessment": True,
        "tags": ["application", "scenario", "problem-solving", "transfer"],
    },
    "StealthAssessment": {
        "category": "assessment",
        "modalities": ["reading", "kinesthetic"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 4,
        "stealth_assessment": True,
        "tags": ["assessment", "stealth", "mastery-inference"],
    },
    "AdaptiveQuiz": {
        "category": "assessment",
        "modalities": ["reading"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 5,
        "stealth_assessment": False,
        "tags": ["quiz", "adaptive", "mastery-check"],
    },
    "MultiCompetencyWorkspace": {
        "category": "assessment",
        "modalities": ["reading", "kinesthetic"],
        "difficulties": ["DEVELOPING", "MASTERING"],
        "estimated_minutes": 8,
        "stealth_assessment": True,
        "tags": ["multi-skill", "complex", "synthesis"],
    },
    "CorrectiveOverlay": {
        "category": "feedback",
        "modalities": ["reading", "visual"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 2,
        "stealth_assessment": False,
        "tags": ["feedback", "error-correction", "scaffolding"],
    },
    "LearningVelocityCard": {
        "category": "visualization",
        "modalities": ["visual"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 1,
        "stealth_assessment": False,
        "tags": ["dashboard", "metrics", "motivation"],
    },
    "ProgressMap": {
        "category": "visualization",
        "modalities": ["visual"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 1,
        "stealth_assessment": False,
        "tags": ["navigation", "progress", "path"],
    },
    "AutoDiagram": {
        "category": "visualization",
        "modalities": ["visual"],
        "difficulties": ["DEVELOPING", "MASTERING"],
        "estimated_minutes": 2,
        "stealth_assessment": False,
        "tags": ["diagram", "concept-map", "relationships"],
    },
}


@dataclass
class LearnerContext:
    """Learner state for component selection."""
    mastery_score: float = 0.5
    difficulty: str = "DEVELOPING"
    preferred_modalities: list[str] = field(default_factory=lambda: ["visual", "reading"])
    recent_struggle_count: int = 0
    time_available_minutes: int = 15
    needs_assessment: bool = False
    topic_tags: list[str] = field(default_factory=list)
    recently_used_components: list[str] = field(default_factory=list)


@dataclass
class ComponentRecommendation:
    """A scored component recommendation."""
    component_id: str
    score: float
    reason: str


def select_components(
    context: LearnerContext,
    max_results: int = 3,
    exclude_categories: Optional[list[str]] = None,
) -> list[ComponentRecommendation]:
    """
    Select the best components for the given learner context.

    Scoring factors:
    - Modality alignment (0.25 weight)
    - Difficulty fit (0.15 weight)
    - Time fit (0.10 weight)
    - Assessment need (0.20 weight)
    - Tag relevance (0.15 weight)
    - Recency penalty (0.10 weight — avoid repeating recently used)
    - Struggle boost (0.05 weight — favor scaffolding if struggling)
    """
    exclude_categories = exclude_categories or []
    scored: list[ComponentRecommendation] = []

    for comp_id, meta in COMPONENT_REGISTRY.items():
        if meta["category"] in exclude_categories:
            continue

        score = 0.0
        reasons: list[str] = []

        # 1. Modality alignment (0.25)
        modality_overlap = len(set(meta["modalities"]) & set(context.preferred_modalities))
        modality_score = modality_overlap / max(len(context.preferred_modalities), 1)
        score += modality_score * 0.25
        if modality_score > 0.5:
            reasons.append("modality match")

        # 2. Difficulty fit (0.15)
        if context.difficulty in meta["difficulties"]:
            score += 0.15
            reasons.append("difficulty fit")

        # 3. Time fit (0.10)
        if meta["estimated_minutes"] <= context.time_available_minutes:
            score += 0.10
        elif meta["estimated_minutes"] <= context.time_available_minutes * 1.2:
            score += 0.05

        # 4. Assessment need (0.20)
        if context.needs_assessment and meta["stealth_assessment"]:
            score += 0.20
            reasons.append("assessment needed")
        elif not context.needs_assessment and not meta["stealth_assessment"]:
            score += 0.05

        # 5. Tag relevance (0.15)
        if context.topic_tags:
            tag_overlap = len(set(meta["tags"]) & set(context.topic_tags))
            tag_score = tag_overlap / max(len(context.topic_tags), 1)
            score += tag_score * 0.15
            if tag_score > 0.3:
                reasons.append("topic relevant")

        # 6. Recency penalty (0.10)
        if comp_id in context.recently_used_components:
            score -= 0.10
        else:
            score += 0.05

        # 7. Struggle boost (0.05)
        if context.recent_struggle_count >= 2:
            if meta["category"] == "feedback":
                score += 0.10
                reasons.append("struggle scaffolding")
            elif meta["category"] == "multimodal" and "kinesthetic" in meta["modalities"]:
                score += 0.05
                reasons.append("hands-on for struggle")

        scored.append(ComponentRecommendation(
            component_id=comp_id,
            score=round(max(0, min(1, score)), 3),
            reason=", ".join(reasons) if reasons else "general fit",
        ))

    # Sort by score descending and return top N
    scored.sort(key=lambda r: r.score, reverse=True)
    results = scored[:max_results]

    logger.info(
        f"[COMPONENT_SELECTOR] Selected {[r.component_id for r in results]} "
        f"for context: mastery={context.mastery_score}, difficulty={context.difficulty}, "
        f"modalities={context.preferred_modalities}"
    )

    return results


def select_remediation_component(context: LearnerContext) -> ComponentRecommendation:
    """
    Select the best component for remediation when student is struggling.
    Prioritizes scaffolding and hands-on components.
    """
    context.recent_struggle_count = max(context.recent_struggle_count, 2)
    context.needs_assessment = False

    results = select_components(
        context,
        max_results=1,
        exclude_categories=["assessment"],
    )

    if results:
        return results[0]

    # Fallback: CorrectiveOverlay is always appropriate for remediation
    return ComponentRecommendation(
        component_id="CorrectiveOverlay",
        score=0.8,
        reason="default remediation fallback",
    )
