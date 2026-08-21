"""Authoritative rules for a student's living, complete curriculum plan.

This agent plans; specialist agents teach. Canonicals store reusable teaching.
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
    # These are intentionally multi-age investigation frames. The household gets
    # one shared frame; grade/mastery-specific standards are assigned separately.
    FAMILY_INVESTIGATIONS = {
        "CREATION_SCIENCE": (
            ("Kitchen Chemistry", "What changes when a family cooks, mixes, heats, and cools ordinary ingredients?"),
            ("Backyard Ecosystem Census", "Observe the living network just outside the door and explain what depends on what."),
            ("Weather Detectives", "Measure local weather, look for patterns, and test a forecast."),
            ("Light, Sound, and Shadows", "Build simple tests that make invisible waves easier to notice."),
        ),
        "HEALTH_NATUROPATHY": (
            ("Family Sleep Lab", "Collect safe family observations about rest and design a better bedtime experiment."),
            ("Food as Fuel", "Compare meals, labels, energy, and evidence to plan food that serves the family well."),
            ("Move and Measure", "Explore how movement changes pulse, breathing, balance, strength, and mood."),
            ("Herb and Remedy Evidence Hunt", "Investigate a traditional household remedy and separate history, claims, safety, and evidence."),
        ),
        "HOMESTEADING": (
            ("Seed-to-Supper Challenge", "Plan how one food travels from soil or farm to the family table."),
            ("Water Wise Household", "Measure household water use and invent one practical conservation improvement."),
            ("Build a Better Garden", "Observe a growing space, map its needs, and propose a useful design."),
            ("Preserve the Harvest", "Explore why food spoils and compare safe ways people make it last."),
        ),
        "GOVERNMENT_ECONOMICS": (
            ("Run a Family Market", "Create a tiny market to investigate price, scarcity, choice, work, and value."),
            ("Who Decides Here?", "Map how a real local decision moves through family, neighborhood, and government."),
            ("Needs, Wants, and a Real Budget", "Make tradeoffs with a realistic family mission and explain every choice."),
            ("The Journey of a Dollar", "Trace where money comes from, where it goes, and what each exchange means."),
        ),
        "JUSTICE_CHANGEMAKING": (
            ("Fair Is Not Always Equal", "Use stories and real scenarios to investigate fairness, responsibility, and repair."),
            ("One Helpful Change", "Notice a local problem, listen to affected people, and take one documented action."),
            ("Whose Voice Is Missing?", "Compare accounts of the same event and look for people the record leaves out."),
            ("Design for Welcome", "Audit a familiar place for access and belonging, then propose an improvement."),
        ),
        "DISCIPLESHIP": (
            ("A Table of Hospitality", "Study biblical hospitality and practice welcoming someone in a concrete way."),
            ("Wisdom in Everyday Choices", "Use a wisdom text to examine a real decision and live one principle together."),
            ("Creation Care Mission", "Study stewardship, observe one part of creation, and care for it together."),
            ("Courage and Faithfulness", "Investigate a biblical story of courage and practice one faithful action."),
        ),
        "TRUTH_HISTORY": (
            ("Family History Detective", "Use interviews, photographs, objects, maps, and records to test a family story."),
            ("A Week in Another Time", "Reconstruct ordinary life in one historical place using primary evidence."),
            ("Map the Story", "Use old and new maps to discover how a place changed and why."),
            ("Newsroom from the Past", "Compare period sources and publish a careful account of what happened."),
        ),
        "ENGLISH_LITERATURE": (
            ("Storytelling Studio", "Read a strong story together, study its craft, and create a family version."),
            ("Poetry You Can Hear", "Explore rhythm, image, voice, and meaning by performing and making poems."),
            ("Book-to-Life Challenge", "Follow a question from a shared text into observation, discussion, and action."),
            ("Family Oral History", "Turn a recorded family memory into a truthful, vivid piece for an audience."),
        ),
        "APPLIED_MATHEMATICS": (
            ("Measure, Design, Build", "Use measurement, number, geometry, and revision to make something the family can use."),
            ("Family Game Lab", "Play, analyze, and redesign a game using patterns, strategy, probability, and data."),
            ("Plan a Real Trip", "Use maps, time, distance, cost, and tradeoffs to build a workable family plan."),
            ("Data in Our House", "Collect a harmless household dataset, represent it clearly, and explain what it does and does not show."),
        ),
        "CREATIVE_ECONOMY": (
            ("Make Something Worth Sharing", "Design, prototype, price, and present something useful or beautiful."),
            ("Family Pop-Up Studio", "Choose roles and turn a creative idea into a tiny collaborative production."),
            ("Solve a Household Problem", "Interview the users, build a prototype, test it, and improve it."),
            ("Tell the Story of a Product", "Investigate materials, labor, cost, design, and honest communication."),
        ),
    }

    def family_investigation_cycle(self, household_id: str, total_weeks: int = 36) -> list[tuple]:
        """Return a stable household-wide cycle spanning all ten learning tracks."""
        seeds = []
        for track in self.TRACKS:
            for index, (title, description) in enumerate(self.FAMILY_INVESTIGATIONS[track]):
                seeds.append((f"family-{track.lower()}-{index}", title, track, description))
        balanced = self.balance_weekly_seeds(seeds, total_weeks=len(seeds))
        offset = int(hashlib.sha256(household_id.encode("utf-8")).hexdigest()[:8], 16) % len(balanced)
        rotated = balanced[offset:] + balanced[:offset]
        return rotated[:total_weeks]

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
