"""Canonical family-style lesson rules and structural validation.

Family style is the lesson itself, not an extra narrative block appended after
specialist generation. The same canonical experience is later adapted by grade
and mastery and rendered for digital or printable surfaces.
"""

from copy import deepcopy
import re
from typing import Any

CANONICAL_FORMAT_VERSION = 5

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
_MAX_CANONICAL_BLOCKS = 10
_MIN_CANONICAL_BLOCKS = 6
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
CANONICAL LESSON AUTHOR — FAMILY-STYLE, NON-NEGOTIABLE:
- Author ONE rich shared family learning experience at full adult/high-school depth.
- This canonical lesson is the durable source of truth; a separate adapter changes grade,
  mastery, scaffolding, vocabulary, independence, and depth of responsibility only.
- Do not write a generic lesson, article, or explanatory narrative and do not append a generic
  family-workshop paragraph. Family style is the structure of the actual learning experience.
- Prefer concrete evidence and meaningful tasks over explanatory prose.
- Keep the central question, learning goal, verified facts, evidence, worldview lens, shared work,
  and real-world outcome fixed across ages.
- Give elementary, middle, and high-school learners different responsibility in the SAME shared work:
  notice/label/build; explain/compare/apply; evaluate/design/calculate/lead.
- Every substantive lesson should produce something real when the subject supports it: an experiment,
  model, map, record, source dossier, performance, plan, service, written argument, useful creation,
  or other authentic deliverable.
- Include a concrete individual contribution that can be preserved as portfolio evidence.
- Use NARRATIVE only when narrative itself is the best instructional medium. Never use it as a fallback,
  placeholder, family-instructions block, filler, or status message.
- Use semantic visuals only when they improve understanding. The renderer decides page layout and UI.
- Keep the canonical lesson to 6–10 substantive blocks. Never pad the lesson to reach the count.
- When the track supports evidence, experimentation, investigation, or real-world application, include at
  least one appropriate substantive block such as PRIMARY_SOURCE, LAB_MISSION, EXPERIMENT, REAL_WORLD_APP,
  or another evidence/action block. Do not force an inappropriate activity.
- The adaptation contract must stay short: 3–5 rules describing only what grade/mastery may change.
- Never invent quotations, source identities, dates, measurements, research findings, or evidence.
- Never print frontend behavior, CSS, page coordinates, rendering instructions, or internal metadata in prose.
- The learner-facing renderer follows the Kitchen Chemistry pattern: a compelling family question,
  three age/mastery responsibility layers, preparation and safety where relevant, real teaching,
  a shared investigation, explicit concepts, an interactive mastery finish, reflection, and portfolio evidence.
- Outside resources never replace the lesson. A rights-aware Resource Router may add a separate live
  evidence/simulation/game/creation section after adaptation; live results are never saved into the canonical.
""".strip()


def family_workshop_block(topic: str) -> dict:
    """Deprecated compatibility helper; family style is no longer a synthetic block.

    Kept so old imports do not break. New canonical generation must NOT append
    this block to lessons.
    """
    safe_topic = topic.strip() or "this topic"
    return {
        "block_type": "NARRATIVE",
        "content": f"## Family learning: {safe_topic}",
        "evidence": [],
        "is_silenced": False,
        "family_style": True,
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
        "deprecated": True,
    }


def ensure_family_workshop(blocks: list[dict], topic: str) -> list[dict]:
    """Compatibility no-op: family style is authored by the canonical lesson itself."""
    return list(blocks)


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
        if str(block.get("block_type") or "").upper() == "NARRATIVE":
            content = str(block.get("content") or "").lower()
            if any(phrase in content for phrase in ("family workshop:", "do this together:", "coming soon", "check back")):
                errors.append(f"block {index} is a generic family/status narrative and is not allowed")

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

    # Enforce the ceiling without inventing or rewriting content.
    finalized = finalized[:_MAX_CANONICAL_BLOCKS]

    errors = validate_canonical_lesson(finalized, track=track)
    if errors:
        # A short/structurally invalid lesson must fail closed rather than being
        # disguised as a generic narrative lesson.
        return []

    return finalized


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
