"""Versioned teaching context; declared grades are not evidence of mastery."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Grade = Literal["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]


class LearnerContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["learner-context-v1"] = "learner-context-v1"
    mode: Literal["individual", "family", "unspecified"] = "unspecified"
    declared_grades: list[Grade] = Field(default_factory=list, max_length=10)
    working_grade: Grade | None = None
    supports: list[Literal["reading_support", "extra_time", "keyboard_input", "screen_reader"]] = Field(default_factory=list, max_length=4)
    language: str = Field(default="en", pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", max_length=35)
    minutes: int | None = Field(default=None, ge=5, le=240)

    @model_validator(mode="after")
    def coherent(self):
        if self.mode == "individual" and len(self.declared_grades) > 1:
            raise ValueError("An individual context has at most one declared grade")
        if self.mode == "family" and self.working_grade is not None:
            raise ValueError("A family cannot have one shared working grade")
        if len(self.declared_grades) != len(set(self.declared_grades)):
            raise ValueError("Use distinct family grade levels, not learner identities")
        if len(self.supports) != len(set(self.supports)):
            raise ValueError("Support preferences must be distinct")
        return self

    def resource_grade(self) -> str | None:
        if self.working_grade is not None:
            return self.working_grade
        if not self.declared_grades:
            return None
        return min(self.declared_grades, key=lambda grade: 0 if grade == "K" else int(grade))

    def authoring_context(self) -> dict:
        return {
            **self.model_dump(mode="json"),
            "resource_grade": self.resource_grade(),
            "resource_grade_basis": (
                "Individual working grade" if self.working_grade else
                "Youngest declared grade is a shared entry point, not the family's working level"
                if self.mode == "family" and self.declared_grades else
                "Declared grade only; assess actual readiness" if self.declared_grades else
                "Unknown; do not infer grade from age or assume readiness"
            ),
            "readiness": "Use supplied reviewed curriculum evidence; age and grade do not establish mastery.",
        }


def from_legacy_level(level: str) -> LearnerContext:
    """Parse explicit grade labels only; preserve unknown/age text on the request."""
    text = level.strip().lower()
    if re.search(r"\bfamily\b", text):
        # Ages 11–16 must never become grades 11 and 16.
        match = re.fullmatch(r"family\s+grades?\s+([k\d,\s&]+)", text)
        grades = re.findall(r"k|\d+", match[1]) if match else []
        if grades and all(g.upper() in ("K", *map(str, range(1, 13))) for g in grades):
            unique = list(dict.fromkeys(g.upper() for g in grades))
            return LearnerContext(mode="family", declared_grades=unique)
        return LearnerContext(mode="family")
    match = re.fullmatch(r"(?:(?:grade|year)\s*)?(k|kindergarten|[1-9]|1[0-2])(?:st|nd|rd|th)?(?:\s*grade)?", text)
    if match:
        grade = "K" if match[1] in {"k", "kindergarten"} else match[1]
        return LearnerContext(mode="individual", declared_grades=[grade])
    return LearnerContext()


def resolve_context(level: str, supplied: LearnerContext | None = None) -> LearnerContext:
    # Explicit structured context wins; the original legacy string is retained.
    return supplied or from_legacy_level(level)


def private_authoring(level: str, materials: str, learning_need: str) -> bool:
    # Free-text inputs can contain identifiable work. Do not share their generated
    # canonical across learners. The original text is never used as a public key.
    parsed = from_legacy_level(level)
    return bool(materials.strip() or learning_need.strip() or not parsed.declared_grades)
