"""Bounded teacher-side review of the complete generated classroom.

A model opinion is never proof of factual accuracy. Structural checks happen
separately in the classroom authoring contract. Only reviewed classrooms publish.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.curriculum.classroom import Blueprint, Classroom


class QualityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_id: str
    scene_id: str
    verdict: Literal["pass", "revise"]
    observation: str = Field(min_length=15, max_length=650)
    revision: str | None = Field(default=None, max_length=700)

    @model_validator(mode="after")
    def actionable(self):
        if self.verdict == "revise" and not (self.revision and self.revision.strip()):
            raise ValueError("Failed criteria require a concrete revision instruction.")
        return self


class QualityReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[QualityFinding] = Field(min_length=2, max_length=5)


POLICY = """Critically review this COMPLETE Dear Adeline class against its
own precommitted class_quality_rubric. You are an independent teaching reviewer,
not the lesson's author. Assess every criterion once, citing a real scene ID,
a specific observable strength or defect, and an actionable revision if deficient.
Flag generic exposition, unsupported scientific or historical claims, missing
concept explanations, false promises of visual or practical interactions, empty
activities, inaccessible steps, answer leakage, inadequate age differentiation,
and failures to teach before asking for an independent final check.
If a source is not supplied, do NOT pretend it verifies the fact; flag unsupported
assertions that need verification. Never invent source access or student work.
Rubric descriptions are fixed: never revise them to pass the class.
Output only JSON. This judgment is a draft quality review, not scientific
verification or evidence of actual student learning."""


def checked_review(review: QualityReview, blueprint: Blueprint) -> dict[str, list[str]]:
    rubric = blueprint.class_quality_rubric
    if rubric is None:
        raise ValueError("A new classroom needs its precommitted quality rubric.")
    expected = {criterion.id for criterion in rubric.criteria}
    actual = [finding.criterion_id for finding in review.findings]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Review must address every class-quality criterion exactly once.")
    scene_ids = {scene.id for scene in blueprint.scenes}
    repairs = {}
    for finding in review.findings:
        if finding.scene_id not in scene_ids:
            raise ValueError("Quality review must refer to a real scene.")
        if finding.verdict == "revise":
            repairs.setdefault(finding.scene_id, []).append(
                f"{finding.criterion_id}: {finding.observation} "
                f"Revision: {finding.revision}"
            )
    return repairs


async def review_and_repair(
    blueprint: Blueprint,
    scenes: list,
    *,
    generate,
    make_scene_context,
    on_repair,
    max_passes: int = 2,
):
    """Review, revise named scenes, then re-review; fail closed on remaining gaps.

    Repaired scenes are saved through on_repair before a second review. On a
    provider outage the caller can resume with its saved, still unpublished scenes.
    """
    from app.curriculum.classroom import Scene, SCENE_POLICY

    if blueprint.class_quality_rubric is None:
        return scenes, None  # Old saved classroom only.
    for attempt in range(max_passes):
        classroom = Classroom(blueprint=blueprint, scenes=scenes)
        review = await generate(
            POLICY, QualityReview,
            {
                "class_quality_rubric": blueprint.class_quality_rubric.model_dump(),
                "understanding": blueprint.understanding,
                "essential_question": blueprint.essential_question,
                "scene_briefs": [brief.model_dump() for brief in blueprint.scenes],
                "scenes": [scene.model_dump() for scene in classroom.scenes],
                "instructions": "Assess teaching, not imagined student performance.",
            },
        )
        try:
            repairs = checked_review(review, blueprint)
        except ValueError as exc:
            raise ValueError("The quality review returned invalid evidence.") from exc
        if not repairs:
            return scenes, review.model_dump()
        if attempt == max_passes - 1:
            raise ValueError("Classroom quality review still found instructional gaps.")
        for i, brief in enumerate(blueprint.scenes):
            if brief.id not in repairs:
                continue
            context = make_scene_context(
                brief, scenes[:i], "\n".join(repairs[brief.id])
            )
            replacement = await generate(
                SCENE_POLICY
                + "\nREPAIR INSTRUCTIONS: Revise this scene to address the "
                  "specific reviewer observations. Preserve its id, type, "
                  "planned mechanism, and factual accuracy. Do not reveal keys.",
                Scene,
                context,
            )
            scenes[i] = replacement
            await on_repair(scenes)
    raise ValueError("Classroom review did not complete.")
