"""
ML Sequencer — adaptive component sequencing engine for the Manager Agent.

Integrates five ML algorithms into a single blended decision:
  1. Learner Profiler    (Decision Tree)   → classify learner archetype
  2. Content-Based Filter (rule-based CF)  → modality + difficulty matching
  3. Collaborative Filter (cosine CF)      → what worked for similar peers
  4. RL Optimizer        (Q-learning)      → long-horizon policy optimization
  5. Learning Velocity   (forgetting curve)→ pacing + SM-2 review scheduling

Blending weights: RL 40 % | Collaborative 25 % | Content-Based 25 % | Velocity 10 %

Pure computation — no DB/Redis calls.
Caller (ManagerAgent) is responsible for fetching input data and persisting
the updated Q-table back to Redis after each lesson.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.algorithms.learner_profiler import (
    InteractionRecord,
    LearnerProfile,
    LearnerProfileType,
    extract_features,
    classify_learner_profile,
)
from app.algorithms.collaborative_filter import (
    PeerProfile,
    build_mastery_vector,
    recommend_from_peers,
)
from app.algorithms.rl_optimizer import (
    encode_state,
    select_action,
    compute_reward,
    q_update,
)
from app.algorithms.learning_velocity import (
    MasteryCheckpoint,
    PacingRecommendation,
    VelocityStatus,
    get_pacing_recommendation,
)
from app.algorithms.component_selector import (
    LearnerContext,
    select_components,
    COMPONENT_REGISTRY,
)

logger = logging.getLogger(__name__)

# ── Signal blending weights ────────────────────────────────────────────────────
_W_RL           = 0.40
_W_COLLAB       = 0.25
_W_CONTENT      = 0.25
_W_VELOCITY     = 0.10

# Profile affinity bonus on top of blended score
_PROFILE_BONUS  = 0.05


@dataclass
class SequencerInput:
    """
    All data the sequencer needs.
    Caller (ManagerAgent) fetches each field from DB / Redis before calling.
    Empty lists / dicts cause graceful fallback — never raise.
    """
    student_id: str
    track: str
    grade_band: str                              # "k2" | "35" | "68" | "912"

    # Real-time state (Cognitive Twin)
    zpd_zone: str = "IN_ZPD"
    mastery_score: float = 0.5
    cognitive_load_level: str = "MEDIUM"
    consecutive_struggles: int = 0

    # Learner profiling history
    interaction_history: list[InteractionRecord] = field(default_factory=list)
    recently_used_components: list[str] = field(default_factory=list)

    # Collaborative filter data
    mastery_map: dict[str, float] = field(default_factory=dict)
    peer_profiles: list[PeerProfile] = field(default_factory=list)

    # RL state (loaded from Redis by caller)
    q_table: dict = field(default_factory=dict)

    # SM-2 + velocity inputs
    sm2_cards: list[dict] = field(default_factory=list)
    mastery_checkpoints: list[MasteryCheckpoint] = field(default_factory=list)

    # Request context
    needs_assessment: bool = False
    topic_tags: list[str] = field(default_factory=list)
    time_available_minutes: int = 20


@dataclass
class SequencerDecision:
    """Output from the ML sequencer — tells the Manager Agent what to render next."""
    component_id: str
    confidence: float

    # Explainability
    reasons: list[str]

    # Rich state for downstream use
    profile: LearnerProfile
    pacing: PacingRecommendation

    # RL artifacts for post-lesson update
    rl_state: tuple
    updated_q_table: dict     # Caller persists this to Redis after lesson feedback

    # Ranked alternatives for fallback
    alternatives: list[str] = field(default_factory=list)


def sequence_next_component(inp: SequencerInput) -> SequencerDecision:
    """
    Run all five ML algorithms and blend their outputs into a single decision.
    Never raises — any algorithm failure causes that signal to contribute 0.
    """

    # ── 1. Learner Profile (Decision Tree) ────────────────────────────────────
    features = extract_features(inp.interaction_history, inp.consecutive_struggles)
    profile  = classify_learner_profile(features)

    logger.info(
        "[MLSequencer] student=%s profile=%s (%.2f) track=%s zpd=%s load=%s",
        inp.student_id, profile.profile_type.value, profile.confidence,
        inp.track, inp.zpd_zone, inp.cognitive_load_level,
    )

    # ── 2. Learning Velocity + Forgetting Curve ───────────────────────────────
    pacing = get_pacing_recommendation(
        checkpoints=inp.mastery_checkpoints,
        grade_band=inp.grade_band,
        sm2_cards=inp.sm2_cards,
    )

    # ── 3. Content-Based Filter ───────────────────────────────────────────────
    time_budget = max(5, int(inp.time_available_minutes * pacing.pacing_factor))
    cb_context = LearnerContext(
        mastery_score=inp.mastery_score,
        difficulty=_mastery_to_difficulty(inp.mastery_score),
        preferred_modalities=_profile_to_modalities(profile.profile_type),
        recent_struggle_count=inp.consecutive_struggles,
        time_available_minutes=time_budget,
        needs_assessment=inp.needs_assessment,
        topic_tags=inp.topic_tags,
        recently_used_components=inp.recently_used_components,
    )
    cb_recs   = select_components(cb_context, max_results=5)
    cb_scores = {r.component_id: r.score for r in cb_recs}

    # ── 4. Collaborative Filter ───────────────────────────────────────────────
    student_vector = build_mastery_vector(inp.mastery_map)
    collab_recs    = recommend_from_peers(
        student_mastery_vector=student_vector,
        peers=inp.peer_profiles,
        top_k_peers=10,
        top_n_components=5,
    )
    collab_scores = {r.component_id: r.score for r in collab_recs}

    # ── 5. RL Optimizer (Q-learning) ─────────────────────────────────────────
    rl_state = encode_state(
        zpd_zone=inp.zpd_zone,
        mastery_score=inp.mastery_score,
        cognitive_load_level=inp.cognitive_load_level,
        learner_profile_type=profile.profile_type.value,
    )

    available = _filter_candidates(inp, pacing)
    rl_action = select_action(inp.q_table, rl_state, available)

    # ── 6. Blend signals ─────────────────────────────────────────────────────
    candidate_set: set[str] = set(available)
    candidate_set.update(profile.preferred_components)
    for cat in pacing.suggested_block_categories:
        candidate_set.update(
            cid for cid, meta in COMPONENT_REGISTRY.items()
            if meta["category"] == cat
        )

    blended: dict[str, float] = {}
    for comp_id in candidate_set:
        # RL: award full weight to the epsilon-greedy winner; partial to rest
        rl_q      = inp.q_table.get((rl_state, comp_id), 0.0)
        rl_norm   = 1.0 if comp_id == rl_action else max(0.0, (rl_q + 10.0) / 20.0)
        score     = _W_RL * rl_norm

        # Collaborative
        score += _W_COLLAB * collab_scores.get(comp_id, 0.0)

        # Content-based
        score += _W_CONTENT * cb_scores.get(comp_id, 0.0)

        # Velocity category boost
        comp_cat  = COMPONENT_REGISTRY.get(comp_id, {}).get("category", "")
        vel_boost = 1.0 if comp_cat in pacing.suggested_block_categories else 0.5
        score += _W_VELOCITY * vel_boost

        # Profile affinity bonus
        if comp_id in profile.preferred_components:
            score += _PROFILE_BONUS

        blended[comp_id] = round(max(0.0, min(1.0, score)), 4)

    ranked = sorted(blended.items(), key=lambda x: x[1], reverse=True)

    if ranked:
        selected, confidence = ranked[0]
        alternatives = [cid for cid, _ in ranked[1:4]]
    else:
        selected, confidence, alternatives = "TextExplanation", 0.30, []

    reasons = _build_reasons(
        selected, profile, collab_scores, collab_recs, rl_action, cb_scores
    )

    logger.info(
        "[MLSequencer] decision=%s conf=%.3f pacing=%s reasons=%s",
        selected, confidence, pacing.status.value, reasons,
    )

    return SequencerDecision(
        component_id=selected,
        confidence=confidence,
        reasons=reasons,
        profile=profile,
        pacing=pacing,
        rl_state=rl_state,
        updated_q_table=dict(inp.q_table),  # Post-lesson update happens via apply_lesson_feedback()
        alternatives=alternatives,
    )


def apply_lesson_feedback(
    q_table: dict,
    rl_state: tuple,
    component_used: str,
    mastery_delta: float,
    engagement_delta: float,
    frustration_delta: float,
    next_zpd_zone: str,
    next_mastery_score: float,
    next_cognitive_load: str,
    next_profile_type: str,
    lesson_completed: bool = True,
    struggled: bool = False,
) -> dict:
    """
    Apply the Bellman Q-update after a lesson completes.

    Call this from the learning_records API route once outcome signals
    (mastery_delta, engagement_delta, frustration_delta) are known,
    then persist the returned Q-table to Redis under key `q_table:{student_id}`.
    """
    reward = compute_reward(
        mastery_delta=mastery_delta,
        engagement_delta=engagement_delta,
        frustration_delta=frustration_delta,
        lesson_completed=lesson_completed,
        struggled=struggled,
    )

    next_state = encode_state(
        zpd_zone=next_zpd_zone,
        mastery_score=next_mastery_score,
        cognitive_load_level=next_cognitive_load,
        learner_profile_type=next_profile_type,
    )

    available_next = list(COMPONENT_REGISTRY.keys())

    updated = q_update(
        q_table=q_table,
        state=rl_state,
        action=component_used,
        reward=reward,
        next_state=next_state,
        available_next_actions=available_next,
    )

    logger.debug(
        "[MLSequencer] Q-update state=%s action=%s reward=%.3f new_Q=%.4f",
        rl_state, component_used, reward,
        updated.get((rl_state, component_used), 0.0),
    )
    return updated


# ── Internal helpers ───────────────────────────────────────────────────────────

def _filter_candidates(inp: SequencerInput, pacing: PacingRecommendation) -> list[str]:
    """
    Restrict available components based on pacing and ZPD zone.
    Always returns at least 3 options to keep selection meaningful.
    """
    all_comps = list(COMPONENT_REGISTRY.keys())

    if pacing.status == VelocityStatus.STALLED:
        restricted = [c for c in all_comps if COMPONENT_REGISTRY[c]["category"] in ("feedback", "multimodal")]
    elif inp.zpd_zone == "BORED":
        restricted = [c for c in all_comps if COMPONENT_REGISTRY[c]["category"] != "feedback"]
    else:
        restricted = all_comps

    # Avoid exact repeat of last 2 components when list is large enough
    if inp.recently_used_components and len(restricted) > 3:
        pruned = [c for c in restricted if c not in inp.recently_used_components[-2:]]
        if pruned:
            restricted = pruned

    return restricted if restricted else all_comps


def _mastery_to_difficulty(mastery: float) -> str:
    if mastery < 0.30:
        return "SEEDLING"
    if mastery < 0.70:
        return "GROWING"
    return "HARVEST"


def _profile_to_modalities(profile_type: LearnerProfileType) -> list[str]:
    return {
        LearnerProfileType.EXPLORER:     ["visual", "kinesthetic"],
        LearnerProfileType.BUILDER:      ["kinesthetic", "visual"],
        LearnerProfileType.PRACTITIONER: ["reading", "kinesthetic"],
        LearnerProfileType.REFLECTOR:    ["reading", "auditory"],
    }[profile_type]


def _build_reasons(
    selected: str,
    profile: LearnerProfile,
    collab_scores: dict,
    collab_recs: list,
    rl_action: str,
    cb_scores: dict,
) -> list[str]:
    reasons: list[str] = []
    if selected in profile.preferred_components:
        reasons.append(f"matches {profile.profile_type.value} learner profile")
    if selected in collab_scores and collab_scores[selected] > 0.60:
        n_peers = next((r.contributing_peers for r in collab_recs if r.component_id == selected), 0)
        if n_peers > 0:
            reasons.append(f"high success rate across {n_peers} similar peers")
    if selected == rl_action:
        reasons.append("Q-learning optimal action for current state")
    if selected in cb_scores and cb_scores[selected] > 0.50:
        reasons.append("strong content-based fit (modality + difficulty)")
    if not reasons:
        reasons.append("highest blended ML score")
    return reasons
