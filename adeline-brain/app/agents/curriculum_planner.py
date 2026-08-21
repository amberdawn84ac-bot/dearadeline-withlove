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
    DAILY_RHYTHM = ("Read together", "Write or tell", "Math through the mission")
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

    def family_investigation_cycle(self, household_id: str, total_weeks: int = 36) -> list[tuple]:
        """Return stable household slots; the adaptive planner supplies their content.

        There is deliberately no canned topic catalog here. A slot coordinates siblings
        around one track and week while standards, gaps, interests, local context, and
        routed resources determine the actual experience at generation time.
        """
        offset = int(hashlib.sha256(household_id.encode("utf-8")).hexdigest()[:8], 16) % len(self.TRACKS)
        tracks = list(self.TRACKS[offset:] + self.TRACKS[:offset])
        seeds: list[tuple] = []
        for week in range(total_weeks):
            track = tracks[week % len(tracks)]
            label = self.TRACK_LABELS[track]
            seeds.append((
                f"family-{track.lower()}-week-{week + 1}",
                f"Family investigation {week + 1}",
                track,
                f"Adeline will shape this {label.lower()} experience from the household's current concepts, interests, gaps, and available real-world resources.",
            ))
        return seeds

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
        parts = tuple(
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", standard.standard_id)
            if part
        )
        return ((standard.strand or "").lower(), parts)

    def assign_sequence(self, standards: list[Any], total_weeks: int = 36) -> list[list[str]]:
        """Order foundations, rotate other disciplines, and schedule retrieval."""
        day_count = total_weeks * 4
        assignments: list[list[str]] = [[] for _ in range(day_count)]
        families: dict[str, list[Any]] = defaultdict(list)
        for standard in standards:
            if not standard.mastered:
                families[self.standard_family(standard.subject)].append(standard)
        for items in families.values():
            items.sort(key=self._natural_key)

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
