"""Authoritative rules for a student's living, complete curriculum plan.

This agent plans; canonical investigations provide the reusable teaching source.
The Registrar records evidence. Keeping those responsibilities separate prevents
an engaging theme list from masquerading as a complete education.
"""
from __future__ import annotations

import re
import hashlib
from collections import defaultdict
from typing import Any


class PersonalizedCurriculumPlannerAgent:
    TRACKS = (
        "CREATION_SCIENCE", "HEALTH_NATUROPATHY", "HOMESTEADING",
        "GOVERNMENT_ECONOMICS", "JUSTICE_CHANGEMAKING", "DISCIPLESHIP",
        "TRUTH_HISTORY", "ENGLISH_LITERATURE", "APPLIED_MATHEMATICS",
        "CREATIVE_ECONOMY",
    )
    # History/social studies and science are the shared household spine. Math
    # and literacy keep learner-specific prerequisite paths and may support the
    # shared investigation only where the connection is genuine. The remaining
    # tracks are valuable extensions, but they do not silently become the
    # family's school-day theme.
    INDIVIDUAL_SKILL_TRACKS = frozenset({"ENGLISH_LITERATURE", "APPLIED_MATHEMATICS"})
    FAMILY_INVESTIGATION_TRACKS = (
        "CREATION_SCIENCE",
        "HEALTH_NATUROPATHY",
        "HOMESTEADING",
        "GOVERNMENT_ECONOMICS",
        "JUSTICE_CHANGEMAKING",
        "TRUTH_HISTORY",
    )
    FAMILY_STANDARD_FAMILIES = {
        "CREATION_SCIENCE": frozenset({"science", "technology"}),
        "HEALTH_NATUROPATHY": frozenset({"science", "health_movement"}),
        "HOMESTEADING": frozenset({"science", "technology"}),
        "GOVERNMENT_ECONOMICS": frozenset({"social_studies"}),
        "JUSTICE_CHANGEMAKING": frozenset({"social_studies"}),
        "TRUTH_HISTORY": frozenset({"social_studies"}),
    }
    DAILY_RHYTHM = ("Gather around the question", "Investigate together", "Make an individual contribution")
    ACTIVITY_STAGES = (
        ("Question Hunt", "Read, notice, ask questions, and collect the clues that launch this week's investigation."),
        ("Experiment or Game", "Test the week's ideas through a hands-on experiment, simulation, movement challenge, or real game."),
        ("Make, Map, or Solve", "Build something useful, map the evidence, solve a real problem, and write about what changed."),
        ("Family Field Report", "Explain, demonstrate, revise, and save the strongest evidence of learning to the portfolio."),
    )
    TRACK_LABELS = {
        "CREATION_SCIENCE": "Creation and science",
        "HEALTH_NATUROPATHY": "Health and the body",
        "HOMESTEADING": "Homesteading and stewardship",
        "GOVERNMENT_ECONOMICS": "Government and economics",
        "JUSTICE_CHANGEMAKING": "Justice and change-making",
        "DISCIPLESHIP": "Discipleship and discernment",
        "TRUTH_HISTORY": "Truth-based history",
        "ENGLISH_LITERATURE": "Language and literature",
        "APPLIED_MATHEMATICS": "Applied mathematics",
        "CREATIVE_ECONOMY": "Creative economy",
    }

    def family_investigation_cycle(
        self,
        household_id: str,
        total_weeks: int = 36,
        seed_catalog: list[tuple] | tuple[tuple, ...] | None = None,
    ) -> list[tuple]:
        """Return stable household slots; the adaptive planner supplies their content.

        Math and literacy never become the household theme. When an approved
        canonical catalog is supplied, its real investigation titles are used;
        otherwise stable track slots remain available for planning forecasts.
        """
        catalog = [
            seed for seed in list(seed_catalog or [])
            if len(seed) >= 4 and seed[2] in self.FAMILY_INVESTIGATION_TRACKS
        ]
        if not catalog:
            catalog = [
                (
                    f"family-{track.lower()}",
                    self.TRACK_LABELS[track],
                    track,
                    f"A shared {self.TRACK_LABELS[track].lower()} investigation.",
                )
                for track in self.FAMILY_INVESTIGATION_TRACKS
            ]
        offset = int(hashlib.sha256(household_id.encode("utf-8")).hexdigest()[:8], 16) % len(catalog)
        ordered = list(catalog[offset:] + catalog[:offset])
        seeds: list[tuple] = []
        for week in range(total_weeks):
            seed = ordered[week % len(ordered)]
            canonical_topic = seed[4] if len(seed) > 4 else seed[1]
            seeds.append((f"{seed[0]}-week-{week + 1}", seed[1], seed[2], seed[3], canonical_topic))
        return seeds

    def delivery_mode(self, track: str) -> str:
        if track in self.INDIVIDUAL_SKILL_TRACKS:
            return "INDIVIDUAL_SKILL"
        if track in self.FAMILY_INVESTIGATION_TRACKS:
            return "FAMILY_INVESTIGATION"
        return "INDIVIDUAL_EXTENSION"

    def standard_fits_family_track(self, track: str, subject: str) -> bool:
        """Require a real disciplinary fit before attaching coverage to a theme."""
        return self.standard_family(subject) in self.FAMILY_STANDARD_FAMILIES.get(track, frozenset())

    @staticmethod
    def standard_family(subject: str) -> str:
        value = subject.lower()
        if "english" in value or "language art" in value or value in {"ela", "reading"}:
            return "literacy"
        if "math" in value:
            return "math"
        if "science" in value:
            return "science"
        if "social" in value or "history" in value or "civic" in value:
            return "social_studies"
        if "health" in value or "physical education" in value:
            return "health_movement"
        if "art" in value or "music" in value or "theatre" in value:
            return "arts"
        if "computer" in value or "technology" in value:
            return "technology"
        return "enrichment"

    @staticmethod
    def _natural_key(standard: Any) -> tuple:
        difficulty_rank = {
            "EMERGING": 0, "DEVELOPING": 1, "EXPANDING": 2, "MASTERING": 3,
        }.get(str(getattr(standard, "difficulty", "EMERGING")).upper(), 4)
        parts = tuple(
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", standard.standard_id)
            if part
        )
        progression_ordinal = int(getattr(standard, "progression_ordinal", 0) or 0)
        progression_lane = str(getattr(standard, "progression_lane", "") or "")
        if progression_ordinal:
            return (0, progression_lane, progression_ordinal, parts)
        return (1, difficulty_rank, (standard.strand or "").lower(), parts)

    def _dependency_order(self, standards: list[Any]) -> list[Any]:
        """Topologically order verified prerequisites, then stable difficulty/code."""
        by_id = {standard.standard_id: standard for standard in standards}
        prerequisites = {
            standard.standard_id: {
                item for item in getattr(standard, "prerequisite_standard_ids", []) if item in by_id
            }
            for standard in standards
        }
        ordered: list[Any] = []
        remaining = set(by_id)
        while remaining:
            ready = [by_id[item] for item in remaining if not (prerequisites[item] & remaining)]
            if not ready:
                # Invalid/cyclic imported data cannot erase required coverage.
                ready = [by_id[item] for item in remaining]
            ready.sort(key=self._natural_key)
            chosen = ready[0]
            ordered.append(chosen)
            remaining.remove(chosen.standard_id)
        return ordered

    def assign_sequence(self, standards: list[Any], total_weeks: int = 36) -> list[list[str]]:
        """Order foundations, rotate other disciplines, and schedule retrieval."""
        day_count = total_weeks * 4
        assignments: list[list[str]] = [[] for _ in range(day_count)]
        families: dict[str, list[Any]] = defaultdict(list)
        for standard in standards:
            if not standard.mastered:
                families[self.standard_family(standard.subject)].append(standard)
        for family, items in list(families.items()):
            families[family] = self._dependency_order(items)

        for family in ("literacy", "math"):
            for index, standard in enumerate(families.pop(family, [])):
                week = min(index // 2, total_weeks - 1)
                slot = index % 2
                first = week * 4 + slot
                assignments[first].append(standard.standard_id)
                assignments[min(first + 2, day_count - 1)].append(standard.standard_id)

        rotating = [item for family in sorted(families) for item in families[family]]
        for index, standard in enumerate(rotating):
            first = index % day_count
            review = (first + 16 + (index // day_count) * 4) % day_count
            assignments[first].append(standard.standard_id)
            if review != first:
                assignments[review].append(standard.standard_id)
        return [list(dict.fromkeys(codes)) for codes in assignments]

    def balance_weekly_seeds(self, seeds: list[tuple], total_weeks: int = 36) -> list[tuple]:
        """Round-robin all ten tracks while retaining personalized order within each."""
        by_track: dict[str, list[tuple]] = defaultdict(list)
        for seed in seeds:
            by_track[seed[2]].append(seed)
        ordered: list[tuple] = []
        track_order = [track for track in self.TRACKS if by_track.get(track)]
        while len(ordered) < total_weeks and track_order:
            next_round = []
            for track in track_order:
                if by_track[track]:
                    ordered.append(by_track[track].pop(0))
                if by_track[track]:
                    next_round.append(track)
                if len(ordered) == total_weeks:
                    break
            track_order = next_round
        return ordered or seeds

    @staticmethod
    def coverage_is_complete(standards: list[Any], assignments: list[list[str]]) -> bool:
        scheduled = {code for day in assignments for code in day}
        return all(item.mastered or item.standard_id in scheduled for item in standards)


personalized_curriculum_planner = PersonalizedCurriculumPlannerAgent()
