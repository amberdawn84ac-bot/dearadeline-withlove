"""adeline-brain/app/algorithms — Learning science algorithms for Adeline 2.0."""
from .zpd_engine import (
    BKTParams, AdaptiveBKTParams,
    bkt_update, adaptive_bkt_update, apply_decay,
    compute_priority, blend_mastery, quality_to_mastery_delta,
    compute_zpd_from_snapshots, format_zpd_for_prompt,
    ZPDConcept, MasterySnapshot,
    MASTERY_THRESHOLD, PREREQ_READINESS,
)
from .spaced_repetition import (
    SM2Result, sm2,
    quality_to_mastery_delta as sm2_quality_to_delta,
    is_due, overdue_days, format_due_reviews_for_prompt,
)
from .adaptive_content import (
    get_grade_band, get_difficulty_for_grade, get_attention_span_minutes,
    get_track_vocabulary, build_lesson_prompt_context, GradeBand,
)
from .cognitive_load import (
    Baseline, CognitiveLoadResult, compute_baseline,
    calculate_cognitive_load, should_simplify_content, get_pacing_recommendation,
)
from .pedagogical_directives import (
    PedagogicalState, analyze_pedagogical_state,
    generate_pedagogical_directives, get_quick_directives,
)

__all__ = [
    "BKTParams", "AdaptiveBKTParams", "bkt_update", "adaptive_bkt_update",
    "apply_decay", "compute_priority", "blend_mastery", "quality_to_mastery_delta",
    "compute_zpd_from_snapshots", "format_zpd_for_prompt",
    "ZPDConcept", "MasterySnapshot", "MASTERY_THRESHOLD", "PREREQ_READINESS",
    "SM2Result", "sm2", "sm2_quality_to_delta", "is_due", "overdue_days",
    "format_due_reviews_for_prompt",
    "get_grade_band", "get_difficulty_for_grade", "get_attention_span_minutes",
    "get_track_vocabulary", "build_lesson_prompt_context", "GradeBand",
    "Baseline", "CognitiveLoadResult", "compute_baseline",
    "calculate_cognitive_load", "should_simplify_content", "get_pacing_recommendation",
    "PedagogicalState", "analyze_pedagogical_state",
    "generate_pedagogical_directives", "get_quick_directives",
]
