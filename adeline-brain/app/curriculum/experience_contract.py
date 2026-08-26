"""Semantic contract shared by every Dear Adeline learning experience.

Block types describe a rendering tool. Experience stages describe why that tool
exists. Keeping those separate prevents a renderer from turning an assortment of
text blocks into something that merely looks like a lesson.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any


class ExperienceStage(StrEnum):
    INVITATION = "INVITATION"
    DISCOVERY = "DISCOVERY"
    ACTION = "ACTION"
    CREATION = "CREATION"
    DEMONSTRATION = "DEMONSTRATION"
    REFLECTION = "REFLECTION"
    RESOURCE = "RESOURCE"


ACTION_TYPES = frozenset({
    "LAB_MISSION", "EXPERIMENT", "REAL_WORLD_APP", "SIMULATION",
    "RESEARCH_MISSION", "DISCUSSION_FORUM", "GENUI_ASSEMBLY", "PROBLEM",
})
CREATION_TYPES = frozenset({"PROJECT_BUILDER", "TIMELINE", "MIND_MAP", "CONCEPT_MAP", "GENUI_ASSEMBLY"})
DEMONSTRATION_TYPES = frozenset({"QUIZ", "FLASHCARD", "SCAFFOLDED_PROBLEM", "GENUI_ASSEMBLY"})
DISCOVERY_TYPES = frozenset({"PRIMARY_SOURCE", "DATA_EXPLORER", "COMPARISON", "TEXT", "NARRATIVE"})
# GENUI_ASSEMBLY is a dynamic-component wrapper (component_type/props chosen at
# authoring time) capable of representing an action, a creation, or a
# demonstration depending on what it wraps — deliberately in all three sets
# rather than forced into one, unlike every other type here.


def infer_stage(block: dict[str, Any], index: int, total: int) -> ExperienceStage:
    """Infer purpose for legacy specialist output without changing its content."""
    explicit = str(block.get("experience_stage") or "").upper()
    if explicit in ExperienceStage._value2member_map_:
        return ExperienceStage(explicit)
    block_type = str(block.get("block_type") or "").upper()
    if block_type == "RESOURCE_COLLECTION":
        return ExperienceStage.RESOURCE
    if block_type in DEMONSTRATION_TYPES:
        return ExperienceStage.DEMONSTRATION
    if block_type in CREATION_TYPES:
        return ExperienceStage.CREATION
    if block_type in ACTION_TYPES:
        return ExperienceStage.ACTION
    if index == 0:
        return ExperienceStage.INVITATION
    if index == total - 1:
        return ExperienceStage.REFLECTION
    return ExperienceStage.DISCOVERY


def annotate_experience(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach renderer-independent purpose and evidence requirements."""
    total = len(blocks)
    for index, block in enumerate(blocks):
        stage = infer_stage(block, index, total)
        block["experience_stage"] = stage.value
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        metadata["requires_evidence"] = stage in {
            ExperienceStage.ACTION,
            ExperienceStage.CREATION,
            ExperienceStage.DEMONSTRATION,
        }
        block["metadata"] = metadata
    return blocks


_STAGE_REQUIRES_CAPABLE_TYPE = {
    ExperienceStage.ACTION: ACTION_TYPES,
    ExperienceStage.CREATION: CREATION_TYPES,
    ExperienceStage.DEMONSTRATION: DEMONSTRATION_TYPES,
}


def validate_experience(blocks: list[dict[str, Any]]) -> list[str]:
    """Enforce experience shape without prescribing a visual template.

    A block may only satisfy ACTION/CREATION/DEMONSTRATION by actually being
    a type capable of that stage — an explicit experience_stage label alone
    is not enough. Without this, a plain TEXT block could self-label
    "experience_stage": "ACTION" and satisfy the requirement below without
    the learner ever encountering a genuine action-capable component.
    """
    stages = {infer_stage(block, index, len(blocks)) for index, block in enumerate(blocks)}
    errors: list[str] = []
    if ExperienceStage.INVITATION not in stages:
        errors.append("experience requires a meaningful invitation or central question")
    if not stages.intersection({ExperienceStage.ACTION, ExperienceStage.CREATION}):
        errors.append("experience requires meaningful learner action or creation")
    if ExperienceStage.DEMONSTRATION not in stages:
        errors.append("experience requires a reviewable demonstration of understanding")

    for index, block in enumerate(blocks):
        stage = infer_stage(block, index, len(blocks))
        capable_types = _STAGE_REQUIRES_CAPABLE_TYPE.get(stage)
        if capable_types is None:
            continue
        block_type = str(block.get("block_type") or "").upper()
        if block_type not in capable_types:
            errors.append(
                f"block {index} declares experience_stage={stage.value} but "
                f"block_type={block_type or '(missing)'} cannot satisfy that stage — "
                f"a label alone does not make it {stage.value.lower()}"
            )

    return errors
