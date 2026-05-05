"""Unified Pedagogical Directives Generator.

Combines ZPD Engine + Cognitive Load Manager into a single injectable prompt block.
This is the "brain" that tells Adeline how to teach based on the student's current state.

Usage:
    from app.algorithms.pedagogical_directives import generate_pedagogical_directives
    
    directives = generate_pedagogical_directives(
        student_message="I don't understand this at all",
        mastery_score=0.45,
        cognitive_load=CognitiveLoadResult(score=0.7, level="HIGH"),
        zpd_zone=ZPDZone.FRUSTRATED,
        mastery_band=MasteryBand.DEVELOPING,
    )
    
    # Inject into system prompt
    full_prompt = base_prompt + directives
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.algorithms.cognitive_load import CognitiveLoadResult, get_pacing_recommendation
from app.agents.pedagogy import ZPDZone, detect_zpd_zone
from app.models.student import MasteryBand

logger = logging.getLogger(__name__)


# ── Scaffolding Instructions by ZPD Zone ─────────────────────────────────────

_ZPD_INSTRUCTIONS = {
    ZPDZone.FRUSTRATED: (
        "SCAFFOLDING LEVEL: HIGH (Student is struggling)\n"
        "- Break the concept into the smallest possible steps.\n"
        "- Connect to something they already know (use their Witness Anchors).\n"
        "- Ask ONE simple, guiding question to help them find the first step.\n"
        "- Do NOT give the answer directly — provide heavy hints instead.\n"
        "- Validate their effort: 'This is a tricky part. Let's slow down together.'"
    ),
    ZPDZone.IN_ZPD: (
        "SCAFFOLDING LEVEL: MEDIUM (Student is engaged and working)\n"
        "- Provide a conceptual hint or an analogy.\n"
        "- Ask a probing question to guide them toward the answer.\n"
        "- Encourage them to connect this to something they already know.\n"
        "- Affirm their effort without praising the answer: 'Good thinking — let's go deeper.'"
    ),
    ZPDZone.BORED: (
        "SCAFFOLDING LEVEL: LOW (Student is ready to advance)\n"
        "- The student is mastering this concept. Challenge them!\n"
        "- Ask them to explain *why* their answer works.\n"
        "- Introduce a slight twist or advanced application of the concept.\n"
        "- Surface a harder primary source or a contradiction to analyze."
    ),
}


# ── Cognitive Load Instructions ──────────────────────────────────────────────

_COGNITIVE_LOAD_INSTRUCTIONS = {
    "CRITICAL": (
        "COGNITIVE LOAD: CRITICAL (Student is overwhelmed)\n"
        "- The student is severely overwhelmed. Validate their frustration empathetically.\n"
        "- Use VERY simple vocabulary and EXTREMELY short sentences (max 10 words).\n"
        "- Focus on ONLY ONE idea right now. Ignore everything else.\n"
        "- Pause new material entirely. Consolidate what they already know.\n"
        "- Example: 'Let's pause. Take a breath. What's ONE thing you remember?'"
    ),
    "HIGH": (
        "COGNITIVE LOAD: HIGH (Student shows strain)\n"
        "- The student shows signs of strain. Simplify your vocabulary.\n"
        "- Use shorter sentences (max 15 words). Reduce complexity.\n"
        "- Check for understanding before introducing anything new.\n"
        "- Example: 'Before we go on — can you tell me what we just learned?'"
    ),
    "MEDIUM": (
        "COGNITIVE LOAD: MEDIUM (Moderate effort)\n"
        "- Moderate load. Maintain current pacing.\n"
        "- Check for understanding periodically.\n"
        "- Safe to continue with current complexity level."
    ),
    "LOW": (
        "COGNITIVE LOAD: LOW (Student is engaged)\n"
        "- Low cognitive load. Student is engaged and comfortable.\n"
        "- Safe to advance complexity or introduce new concepts.\n"
        "- Maintain a warm, natural, and conversational tone."
    ),
}


# ── Mastery Band Vocabulary Guidelines ───────────────────────────────────────

_MASTERY_VOCABULARY = {
    MasteryBand.NOVICE: (
        "VOCABULARY LEVEL: NOVICE\n"
        "- Use simple, everyday language. Avoid jargon entirely.\n"
        "- Define every new term with a concrete example.\n"
        "- Connect concepts to everyday life experiences."
    ),
    MasteryBand.DEVELOPING: (
        "VOCABULARY LEVEL: DEVELOPING\n"
        "- Use correct terminology but define it on first use.\n"
        "- Provide analogies to bridge new concepts.\n"
        "- Build on vocabulary from previous lessons."
    ),
    MasteryBand.PROFICIENT: (
        "VOCABULARY LEVEL: PROFICIENT\n"
        "- Use subject-appropriate vocabulary freely.\n"
        "- Introduce primary source excerpts with context.\n"
        "- Encourage precise language in student responses."
    ),
    MasteryBand.ADVANCED: (
        "VOCABULARY LEVEL: ADVANCED\n"
        "- Use full academic register.\n"
        "- Engage with historiography, scientific debate, or theological nuance.\n"
        "- Challenge the student to defend positions with evidence."
    ),
}


@dataclass
class PedagogicalState:
    """Snapshot of the student's current pedagogical state."""
    zpd_zone: ZPDZone
    cognitive_load_level: str
    mastery_band: MasteryBand
    mastery_score: float
    should_simplify: bool
    pacing_recommendation: str


