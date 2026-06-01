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
    # ── Multi-Modal Representation ──────────────────────────────────────────────
    "SimulationEmbed": {
        "category": "multimodal",
        "modalities": ["visual", "kinesthetic"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 5,
        "stealth_assessment": False,
        "tags": ["science", "math", "exploration", "hands-on"],
        "concept_types": ["science"],
        "abstraction": "concrete",
    },
    "VirtualManipulative": {
        "category": "multimodal",
        "modalities": ["kinesthetic", "visual"],
        "difficulties": ["EMERGING", "DEVELOPING"],
        "estimated_minutes": 4,
        "stealth_assessment": False,
        "tags": ["math", "concrete", "hands-on", "spatial"],
        "concept_types": ["math"],
        "abstraction": "concrete",
    },
    "VideoExplanation": {
        "category": "multimodal",
        "modalities": ["visual", "auditory"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 6,
        "stealth_assessment": False,
        "tags": ["explanation", "lecture", "visual-learner", "passive"],
        "concept_types": ["any"],
        "abstraction": "concrete",
    },
    "TextExplanation": {
        "category": "multimodal",
        "modalities": ["reading", "text"],
        "difficulties": ["DEVELOPING", "MASTERING"],
        "estimated_minutes": 4,
        "stealth_assessment": False,
        "tags": ["reading", "text", "reference", "key-terms"],
        "concept_types": ["any"],
        "abstraction": "any",
    },
    "RealWorldApplication": {
        "category": "multimodal",
        "modalities": ["reading", "kinesthetic", "text"],
        "difficulties": ["DEVELOPING", "MASTERING"],
        "estimated_minutes": 7,
        "stealth_assessment": True,
        "tags": ["application", "scenario", "problem-solving", "transfer"],
        "concept_types": ["any"],
        "abstraction": "concrete",
    },
    "MoleculeSimulator": {
        "category": "multimodal",
        "modalities": ["visual", "kinesthetic"],
        "difficulties": ["DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 5,
        "stealth_assessment": False,
        "tags": ["science", "chemistry", "physics", "hands-on"],
        "concept_types": ["science"],
        "abstraction": "concrete",
    },
    "AutoDiagram": {
        "category": "visualization",
        "modalities": ["visual"],
        "difficulties": ["DEVELOPING", "MASTERING"],
        "estimated_minutes": 2,
        "stealth_assessment": False,
        "tags": ["diagram", "concept-map", "relationships"],
        "concept_types": ["any"],
        "abstraction": "abstract",
    },
    # ── ALU Multimodal — Audio Dialogue ─────────────────────────────────────────
    "AudioDialogue": {
        "category": "multimodal",
        "modalities": ["auditory", "visual"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 4,
        "stealth_assessment": False,
        "tags": ["audio", "dialogue", "misconceptions", "podcast", "listening"],
        "concept_types": ["any"],
        "abstraction": "concrete",
    },
    # ── Additional first-class block types ──────────────────────────────────────
    "Simulation": {
        "category": "multimodal",
        "modalities": ["kinesthetic", "visual"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 5,
        "stealth_assessment": True,
        "tags": ["science", "math", "exploration", "hands-on", "interactive"],
        "concept_types": ["science", "math"],
        "abstraction": "concrete",
    },
    "TextDeep": {
        "category": "multimodal",
        "modalities": ["reading", "text"],
        "difficulties": ["DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 8,
        "stealth_assessment": False,
        "tags": ["reading", "text", "reference", "deep-dive", "key-terms"],
        "concept_types": ["any"],
        "abstraction": "abstract",
    },
    "ConceptMap": {
        "category": "visualization",
        "modalities": ["visual"],
        "difficulties": ["DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 3,
        "stealth_assessment": False,
        "tags": ["concept-map", "relationships", "synthesis", "visual"],
        "concept_types": ["any"],
        "abstraction": "abstract",
    },
    # ── Stealth & Adaptive Assessment ───────────────────────────────────────────
    "StealthAssessment": {
        "category": "assessment",
        "modalities": ["reading", "kinesthetic"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 4,
        "stealth_assessment": True,
        "tags": ["assessment", "stealth", "mastery-inference"],
        "concept_types": ["any"],
        "abstraction": "any",
    },
    "AdaptiveQuiz": {
        "category": "assessment",
        "modalities": ["reading", "text"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 5,
        "stealth_assessment": False,
        "tags": ["quiz", "adaptive", "mastery-check"],
        "concept_types": ["any"],
        "abstraction": "any",
    },
    "MultiCompetencyWorkspace": {
        "category": "assessment",
        "modalities": ["reading", "kinesthetic"],
        "difficulties": ["DEVELOPING", "MASTERING"],
        "estimated_minutes": 8,
        "stealth_assessment": True,
        "tags": ["multi-skill", "complex", "synthesis"],
        "concept_types": ["any"],
        "abstraction": "abstract",
    },
    "ScaffoldedProblem": {
        "category": "assessment",
        "modalities": ["reading", "text", "kinesthetic"],
        "difficulties": ["DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 6,
        "stealth_assessment": False,
        "tags": ["problem-solving", "scaffolding", "math", "step-by-step"],
        "concept_types": ["math", "science"],
        "abstraction": "abstract",
    },
    "HardThingChallenge": {
        "category": "assessment",
        "modalities": ["text", "reading"],
        "difficulties": ["EXPANDING", "MASTERING"],
        "estimated_minutes": 10,
        "stealth_assessment": False,
        "tags": ["challenge", "mastery", "misconceptions", "deep-learning"],
        "concept_types": ["any"],
        "abstraction": "abstract",
    },
    # ── Intelligent Feedback & Scaffolding ──────────────────────────────────────
    "CorrectiveOverlay": {
        "category": "feedback",
        "modalities": ["reading", "visual", "text"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 2,
        "stealth_assessment": False,
        "tags": ["feedback", "error-correction", "scaffolding"],
        "concept_types": ["any"],
        "abstraction": "any",
    },
    "GlowGrow": {
        "category": "feedback",
        "modalities": ["reading", "text"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 2,
        "stealth_assessment": False,
        "tags": ["feedback", "formative", "sel", "reflection"],
        "concept_types": ["any"],
        "abstraction": "any",
    },
    "TaskScaffold": {
        "category": "scaffolding",
        "modalities": ["text", "kinesthetic"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING"],
        "estimated_minutes": 5,
        "stealth_assessment": False,
        "tags": ["task", "step-by-step", "guidance", "hints"],
        "concept_types": ["any"],
        "abstraction": "concrete",
    },
    "LearningVelocityCard": {
        "category": "visualization",
        "modalities": ["visual"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 1,
        "stealth_assessment": False,
        "tags": ["dashboard", "metrics", "motivation", "velocity"],
        "concept_types": ["any"],
        "abstraction": "abstract",
    },
    "ProgressMap": {
        "category": "visualization",
        "modalities": ["visual"],
        "difficulties": ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 1,
        "stealth_assessment": False,
        "tags": ["navigation", "progress", "path", "mastery"],
        "concept_types": ["any"],
        "abstraction": "abstract",
    },
    # ── Collaborative Learning ───────────────────────────────────────────────────
    "PeerTutoringCard": {
        "category": "collaborative",
        "modalities": ["text", "auditory"],
        "difficulties": ["DEVELOPING", "EXPANDING", "MASTERING"],
        "estimated_minutes": 10,
        "stealth_assessment": False,
        "tags": ["peer", "social", "tutoring", "collaboration"],
        "concept_types": ["any"],
        "abstraction": "any",
    },
    "DiscussionForum": {
        "category": "collaborative",
        "modalities": ["text"],
        "difficulties": ["EXPANDING", "MASTERING"],
        "estimated_minutes": 8,
        "stealth_assessment": False,
        "tags": ["discussion", "social", "debate", "synthesis"],
        "concept_types": ["any"],
        "abstraction": "abstract",
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
    student_id: Optional[str] = None,
) -> list[ComponentRecommendation]:
    """
    Select the best components for the given learner context.

    Uses ML-based collaborative filtering when student_id is provided and
    sufficient training data exists. Falls back to heuristic scoring otherwise.

    Heuristic scoring factors:
    - Modality alignment (0.25 weight)
    - Difficulty fit (0.15 weight)
    - Time fit (0.10 weight)
    - Assessment need (0.20 weight)
    - Tag relevance (0.15 weight)
    - Recency penalty (0.10 weight — avoid repeating recently used)
    - Struggle boost (0.05 weight — favor scaffolding if struggling)
    """
    exclude_categories = exclude_categories or []

    # Try ML selector if student_id is provided
    if student_id:
        try:
            from app.algorithms.ml_component_selector import get_ml_selector

            ml_selector = get_ml_selector()
            available_components = list(COMPONENT_REGISTRY.keys())

            ml_results = ml_selector.select_components(
                student_id=student_id,
                learner_context=context,
                available_components=available_components,
                max_results=max_results,
                exclude_categories=exclude_categories,
            )

            if ml_results:
                logger.info(
                    f"[COMPONENT_SELECTOR] ML selector returned {[r.component_id for r in ml_results]} "
                    f"for student {student_id}"
                )
                return ml_results
        except Exception as e:
            logger.warning(f"[COMPONENT_SELECTOR] ML selector failed, falling back to heuristic: {e}")

    # Heuristic fallback
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
        f"[COMPONENT_SELECTOR] Heuristic selected {[r.component_id for r in results]} "
        f"for context: mastery={context.mastery_score}, difficulty={context.difficulty}, "
        f"modalities={context.preferred_modalities}"
    )

    return results


# ── Track → concept_type mapping ─────────────────────────────────────────────

_TRACK_CONCEPT_TYPE: dict[str, str] = {
    "CREATION_SCIENCE":     "science",
    "HEALTH_NATUROPATHY":   "science",
    "HOMESTEADING":         "science",
    "GOVERNMENT_ECONOMICS": "any",
    "JUSTICE_CHANGEMAKING": "any",
    "DISCIPLESHIP":         "any",
    "TRUTH_HISTORY":        "history",
    "ENGLISH_LITERATURE":   "writing",
    "APPLIED_MATHEMATICS":  "math",
    "CREATIVE_ECONOMY":     "any",
}

# Modality → preferred supplement component, by concept type.
# auditory is already served by the animated sketchnote / narrated slide cascade.
_MODAL_SUPPLEMENT_MAP: dict[str, dict[str, Optional[str]]] = {
    "kinesthetic": {
        "math":    "VirtualManipulative",
        "science": "LabGuide",
        "history": "TaskScaffold",
        "writing": "TaskScaffold",
        "any":     "TaskScaffold",
    },
    "visual": {
        "math":    "AutoDiagram",
        "science": "AutoDiagram",
        "history": "AutoDiagram",
        "writing": "AutoDiagram",
        "any":     "AutoDiagram",
    },
    "text": {
        "math":    "ScaffoldedProblem",
        "science": "LabGuide",
        "history": "HardThingChallenge",
        "writing": "GlowGrow",
        "any":     "GlowGrow",
    },
    "reading": {
        "math":    "ScaffoldedProblem",
        "science": "LabGuide",
        "history": "HardThingChallenge",
        "writing": "GlowGrow",
        "any":     "GlowGrow",
    },
    "auditory": {
        "any":     "AudioDialogue",
        "science": "AudioDialogue",
        "math":    "AudioDialogue",
        "history": "AudioDialogue",
        "writing": "AudioDialogue",
    },
}

# Components already injected by the cascade or track-specific synthesizers —
# skip these when choosing a modal supplement to avoid duplication.
_CASCADE_COMPONENTS: set[str] = {
    "SocraticDebate",
    "NarratedSlides",
    "MindMap",
    "DragDropTimeline",
    "InteractiveConceptMap",
    "MoleculeSimulator",
    "CodePlayground",
    "ProjectBuilder",
}


def select_modal_supplement(
    preferred_modality: str,
    difficulty: str,
    track: str,
    already_emitted: Optional[list[str]] = None,
) -> Optional[str]:
    """
    Pick the best supplement component matched to the student's preferred modality.

    Called by orchestrator._inject_modal_supplement after the main render cascade.
    Returns a component_type string or None if no supplement is appropriate.

    Args:
        preferred_modality: "visual" | "auditory" | "kinesthetic" | "text" | "reading"
        difficulty:         "EMERGING" | "DEVELOPING" | "EXPANDING" | "MASTERING"
        track:              Track value string (e.g. "APPLIED_MATHEMATICS")
        already_emitted:    Component types already present in this lesson
    """
    concept_type = _TRACK_CONCEPT_TYPE.get(track, "any")
    modality_map = _MODAL_SUPPLEMENT_MAP.get(preferred_modality, {})
    component = modality_map.get(concept_type) or modality_map.get("any")

    if not component:
        return None

    skip = set(already_emitted or []) | _CASCADE_COMPONENTS
    if component in skip:
        # Fall back: run the scored selector, excluding already-present components
        context = LearnerContext(
            difficulty=difficulty,
            preferred_modalities=[preferred_modality],
            topic_tags=[concept_type],
        )
        fallback = select_components(
            context,
            max_results=1,
            exclude_categories=["visualization"],
        )
        if fallback:
            candidate = fallback[0].component_id
            if candidate not in skip:
                return candidate
        return None

    return component


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
