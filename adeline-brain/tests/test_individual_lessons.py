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
    assert elementary[0].id == "family-science:scene"
