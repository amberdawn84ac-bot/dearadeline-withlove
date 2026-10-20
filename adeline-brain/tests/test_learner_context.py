"""Learner adaptation inputs, resource audience, and privacy-safe reuse."""

import pytest
from pydantic import ValidationError

from app.api.classrooms import ClassroomRequest, classroom_slug
from app.curriculum.learner_context import LearnerContext, from_legacy_level, resolve_context
from app.schemas.api_models import Track
from app.services.resource_router import _grade_number


@pytest.mark.parametrize(("label", "grade"), [("3", "3"), ("3rd grade", "3"), ("GRADE 8", "8"), ("8th grade", "8"), ("Kindergarten", "K"), ("K", "K")])
def test_explicit_grade_adapters(label, grade):
    context = from_legacy_level(label)
    assert context.mode == "individual"
    assert context.declared_grades == [grade]
    assert context.resource_grade() == grade


def test_family_age_labels_do_not_become_grades():
    context = from_legacy_level("Family ages 11–16")
    assert context.mode == "family"
    assert context.declared_grades == []
    assert context.resource_grade() is None
    assert _grade_number(None) == -1


def test_structured_family_and_individual_working_level():
    family = LearnerContext(mode="family", declared_grades=["8", "3", "10"])
    assert family.resource_grade() == "3"
    assert "not the family's working level" in family.authoring_context()["resource_grade_basis"]
    child = LearnerContext(mode="individual", declared_grades=["8"], working_grade="5")
    assert resolve_context("8th grade", child).resource_grade() == "5"
    assert "not establish mastery" in child.authoring_context()["readiness"]


@pytest.mark.parametrize("data", [
    {"mode": "family", "working_grade": "5"},
    {"mode": "individual", "declared_grades": ["3", "8"]},
    {"declared_grades": ["16"]},
    {"name": "Do not put learner identities in a shareable context"},
    {"supports": ["medical_diagnosis"]},
    {"language": "English for a named child"},
])
def test_invalid_or_identifying_context_is_rejected(data):
    with pytest.raises(ValidationError):
        LearnerContext(**data)


def test_context_changes_identity_without_cross_learner_private_reuse():
    request = ClassroomRequest(topic="Matter", track=Track.CREATION_SCIENCE, level="8")
    lower = request.model_copy(update={"learner_context": LearnerContext(mode="individual", declared_grades=["8"], working_grade="3")})
    assert classroom_slug(request, "one") != classroom_slug(lower, "one")
    assert classroom_slug(request, "one") == classroom_slug(request, "two")
    private = request.model_copy(update={"learning_need": "Learner-authored explanation for targeted practice"})
    assert classroom_slug(private, "one") != classroom_slug(private, "two")
    age_context = request.model_copy(update={"level": "Family ages 11–16"})
    assert classroom_slug(age_context, "one") != classroom_slug(age_context, "two")