def analyze_pedagogical_state(
    student_message: str,
    mastery_score: float,
    mastery_band: MasteryBand,
    cognitive_load: Optional[CognitiveLoadResult] = None,
) -> PedagogicalState:
    """
    Analyze the student's current state from their message and metrics.
    
    Args:
        student_message: The student's most recent message
        mastery_score: Current mastery score (0.0 to 1.0)
        mastery_band: Current mastery band (NOVICE/DEVELOPING/PROFICIENT/ADVANCED)
        cognitive_load: Optional pre-computed cognitive load result
    
    Returns:
        PedagogicalState with all relevant teaching adjustments
    """
    # Detect ZPD zone from message
    zpd_zone = detect_zpd_zone(student_message)
    
    # Use provided cognitive load or default to MEDIUM
    if cognitive_load:
        load_level = cognitive_load.level
        should_simplify = load_level in ("HIGH", "CRITICAL")
        pacing = get_pacing_recommendation(cognitive_load)
    else:
        # Infer from ZPD zone if no cognitive load data
        if zpd_zone == ZPDZone.FRUSTRATED:
            load_level = "HIGH"
            should_simplify = True
            pacing = "Student appears to be struggling. Simplify and slow down."
        else:
            load_level = "MEDIUM"
            should_simplify = False
            pacing = "Maintain current pacing."
    
    return PedagogicalState(
        zpd_zone=zpd_zone,
        cognitive_load_level=load_level,
        mastery_band=mastery_band,
        mastery_score=mastery_score,
        should_simplify=should_simplify,
        pacing_recommendation=pacing,
    )


def generate_pedagogical_directives(
    student_message: str,
    mastery_score: float,
    mastery_band: MasteryBand,
    cognitive_load: Optional[CognitiveLoadResult] = None,
    zpd_zone: Optional[ZPDZone] = None,
    include_vocabulary_guide: bool = True,
) -> str:
    """
    Generate unified pedagogical directives for injection into Adeline's system prompt.
    
    This function combines:
    - ZPD Engine (scaffolding level based on student struggle/mastery)
    - Cognitive Load Manager (simplification based on overwhelm signals)
    - Mastery Band (vocabulary complexity guidelines)
    
    Args:
        student_message: The student's most recent message
        mastery_score: Current mastery score (0.0 to 1.0)
        mastery_band: Current mastery band
        cognitive_load: Optional pre-computed cognitive load result
        zpd_zone: Optional pre-computed ZPD zone (will detect from message if not provided)
        include_vocabulary_guide: Whether to include vocabulary level instructions
    
    Returns:
        Formatted directive block to inject into system prompt
    """
    logger.info(f"[Pedagogy] Generating directives | mastery={mastery_score:.2f} | band={mastery_band.value}")
    
    # Detect or use provided ZPD zone
    if zpd_zone is None:
        zpd_zone = detect_zpd_zone(student_message)
    
    # Get cognitive load level
    if cognitive_load:
        load_level = cognitive_load.level
    else:
        # Infer from ZPD zone
        load_level = "HIGH" if zpd_zone == ZPDZone.FRUSTRATED else "MEDIUM"
    
    # Build directive sections
    zpd_instructions = _ZPD_INSTRUCTIONS.get(zpd_zone, _ZPD_INSTRUCTIONS[ZPDZone.IN_ZPD])
    load_instructions = _COGNITIVE_LOAD_INSTRUCTIONS.get(load_level, _COGNITIVE_LOAD_INSTRUCTIONS["MEDIUM"])
    
    directives = (
        "\n╔══════════════════════════════════════════════════════════════╗\n"
        "║           PEDAGOGICAL DIRECTIVES (MANDATORY)                 ║\n"
        "╚══════════════════════════════════════════════════════════════╝\n"
        "You MUST adjust your teaching style based on the following rules:\n\n"
        f"{zpd_instructions}\n\n"
        f"{load_instructions}\n"
    )
    
    if include_vocabulary_guide:
        vocab_instructions = _MASTERY_VOCABULARY.get(mastery_band, _MASTERY_VOCABULARY[MasteryBand.DEVELOPING])
        directives += f"\n{vocab_instructions}\n"
    
    directives += (
        "\n────────────────────────────────────────────────────────────────\n"
        f"Current State: ZPD={zpd_zone.value} | Load={load_level} | "
        f"Mastery={mastery_score*100:.0f}% ({mastery_band.value})\n"
        "────────────────────────────────────────────────────────────────\n"
    )
    
    logger.info(f"[Pedagogy] Directives generated | zpd={zpd_zone.value} | load={load_level}")
    
    return directives


