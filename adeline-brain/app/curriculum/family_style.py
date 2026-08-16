"""The one canonical lesson format shared by every learner-facing surface."""

from copy import deepcopy
import re

CANONICAL_FORMAT_VERSION = 3

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
)

FAMILY_CANONICAL_AUTHORING_RULES = """
FAMILY-STYLE CANONICAL RULES (non-negotiable):
- Author the durable lesson at full adult/high-school depth. Do not lower or remove
  verified facts because the requesting learner is younger.
- Build one shared intellectual experience for the household: one story, inquiry,
  demonstration, discussion, or real project that learners can do together.
- Give learners different responsibility, not different disconnected lessons:
  upper-elementary learners notice, name, sequence, measure, draw, or narrate;
  middle-school learners explain mechanisms, compare evidence, and make connections;
  high-school learners evaluate sources, handle nuance, calculate, design, or lead synthesis.
- The shared work must culminate in something real: a model, map, experiment, record,
  performance, plan, service, or useful creation. No worksheets or decorative busywork.
- Each learner must be able to preserve an individual contribution as portfolio evidence.
- Keep facts, sources, central questions, and worldview fixed across ages. Adapt only
  vocabulary, scaffolding, independence, and depth of responsibility.
""".strip()


def family_workshop_block(topic: str) -> dict:
    """Return the stable one-room-schoolhouse spine stored with every canonical."""
    safe_topic = topic.strip() or "this topic"
    return {
        "block_type": "NARRATIVE",
        "content": (
            f"## Do this together: {safe_topic}\n\n"
            "Begin with one shared question: **What is happening, how do we know, and what can we "
            "make or do with what we learn?** Read the lesson, inspect its sources, and try its "
            "demonstration or example together.\n\n"
            "**Grades 4–5:** notice and name details; sequence, measure, sketch, label, narrate, or "
            "build one concrete part.\n\n"
            "**Grades 6–8:** explain the mechanism or cause and effect; compare evidence, record "
            "results, and connect the idea to real life.\n\n"
            "**Grades 9–12:** evaluate claims and sources; handle nuance, design the method, calculate "
            "where useful, or lead the final synthesis.\n\n"
            "**Finish with something real.** Make the form fit the topic: a model, map, experiment "
            "record, performance, plan, service, or useful creation. Each learner preserves one "
            "clearly identified contribution—a photo, page, recording, explanation, or reflection—"
            "for the portfolio."
        ),
        "evidence": [],
        "is_silenced": False,
        "homestead_content": None,
        "_enrichment": True,
        "family_style": True,
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
        "family_roles": {
            "upper_elementary": "notice, name, sequence, measure, sketch, narrate, or build",
            "middle_school": "explain, compare evidence, record results, and connect ideas",
            "high_school": "evaluate sources, handle nuance, design, calculate, and lead synthesis",
        },
        "portfolio_evidence": "Each learner preserves an identifiable contribution to the shared work.",
    }


def ensure_family_workshop(blocks: list[dict], topic: str) -> list[dict]:
    """Add exactly one family workshop without mutating the caller's list."""
    if any(block.get("family_style") for block in blocks):
        return list(blocks)
    return [*blocks, family_workshop_block(topic)]


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


def finalize_family_lesson(blocks: list[dict], topic: str) -> list[dict]:
    """Normalize specialist output once without rebuilding it into another format.

    Specialists own the lesson's facts, sources, and real work. This function is
    the only structural finalizer: it removes obsolete formats/placeholders,
    rejects malformed widgets, deduplicates content, and adds one family workshop.
    It never calls an LLM and never converts one block type into another.
    """
    finalized: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for original in blocks:
        block = deepcopy(original)
        block_type = str(block.get("block_type") or "NARRATIVE").strip().upper()
        if block_type in _OBSOLETE_FORMATS or block.get("is_silenced"):
            continue
        if not _usable_content(block) or not _valid_interactive(block):
            continue

        # TEXT is a transport-era alias. Learners see one coherent narrative type.
        if block_type == "TEXT":
            block_type = "NARRATIVE"
        block["block_type"] = block_type
        block["content"] = re.sub(r"\n{3,}", "\n\n", str(block["content"]).strip())

        fingerprint = (block_type, re.sub(r"\s+", " ", block["content"]).lower())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        finalized.append(block)

    # Never disguise a failed specialist response as a lesson by returning only
    # the generic workshop. The caller can surface a real generation failure.
    return ensure_family_workshop(finalized, topic) if finalized else []


def is_current_family_canonical(blocks: list[dict]) -> bool:
    """Only reuse lessons authored and saved by the current family format."""
    return any(
        block.get("family_style")
        and block.get("canonical_format_version") == CANONICAL_FORMAT_VERSION
        for block in blocks
    )
