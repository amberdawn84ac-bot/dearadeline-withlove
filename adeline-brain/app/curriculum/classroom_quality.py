"""Checks for new authoring. Older saved classrooms retain their original contract."""

import re

from app.curriculum.classroom import Blueprint, Scene


def normalized(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def validate_teaching_plan(blueprint: Blueprint, capabilities: dict) -> None:
    if blueprint.teaching_design is None:
        raise ValueError("Give the lesson an explicit teaching design.")
    mechanisms = {item["id"] for item in capabilities["mechanisms"]}
    for brief in blueprint.scenes:
        if not brief.evidence or not brief.evidence.strip():
            raise ValueError(
                f"{brief.id}: name the actual learner work that will show progress."
            )
        if brief.type == "interactive" and brief.mechanism not in mechanisms:
            raise ValueError(f"{brief.id}: select one installed activity mechanism.")
        if brief.type != "interactive" and brief.mechanism is not None:
            raise ValueError(f"{brief.id}: only interactive scenes use a mechanism.")
    purposes = [brief.purpose for brief in blueprint.scenes]
    initial, final = (
        purposes.index("independent_attempt"),
        purposes.index("independent_check"),
    )
    instruction = blueprint.scenes[initial + 1 : final]
    if not any(brief.purpose == "explain" for brief in instruction):
        raise ValueError(
            "Explain the core idea after the initial attempt and before the final check."
        )
    if not any(brief.purpose in {"practice", "apply"} for brief in instruction):
        raise ValueError(
            "Give learners a chance to use the idea before checking it independently."
        )
    if blueprint.teaching_design.approach == "workshop" and not any(
        brief.type in {"interactive", "pbl"} and brief.purpose in {"practice", "apply"}
        for brief in instruction
    ):
        raise ValueError(
            "A workshop needs an interactive investigation or a hands-on project before the check."
        )


def validate_teaching_scene(
    scene: Scene, brief: dict, previous: list[dict], sources: list[dict]
) -> None:
    roles = {normalized(value) for value in scene.family_roles.values()}
    if len(roles) != 3 or "" in roles:
        raise ValueError(
            "Give each age band genuinely different work with a specific output."
        )
    body, task = normalized(scene.content), normalized(scene.learner_task)
    if not body or not task or body == task:
        raise ValueError(
            "Give specific teaching or context and a separate, actionable task."
        )
    source_ids = {source["id"] for source in sources}
    cited = {use.source_id for use in scene.source_uses}
    approved_images = {
        source["image_url"]
        for source in sources
        if source["id"] in cited and source.get("image_url")
    }
    elements = scene.visual.elements if scene.visual else []
    if any(element.type == "image" and element.url not in approved_images for element in elements):
        raise ValueError(
            "Use the exact image_url of a supplied, cited image. Otherwise replace it with a native visual or a worked example."
        )
    if brief["purpose"] == "explain":
        example = normalized(scene.worked_example or "")
        visual_teaches = any(
            element.type in {"image", "chart", "table", "layer_stack"}
            for element in elements
        )
        if not visual_teaches and (not example or example in body or example == task):
            raise ValueError(
                "Teach the idea with a visual explanation or a distinct, worked-through example."
            )
    if (
        brief["purpose"] in {"practice", "apply"}
        and scene.type == "pbl"
        and len({normalized(step) for step in scene.steps} - {""}) < 2
    ):
        raise ValueError(
            "Provide at least two distinct steps for doing and checking the work."
        )
    if scene.portfolio_title and brief["purpose"] != "apply":
        raise ValueError(
            "A portfolio title belongs to an application project with an actual deliverable."
        )
    if scene.type == "interactive" and brief.get("mechanism"):
        mechanism = (
            scene.interaction.kind
            if scene.interaction
            else scene.simulation.model
            if scene.simulation
            else "sorting"
        )
        if mechanism != brief["mechanism"]:
            raise ValueError(f"Use the planned mechanism {brief['mechanism']!r}.")
    if brief["purpose"] in {"independent_attempt", "independent_check"}:
        prompt = normalized(scene.question.prompt) if scene.question else task
        for prior in previous:
            question = prior.get("question")
            prior_prompt = (
                normalized(question["prompt"])
                if question
                else normalized(prior["learner_task"])
            )
            if prompt == prior_prompt:
                raise ValueError(
                    "Give a fresh independent task using a different example."
                )
    if any(body == normalized(prior["content"]) for prior in previous):
        raise ValueError("Write a new explanation or scenario for this scene; do not repeat an earlier page.")
    used = [use.source_id for use in scene.source_uses]
    if set(used) - source_ids or len(set(used)) != len(used):
        raise ValueError(
            "Reference each supplied source by its exact ID, at most once per scene."
        )
