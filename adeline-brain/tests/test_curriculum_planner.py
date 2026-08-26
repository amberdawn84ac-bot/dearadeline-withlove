from dataclasses import dataclass

from app.agents.curriculum_planner import PersonalizedCurriculumPlannerAgent


@dataclass
class Standard:
    standard_id: str
    subject: str
    strand: str
    mastered: bool = False
    difficulty: str = "EMERGING"
    prerequisite_standard_ids: tuple[str, ...] = ()


def test_planner_owns_all_ten_tracks():
    planner = PersonalizedCurriculumPlannerAgent()
    assert len(planner.TRACKS) == 10
    assert len(set(planner.TRACKS)) == 10


def test_every_unmastered_standard_is_scheduled_and_retrieved():
    planner = PersonalizedCurriculumPlannerAgent()
    standards = [
        Standard("3.ELA.1", "English Language Arts", "Reading"),
        Standard("3.ELA.2", "English Language Arts", "Reading"),
        Standard("3.M.1", "Mathematics", "Numbers"),
        Standard("3.S.1", "Science", "Matter"),
        Standard("3.H.1", "Social Studies", "Oklahoma"),
    ]
    sequence = planner.assign_sequence(standards)
    assert len(sequence) == 144
    assert planner.coverage_is_complete(standards, sequence)
    for standard in standards:
        assert sum(standard.standard_id in day for day in sequence) >= 2


def test_mastered_standard_is_not_reassigned():
    planner = PersonalizedCurriculumPlannerAgent()
    standards = [Standard("3.M.1", "Mathematics", "Numbers", mastered=True)]
    sequence = planner.assign_sequence(standards)
    assert all("3.M.1" not in day for day in sequence)
    assert planner.coverage_is_complete(standards, sequence)


def test_weekly_themes_round_robin_tracks():
    planner = PersonalizedCurriculumPlannerAgent()
    seeds = [
        (f"id-{track}", f"Theme {track}", track, "description", "✦")
        for track in planner.TRACKS
    ]
    ordered = planner.balance_weekly_seeds(seeds)
    assert [seed[2] for seed in ordered[:10]] == list(planner.TRACKS)


def test_siblings_receive_the_same_family_investigation_cycle():
    planner = PersonalizedCurriculumPlannerAgent()
    older_sibling_cycle = planner.family_investigation_cycle("parent-1")
    younger_sibling_cycle = planner.family_investigation_cycle("parent-1")

    assert older_sibling_cycle == younger_sibling_cycle
    assert len(older_sibling_cycle) == 36
    assert len({seed[2] for seed in older_sibling_cycle}) == len(planner.FAMILY_INVESTIGATION_TRACKS)
    assert not ({"ENGLISH_LITERATURE", "APPLIED_MATHEMATICS"} & {seed[2] for seed in older_sibling_cycle})


def test_delivery_modes_keep_the_shared_spine_to_history_and_science():
    planner = PersonalizedCurriculumPlannerAgent()

    assert planner.delivery_mode("TRUTH_HISTORY") == "FAMILY_INVESTIGATION"
    assert planner.delivery_mode("CREATION_SCIENCE") == "FAMILY_INVESTIGATION"
    assert planner.delivery_mode("APPLIED_MATHEMATICS") == "INDIVIDUAL_SKILL"
    assert planner.delivery_mode("ENGLISH_LITERATURE") == "INDIVIDUAL_SKILL"
    assert planner.delivery_mode("DISCIPLESHIP") == "INDIVIDUAL_EXTENSION"
    assert planner.delivery_mode("CREATIVE_ECONOMY") == "INDIVIDUAL_EXTENSION"


def test_standards_attach_to_a_family_theme_only_when_the_discipline_fits():
    planner = PersonalizedCurriculumPlannerAgent()

    assert planner.standard_fits_family_track("CREATION_SCIENCE", "Science") is True
    assert planner.standard_fits_family_track("TRUTH_HISTORY", "Social Studies") is True
    assert planner.standard_fits_family_track("TRUTH_HISTORY", "Mathematics") is False
    assert planner.standard_fits_family_track("CREATION_SCIENCE", "English Language Arts") is False


def test_households_get_distinct_stable_investigation_orders():
    planner = PersonalizedCurriculumPlannerAgent()

    assert planner.family_investigation_cycle("family-a") == planner.family_investigation_cycle("family-a")
    assert planner.family_investigation_cycle("family-a") != planner.family_investigation_cycle("family-b")


def test_verified_dependencies_override_code_order():
    planner = PersonalizedCurriculumPlannerAgent()
    standards = [
        Standard("3.M.1", "Mathematics", "Numbers", prerequisite_standard_ids=("3.M.9",)),
        Standard("3.M.9", "Mathematics", "Numbers"),
    ]
    sequence = planner.assign_sequence(standards)
    first_foundation = next(i for i, day in enumerate(sequence) if "3.M.9" in day)
    first_dependent = next(i for i, day in enumerate(sequence) if "3.M.1" in day)
    assert first_foundation < first_dependent


def test_difficulty_orders_foundations_before_advanced_unmapped_standards():
    planner = PersonalizedCurriculumPlannerAgent()
    standards = [
        Standard("3.M.1", "Mathematics", "Numbers", difficulty="MASTERING"),
        Standard("3.M.9", "Mathematics", "Numbers", difficulty="EMERGING"),
    ]
    sequence = planner.assign_sequence(standards)
    first_foundation = next(i for i, day in enumerate(sequence) if "3.M.9" in day)
    first_advanced = next(i for i, day in enumerate(sequence) if "3.M.1" in day)
    assert first_foundation < first_advanced
