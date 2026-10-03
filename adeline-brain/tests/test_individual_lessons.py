"""Today's individual area is the child's part of the open family investigation."""
from app.api.learning_plan import lessons_from_canonical
from app.curriculum.kitchen_case_file import build_kitchen_case_canonical


def test_kitchen_case_splits_into_this_childs_lessons():
    record = build_kitchen_case_canonical()
    elementary = lessons_from_canonical(
        record,
        investigation_id="family-science",
        investigation_title="Forensic Science",
        slot="science",
        track="CREATION_SCIENCE",
        grade_level="5",
    )
    middle = lessons_from_canonical(
        record,
        investigation_id="family-science",
        investigation_title="Forensic Science",
        slot="science",
        track="CREATION_SCIENCE",
        grade_level="8",
    )

    assert [card.title for card in elementary[:3]] == [
        "The crime scene",
        "Who works a scene",
        "Latent prints",
    ]
    assert elementary[0].assignment.startswith("Walk the boundary")
    assert middle[0].assignment.startswith("Start the log")
    assert middle[2].assignment.startswith("Compare the unknown lift")
    assert all("Students will" not in card.assignment for card in elementary)
    assert elementary[0].index == 1
    assert elementary[0].count == 10
    assert elementary[0].faith_talk.startswith("Deuteronomy 19:15")
    assert elementary[0].think_tank.startswith("What can a later person")
    assert elementary[0].id == "family-science:scene"


def test_child_core_skills_attach_to_the_unit_not_the_other_way_around():
    from app.api.learning_plan import IndividualSkillTarget, personalize_lessons

    record = build_kitchen_case_canonical()
    lessons = lessons_from_canonical(
        record,
        investigation_id="family-science",
        investigation_title="Forensic Science",
        slot="science",
        track="CREATION_SCIENCE",
        grade_level="8",
    )
    targets = [
        IndividualSkillTarget(
            suggestion_id="math-1", domain="math", title="Measure a real length and keep the unit",
            track="APPLIED_MATHEMATICS", working_level="8", sequence_state="READY", mastery_eligible=True,
        ),
        IndividualSkillTarget(
            suggestion_id="write-1", domain="literacy", title="Write one precise observation",
            track="ENGLISH_LITERATURE", working_level="8", sequence_state="READY", mastery_eligible=True,
        ),
        IndividualSkillTarget(
            suggestion_id="scripture-1", domain="discipleship", title="Read the verse in context",
            track="DISCIPLESHIP", working_level="8", sequence_state="READY", mastery_eligible=True,
        ),
        IndividualSkillTarget(
            suggestion_id="too-old", domain="math", title="Use a derivative",
            track="APPLIED_MATHEMATICS", working_level="11", sequence_state="READY",
        ),
        IndividualSkillTarget(
            suggestion_id="locked", domain="health", title="Explain a dose",
            track="HEALTH_NATUROPATHY", working_level="8", sequence_state="LOCKED",
        ),
        IndividualSkillTarget(
            suggestion_id="science-gap", domain="science", title="Name a variable",
            track="CREATION_SCIENCE", working_level="8", sequence_state="READY",
        ),
    ]
    personalized = personalize_lessons(lessons, targets, "8", {"CREATION_SCIENCE"})
    blood = next(card for card in personalized if card.title == "Bloodstain patterns")
    custody = next(card for card in personalized if card.title == "Who works a scene")
    scene = next(card for card in personalized if card.title == "The crime scene")

    assert [item.skill_title for item in blood.core_activities] == ["Measure a real length and keep the unit"]
    assert blood.core_activities[0].fit == "direct"
    assert "Measure width and length" in blood.core_activities[0].activity
    assert [item.skill_title for item in custody.core_activities] == ["Write one precise observation"]
    assert custody.core_activities[0].fit == "direct"
    assert [item.skill_title for item in scene.core_activities] == ["Read the verse in context"]
    assert scene.core_activities[0].fit == "bridged"
    assert all(card.kind != "gap" for card in personalized)
    assert all(card.title != "Use a derivative" for card in personalized)
    assert all(card.title != "Explain a dose" for card in personalized)
    assert all(card.title != "Name a variable" for card in personalized)

