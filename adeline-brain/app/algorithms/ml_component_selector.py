"""
ML Component Selector — Collaborative filtering + feature-based ranking.

Replaces heuristic scoring in component_selector.py with a data-driven model
that learns from student interactions logged in ComponentInteractionLog.

Model combines:
1. Collaborative filtering: students with similar interaction patterns
2. Content-based filtering: component features (modality, difficulty, category)
3. Contextual features: student's current mastery, recent struggle, ZPD zone

When insufficient training data exists, falls back to heuristic scoring.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


# ── Component Feature Vectors (from component_selector.py registry) ─────────

@dataclass
class ComponentFeatures:
    """Feature vector for a component, extracted from COMPONENT_REGISTRY."""
    component_id: str
    category: str  # "multimodal", "assessment", "scaffolding", "visualization"
    modalities: List[str]  # ["visual", "auditory", "kinesthetic", "text", "reading"]
    difficulties: List[str]  # ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"]
    estimated_minutes: int
    stealth_assessment: bool
    tags: List[str]
    concept_types: List[str]
    abstraction: str  # "concrete" or "abstract"


# ── Student Interaction History ───────────────────────────────────────────────

@dataclass
class StudentInteraction:
    """A single component interaction from ComponentInteractionLog."""
    component_id: str
    component_type: str
    interaction_type: str  # "viewed", "completed", "struggled", "skipped", "scaffold_triggered"
    student_modality: Optional[str]
    component_modalities: List[str]
    difficulty: str
    duration_secs: Optional[float]
    completed: bool
    struggle_count: int
    hints_used: int
    mastery_before: Optional[float]
    mastery_after: Optional[float]
    timestamp: float


# ── ML Model: Collaborative Filtering + Content-Based ──────────────────────

class MLComponentSelector:
    """
    ML-based component selector using collaborative filtering + content features.

    Scoring formula:
      score = w1 * collaborative_score + w2 * content_score + w3 * context_score

    Where:
      - collaborative_score: similarity to successful interactions from similar students
      - content_score: modality match, difficulty alignment, category relevance
      - context_score: ZPD alignment, recent struggle compensation
    """

    def __init__(
        self,
        collaborative_weight: float = 0.4,
        content_weight: float = 0.4,
        context_weight: float = 0.2,
        min_interactions_for_cf: int = 5,
    ):
        self.collaborative_weight = collaborative_weight
        self.content_weight = content_weight
        self.context_weight = context_weight
        self.min_interactions_for_cf = min_interactions_for_cf

        # In-memory caches (in production, these would be in Redis)
        self._component_features: Dict[str, ComponentFeatures] = {}
        self._student_interactions: Dict[str, List[StudentInteraction]] = defaultdict(list)

    def register_component_features(self, features: ComponentFeatures) -> None:
        """Register component features from COMPONENT_REGISTRY."""
        self._component_features[features.component_id] = features

    def log_interaction(self, student_id: str, interaction: StudentInteraction) -> None:
        """Log a student interaction for future model training."""
        self._student_interactions[student_id].append(interaction)

    def select_components(
        self,
        student_id: str,
        learner_context: "LearnerContext",
        available_components: List[str],
        max_results: int = 5,
        exclude_categories: Optional[List[str]] = None,
    ) -> List["ComponentRecommendation"]:
        """
        Select and rank components using ML scoring.

        Args:
            student_id: Student identifier
            learner_context: Current learner state (mastery, modality, struggle)
            available_components: List of component IDs to consider
            max_results: Number of recommendations to return
            exclude_categories: Component categories to exclude

        Returns:
            List of ComponentRecommendation sorted by score (descending)
        """
        from app.algorithms.component_selector import ComponentRecommendation, LearnerContext

        # Filter out excluded categories
        exclude = set(exclude_categories or [])
        candidates = [
            cid for cid in available_components
            if self._component_features.get(cid)?.category not in exclude
        ]

        if not candidates:
            return []

        # Get student's interaction history
        student_history = self._student_interactions.get(student_id, [])

        # If insufficient data, fall back to heuristic scoring
        if len(student_history) < self.min_interactions_for_cf:
            logger.info(
                f"[ML_SELECTOR] Insufficient data for student {student_id} "
                f"({len(student_history)} interactions), falling back to heuristic"
            )
            return self._heuristic_fallback(
                learner_context,
                candidates,
                max_results,
            )

        # Compute scores for each candidate
        scored: List[Tuple[str, float, str]] = []
        for component_id in candidates:
            features = self._component_features.get(component_id)
            if not features:
                continue

            collab_score = self._collaborative_score(
                student_id,
                component_id,
                features,
                student_history,
            )
            content_score = self._content_score(
                features,
                learner_context,
            )
            context_score = self._context_score(
                features,
                learner_context,
            )

            # Weighted combination
            total_score = (
                self.collaborative_weight * collab_score +
                self.content_weight * content_score +
                self.context_weight * context_score
            )

            reason = self._build_reason(
                collab_score,
                content_score,
                context_score,
                features,
            )
            scored.append((component_id, total_score, reason))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Convert to ComponentRecommendation objects
        recommendations = [
            ComponentRecommendation(
                component_id=cid,
                score=score,
                reason=reason,
            )
            for cid, score, reason in scored[:max_results]
        ]

        logger.info(
            f"[ML_SELECTOR] Selected {len(recommendations)} components for student {student_id}"
        )
        return recommendations

    def _collaborative_score(
        self,
        student_id: str,
        component_id: str,
        features: ComponentFeatures,
        student_history: List[StudentInteraction],
    ) -> float:
        """
        Collaborative filtering score based on similar students' success.

        Finds students with similar interaction patterns and checks how they
        performed with this component or similar components.
        """
        # Build student profile: preferred modalities, successful components
        student_profile = self._build_student_profile(student_history)

        # Find similar students (Jaccard similarity on interaction sets)
        similar_students = self._find_similar_students(
            student_id,
            student_profile,
        )

        if not similar_students:
            return 0.5  # Neutral score when no similar students

        # Aggregate success rate of similar students with this component
        total_interactions = 0
        successful_interactions = 0

        for similar_id, similarity in similar_students[:10]:  # Top 10 similar
            for interaction in self._student_interactions.get(similar_id, []):
                if interaction.component_id == component_id:
                    total_interactions += 1
                    if interaction.completed and interaction.struggle_count == 0:
                        successful_interactions += 1

        if total_interactions == 0:
            # No direct data, use similarity-weighted baseline
            return 0.5 + 0.1 * sum(s for _, s in similar_students[:5])

        success_rate = successful_interactions / total_interactions
        return success_rate

    def _content_score(
        self,
        features: ComponentFeatures,
        context: "LearnerContext",
    ) -> float:
        """
        Content-based score: modality match, difficulty alignment, category relevance.
        """
        score = 0.0

        # Modality match (0.0–0.4)
        if context.preferred_modalities:
            match_count = sum(
                1 for m in context.preferred_modalities
                if m in features.modalities
            )
            score += 0.4 * (match_count / max(len(features.modalities), 1))

        # Difficulty alignment (0.0–0.3)
        if context.difficulty in features.difficulties:
            score += 0.3
        elif self._difficulty_adjacent(context.difficulty, features.difficulties):
            score += 0.15

        # Category relevance (0.0–0.2)
        # Prefer assessment when needs_assessment, scaffolding when struggling
        if context.needs_assessment and features.category == "assessment":
            score += 0.2
        elif context.recent_struggle_count >= 2 and features.category == "scaffolding":
            score += 0.2
        elif features.category == "multimodal":
            score += 0.1

        # Stealth assessment preference (0.0–0.1)
        if context.needs_assessment and features.stealth_assessment:
            score += 0.1

        return min(score, 1.0)

    def _context_score(
        self,
        features: ComponentFeatures,
        context: "LearnerContext",
    ) -> float:
        """
        Contextual score: ZPD alignment, concept type match, recent struggle.
        """
        score = 0.0

        # Concept type match (0.0–0.4)
        if context.topic_tags:
            match_count = sum(
                1 for tag in context.topic_tags
                if tag in features.concept_types or tag in features.tags
            )
            score += 0.4 * (match_count / max(len(context.topic_tags), 1))

        # Abstraction match (0.0–0.3)
        # Concrete for emerging/developing, abstract for expanding/mastering
        if context.difficulty in ["EMERGING", "DEVELOPING"]:
            if features.abstraction == "concrete":
                score += 0.3
        else:
            if features.abstraction == "abstract":
                score += 0.3

        # Struggle compensation (0.0–0.3)
        if context.recent_struggle_count >= 3:
            # Prefer scaffolding and simpler components
            if features.category == "scaffolding":
                score += 0.3
            elif "EMERGING" in features.difficulties:
                score += 0.15

        return min(score, 1.0)

    def _build_student_profile(
        self,
        history: List[StudentInteraction],
    ) -> Dict[str, any]:
        """Build a profile from student's interaction history."""
        completed_components = set()
        preferred_modalities = defaultdict(int)
        successful_difficulties = defaultdict(int)

        for interaction in history:
            if interaction.completed:
                completed_components.add(interaction.component_id)
                if interaction.student_modality:
                    preferred_modalities[interaction.student_modality] += 1
                successful_difficulties[interaction.difficulty] += 1

        return {
            "completed_components": completed_components,
            "preferred_modalities": dict(preferred_modalities),
            "successful_difficulties": dict(successful_difficulties),
        }

    def _find_similar_students(
        self,
        student_id: str,
        profile: Dict[str, any],
    ) -> List[Tuple[str, float]]:
        """
        Find students with similar interaction profiles using Jaccard similarity.
        Returns list of (student_id, similarity) sorted by similarity descending.
        """
        similarities = []

        for other_id, other_history in self._student_interactions.items():
            if other_id == student_id:
                continue

            other_profile = self._build_student_profile(other_history)

            # Jaccard similarity on completed components
            set1 = profile["completed_components"]
            set2 = other_profile["completed_components"]
            if not set1 or not set2:
                continue

            intersection = len(set1 & set2)
            union = len(set1 | set2)
            jaccard = intersection / union if union > 0 else 0.0

            # Boost similarity if preferred modalities match
            modality_match = 0.0
            for mod, count in profile["preferred_modalities"].items():
                if mod in other_profile["preferred_modalities"]:
                    modality_match += min(count, other_profile["preferred_modalities"][mod])

            combined_score = 0.7 * jaccard + 0.3 * (modality_match / (sum(profile["preferred_modalities"].values()) or 1))

            if combined_score > 0.1:
                similarities.append((other_id, combined_score))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities

    def _difficulty_adjacent(
        self,
        current: str,
        difficulties: List[str],
    ) -> bool:
        """Check if current difficulty is adjacent to any in the list."""
        order = ["EMERGING", "DEVELOPING", "EXPANDING", "MASTERING"]
        try:
            idx = order.index(current)
        except ValueError:
            return False

        for diff in difficulties:
            try:
                other_idx = order.index(diff)
                if abs(other_idx - idx) == 1:
                    return True
            except ValueError:
                continue
        return False

    def _build_reason(
        self,
        collab_score: float,
        content_score: float,
        context_score: float,
        features: ComponentFeatures,
    ) -> str:
        """Build human-readable reason for the recommendation."""
        reasons = []

        if collab_score > 0.7:
            reasons.append("similar students succeeded")
        elif collab_score > 0.5:
            reasons.append("peer-validated")

        if content_score > 0.6:
            reasons.append(f"matches {features.modalities[0] if features.modalities else 'your'} modality")
        if context_score > 0.6:
            reasons.append("aligned with your current level")

        if not reasons:
            reasons.append("balanced fit")

        return ", ".join(reasons)

    def _heuristic_fallback(
        self,
        context: "LearnerContext",
        candidates: List[str],
        max_results: int,
    ) -> List["ComponentRecommendation"]:
        """Fallback to heuristic scoring when insufficient ML data."""
        from app.algorithms.component_selector import ComponentRecommendation, select_components

        # Use the existing heuristic selector
        results = select_components(
            context,
            max_results=max_results,
            exclude_categories=[],
        )

        # Filter to only candidates in our available list
        filtered = [
            r for r in results
            if r.component_id in candidates
        ]

        return filtered[:max_results]


# ── Global ML Selector Instance ─────────────────────────────────────────────

_ml_selector: Optional[MLComponentSelector] = None


def get_ml_selector() -> MLComponentSelector:
    """Get or create the global ML selector instance."""
    global _ml_selector
    if _ml_selector is None:
        _ml_selector = MLComponentSelector()
        # Initialize with component features from registry
        from app.algorithms.component_selector import COMPONENT_REGISTRY
        for component_id, config in COMPONENT_REGISTRY.items():
            features = ComponentFeatures(
                component_id=component_id,
                category=config["category"],
                modalities=config["modalities"],
                difficulties=config["difficulties"],
                estimated_minutes=config["estimated_minutes"],
                stealth_assessment=config["stealth_assessment"],
                tags=config["tags"],
                concept_types=config["concept_types"],
                abstraction=config["abstraction"],
            )
            _ml_selector.register_component_features(features)
    return _ml_selector