def get_quick_directives(zpd_zone: ZPDZone, mastery_band: MasteryBand) -> str:
    """
    Get a minimal directive string for quick injection.
    Useful for chat responses where full directives would be too verbose.
    """
    scaffolding = {
        ZPDZone.FRUSTRATED: "HIGH scaffolding: break it down, heavy hints, validate struggle",
        ZPDZone.IN_ZPD: "MEDIUM scaffolding: probing questions, build connections",
        ZPDZone.BORED: "LOW scaffolding: challenge them, introduce twists",
    }[zpd_zone]
    
    vocab = {
        MasteryBand.NOVICE: "simple language, define everything",
        MasteryBand.DEVELOPING: "clear terms, provide analogies",
        MasteryBand.PROFICIENT: "subject vocabulary, primary sources",
        MasteryBand.ADVANCED: "academic register, debate-ready",
    }[mastery_band]
    
    return f"[Pedagogy: {scaffolding} | Vocab: {vocab}]"


# ── Track → Conversation Mode Mapping ────────────────────────────────────────
# Used by the streaming conversation endpoint to shape Adeline's teaching voice.

TRACK_TO_MODE: dict[str, str] = {
    "TRUTH_HISTORY":        "INVESTIGATOR",
    "JUSTICE_CHANGEMAKING": "INVESTIGATOR",
    "CREATION_SCIENCE":     "LAB",
    "HOMESTEADING":         "LAB",
    "HEALTH_NATUROPATHY":   "DIALOGUE",
    "GOVERNMENT_ECONOMICS": "INVESTIGATOR",
    "DISCIPLESHIP":         "DIALOGUE",
    "ENGLISH_LITERATURE":   "DIALOGUE",
    "APPLIED_MATHEMATICS":  "LAB",
    "CREATIVE_ECONOMY":     "WORKSHOP",
}

_MODE_DIRECTIVES: dict[str, str] = {
    "INVESTIGATOR": (
        "INVESTIGATOR MODE:\n"
        "- Lead with a question or a discrepancy — never an explanation.\n"
        "- When you have a relevant primary source, surface it with a <BLOCK> tag mid-sentence.\n"
        "- Never summarize what the archive says. Show the raw material and ask what the student notices.\n"
        "- 'Follow the money' and 'Who wrote this, and why?' are always valid questions.\n"
    ),
    "LAB": (
        "LAB MODE:\n"
        "- Frame everything as a prediction before revealing anything.\n"
        "- Ask: 'What would you expect to happen?' before showing results.\n"
        "- Surface LabGuide or ExperimentCard blocks when the student is ready to try something.\n"
        "- Connect every concept back to something testable on the homestead.\n"
    ),
    "DIALOGUE": (
        "DIALOGUE MODE:\n"
        "- Reason together, out loud. Ask 'what do you think?' before telling them what you think.\n"
        "- Pull in scripture when genuinely relevant — Fox translation, never decorative.\n"
        "- Read carefully. Name what you see honestly. Speak into it with precision and courage.\n"
        "- Surface SocraticDebate blocks when the student is ready to defend a position.\n"
    ),
    "WORKSHOP": (
        "WORKSHOP MODE:\n"
        "- Connect everything to making, pricing, and selling real things.\n"
        "- 'What would you make with this?' and 'What would you charge?' are always valid.\n"
        "- Surface ProjectBuilder blocks when the student has enough context to build something.\n"
        "- Math lives in the workshop: materials, margins, market pricing.\n"
    ),
}


def get_mode_directives(tracks: list[str]) -> str:
    """
    Return blended mode directives for the given active tracks.
    Multiple tracks may map to the same mode — deduplication is handled automatically.
    """
    modes = {TRACK_TO_MODE[t] for t in tracks if t in TRACK_TO_MODE}
    if not modes:
        return ""
    return "\n\n".join(_MODE_DIRECTIVES[mode] for mode in sorted(modes))
