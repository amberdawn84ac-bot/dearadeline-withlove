"""Canonical family-style lesson rules and structural validation.

Family style is the lesson itself, not an extra narrative block appended after
specialist generation. The same canonical experience is later adapted by grade
and mastery and rendered for digital or printable surfaces.
"""

from copy import deepcopy
import re
from typing import Any

from app.curriculum.experience_contract import ExperienceStage, annotate_experience, validate_experience

CANONICAL_FORMAT_VERSION = 7

_OBSOLETE_FORMATS = {
    "ANIMATED_SKETCHNOTE_LESSON",
    "NARRATED_SLIDE",
}
_PLACEHOLDER_PHRASES = (
    "adeline is preparing",
    "check back shortly",
    "check back soon",
    "no content provided",
    "[genui hint",
    "lesson is being prepared",
    "come back later",
)
_MAX_CANONICAL_BLOCKS = 12
_MIN_CANONICAL_BLOCKS = 3
_SUBSTANTIVE_BLOCK_TYPES = frozenset({
    "PRIMARY_SOURCE",
    "LAB_MISSION",
    "EXPERIMENT",
    "RESEARCH_MISSION",
    "REAL_WORLD_APP",
    "SIMULATION",
    "TIMELINE",
    "MIND_MAP",
    "CONCEPT_MAP",
    "GENUI_ASSEMBLY",
    "DISCUSSION_FORUM",
    "QUIZ",
})
_TRACKS_EXPECTING_SUBSTANTIVE_BLOCKS = frozenset({
    "TRUTH_HISTORY",
    "JUSTICE_CHANGEMAKING",
    "CREATION_SCIENCE",
    "HOMESTEADING",
    "ENGLISH_LITERATURE",
    "APPLIED_MATHEMATICS",
    "CREATIVE_ECONOMY",
})

FAMILY_CANONICAL_AUTHORING_RULES = """
CANONICAL EXPERIENCE AUTHOR — NON-NEGOTIABLE:
- Author ONE coherent experience, not a stack of explanatory cards, a worksheet, a slideshow,
  a chapter, or a decorated chat answer.
- Begin with a consequential question, mystery, problem, creation, or decision that gives the
  learner a real reason to continue. Do not announce standards or academic bookkeeping.
- Use only the teaching needed to act intelligently. Put facts, sources, demonstrations, and
  explanations beside the moment in which the learner needs them.
- The learner must DO something intellectually or physically meaningful: examine evidence,
  manipulate a system, investigate, experiment, play a real rules-based game, build, design,
  interview, calculate, perform, write for an audience, or solve a consequential problem.
- The finish must produce reviewable evidence. Name the artifact, observation, explanation,
  performance, decision trail, or scored interaction that could demonstrate each target concept.
- Completion, exposure, elapsed time, and button clicks are never mastery. Proposed credit remains
  a draft until the evidence is evaluated.
- A shared family experience keeps one central question and shared outcome. Give each learner an
  age-, mastery-, and prerequisite-appropriate contribution; siblings do not receive cloned work.
- The canonical is full-depth and durable. Adaptation may change vocabulary, scaffolding,
  independence, examples, and responsibility, but never facts, sources, central question, or goal.
- Outside resources are routed as tools, evidence, games, simulations, objects, texts, or practice.
  Record item-level rights and use mode. They enrich the experience; they do not become the teacher.
- Use NARRATIVE only when story itself is the learning medium. Never use narrative as filler,
  status, directions, a default explanation box, or a substitute for an experience.
- Use semantic visuals only when they materially improve understanding. The renderer owns layout.
- Use only as many substantive parts as the experience needs; never pad to hit a count.
- Never invent facts, quotations, sources, measurements, standards, results, or certainty.
- Never include CSS, screen layout, internal agent language, or renderer instructions in learner prose.
""".strip()


def _usable_content(block: dict) -> bool:
    content = str(block.get("content") or "").strip()
    if not content:
        return False
    lowered = content.lower()
    return not any(phrase in lowered for phrase in _PLACEHOLDER_PHRASES)


def _valid_interactive(block: dict) -> bool:
    if block.get("block_type") != "GENUI_ASSEMBLY":
        return True
    data = block.get("genui_assembly_data")
    return (
        isinstance(data, dict)
        and isinstance(data.get("component_type"), str)
        and bool(data["component_type"].strip())
        and isinstance(data.get("props"), dict)
    )


