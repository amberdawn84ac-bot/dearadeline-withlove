from dataclasses import dataclass

from app.agents.curriculum_planner import PersonalizedCurriculumPlannerAgent


@dataclass
class Standard:
    standard_id: str
    subject: str
    strand: str
    mastered: bool = False


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
    assert len({seed[2] for seed in older_sibling_cycle}) == 10


def test_households_get_distinct_stable_investigation_orders():
    planner = PersonalizedCurriculumPlannerAgent()

    assert planner.family_investigation_cycle("family-a") == planner.family_investigation_cycle("family-a")
    assert planner.family_investigation_cycle("family-a") != planner.family_investigation_cycle("family-b")