def _family_role_metadata(block: dict) -> dict:
    roles = block.get("family_roles")
    if isinstance(roles, dict):
        return roles
    return {
        "elementary": "notice, identify, sequence, measure, sketch, label, narrate, or build",
        "middle": "explain, compare evidence, connect cause and effect, record results, or apply",
        "high_school": "evaluate sources, handle nuance, calculate where useful, design, or lead synthesis",
    }


def validate_canonical_lesson(
    blocks: list[dict],
    *,
    track: str | None = None,
) -> list[str]:
    """Return structural canonical-lesson violations without inventing content."""
    errors: list[str] = []
    count = len(blocks)
    if count < _MIN_CANONICAL_BLOCKS:
        errors.append(f"canonical lesson requires at least {_MIN_CANONICAL_BLOCKS} substantive blocks; got {count}")
    if count > _MAX_CANONICAL_BLOCKS:
        errors.append(f"canonical lesson may contain at most {_MAX_CANONICAL_BLOCKS} blocks; got {count}")

    if track in _TRACKS_EXPECTING_SUBSTANTIVE_BLOCKS:
        if not any(str(block.get("block_type", "")).upper() in _SUBSTANTIVE_BLOCK_TYPES for block in blocks):
            errors.append(f"track {track} requires at least one evidence/action-oriented block")

    for index, block in enumerate(blocks):
        if str(block.get("experience_stage") or "").upper() not in ExperienceStage._value2member_map_:
            errors.append(f"block {index} must directly declare a valid experience_stage")
        if str(block.get("block_type") or "").upper() == "NARRATIVE":
            content = str(block.get("content") or "").lower()
            if any(phrase in content for phrase in ("family workshop:", "do this together:", "coming soon", "check back")):
                errors.append(f"block {index} is a generic family/status narrative and is not allowed")

    errors.extend(validate_experience(blocks))

    return errors


def finalize_family_lesson(blocks: list[dict], topic: str, *, track: str | None = None) -> list[dict]:
    """Normalize specialist output without rebuilding it into another format.

    Specialists own the actual lesson. This finalizer only removes obsolete or
    unusable blocks, deduplicates identical content, preserves block types, marks
    the result as the current family canonical format, and enforces the 6–10
    canonical block ceiling. It never calls an LLM and never appends a synthetic
    narrative block.
    """
    finalized: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for original in blocks:
        block = deepcopy(original)
        block_type = str(block.get("block_type") or "").strip().upper()
        if not block_type:
            continue
        if block_type in _OBSOLETE_FORMATS or block.get("is_silenced"):
            continue
        if not _usable_content(block) or not _valid_interactive(block):
            continue

        # Preserve the semantic block type. Do not silently relabel TEXT as NARRATIVE.
        block["block_type"] = block_type
        block["content"] = re.sub(r"\n{3,}", "\n\n", str(block["content"]).strip())
        block["family_style"] = True
        block["canonical_format_version"] = CANONICAL_FORMAT_VERSION
        block["family_roles"] = _family_role_metadata(block)

        fingerprint = (block_type, re.sub(r"\s+", " ", block["content"]).lower())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        finalized.append(block)

    # New specialists/authors must state instructional purpose directly. Stage
    # inference remains available only when reading archived legacy material;
    # it is not allowed to make new output appear contract-complete.
    finalized = finalized[:_MAX_CANONICAL_BLOCKS]

    errors = validate_canonical_lesson(finalized, track=track)
    if errors:
        # A short/structurally invalid lesson must fail closed rather than being
        # disguised as a generic narrative lesson.
        return []

    return annotate_experience(finalized)


def is_current_family_canonical(blocks: list[dict]) -> bool:
    """Only reuse lessons authored and saved by the current family format."""
    return bool(blocks) and all(
        block.get("family_style")
        and block.get("canonical_format_version") == CANONICAL_FORMAT_VERSION
        and not block.get("deprecated")
        for block in blocks
    )


def canonical_metadata(topic: str, track: str, adaptation_contract: list[str]) -> dict[str, Any]:
    """Create the small renderer/adaptor metadata envelope for a canonical lesson."""
    contract = [str(rule).strip() for rule in adaptation_contract if str(rule).strip()][:5]
    return {
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
        "topic": topic,
        "track": track,
        "adaptation_contract": contract,
    }
