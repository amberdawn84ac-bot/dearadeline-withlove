"""Small accountable agent team for the personalized mission lifecycle.

These agents make planning decisions and contracts. Canonical investigations
remain the only teaching source, and RegistrarAgent remains the only authority
that awards credit.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from app.agents.resource_intelligence import ResourceIntelligenceAgent
from app.algorithms.sequence_policy import suggestion_is_assignable


@dataclass(frozen=True)
class CurriculumAvailability:
    slug: str
    ready: bool


class CurriculumLibrarianAgent:
    """Find reusable canonical teaching before any mission asks for generation."""

    async def lookup(self, topic: str, track: str) -> CurriculumAvailability:
        from app.connections.canonical_store import canonical_slug, canonical_store

        slug = canonical_slug(topic, track)
        try:
            canonical = await canonical_store.get(slug)
            ready = bool(canonical and canonical.get("blocks"))
        except Exception:
            ready = False
        return CurriculumAvailability(slug=slug, ready=ready)


class PortfolioCuratorAgent:
    """Define the natural portfolio contribution without schoolish evidence language."""

    _VISUAL_TRACKS = {"CREATION_SCIENCE", "HOMESTEADING", "CREATIVE_ECONOMY", "APPLIED_MATHEMATICS"}

    def contribution_for(self, title: str, track: str, source: str) -> str:
        if track in self._VISUAL_TRACKS:
            return f"Add a photo of what you made, tested, or changed for “{title}” to your portfolio, plus one sentence about what you learned."
        if source == "zpd":
            return f"Add your clearest explanation, annotated example, or finished creation from “{title}” to your portfolio."
        return f"Choose the part of “{title}” that best shows what you can now understand or do, and add it to your portfolio."


class MissionArchitectAgent:
    """Turn ranked curriculum suggestions into finishable learner missions."""

    def __init__(self) -> None:
        self.librarian = CurriculumLibrarianAgent()
        self.curator = PortfolioCuratorAgent()
        self.resource_intelligence = ResourceIntelligenceAgent()

    def select_balanced(self, candidates: list[Any], limit: int) -> list[Any]:
        """Own final mission choice and enforce sequencing at the last possible gate."""
        ranked = sorted(
            (item for item in candidates if suggestion_is_assignable(item)),
            key=lambda item: item.priority,
            reverse=True,
        )
        chosen: list[Any] = []
        seen_tracks: set[str] = set()
        # First give the learner the strongest mission from each available
        # track. This prevents the first alphabetic subject from occupying most
        # of Today when hundreds of unfinished standards share a priority.
        for item in ranked:
            if item.track not in seen_tracks:
                chosen.append(item)
                seen_tracks.add(item.track)
            if len(chosen) >= limit:
                return chosen
        # Only after every available track is represented may a track receive a
        # second mission, still preserving the original priority order.
        for item in ranked:
            if item not in chosen:
                chosen.append(item)
            if len(chosen) >= limit:
                break
        return chosen

    async def compose(self, suggestions: list[Any], grade_level: str, interests: list[str]) -> list[Any]:
        availability = await asyncio.gather(*[
            self.librarian.lookup(item.title, item.track) for item in suggestions
        ])
        resource_packets = [
            self.resource_intelligence.select(item.title, item.track) for item in suggestions
        ]
        return [
            item.model_copy(update=self._mission_contract(item, found, grade_level, interests, resource_packet))
            for item, found, resource_packet in zip(suggestions, availability, resource_packets)
        ]

    def _mission_contract(
        self,
        item: Any,
        availability: CurriculumAvailability,
        grade_level: str,
        interests: list[str],
        resource_packet: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = item.source
        sequence_policy = getattr(item, "sequence_policy", "OPEN")
        bridge_required = bool(getattr(item, "bridge_required", False))
        if sequence_policy == "HARD":
            kind = "skill_mission"
            criteria = [
                "Use the central idea correctly in a new example.",
                "Explain why the example works in your own words.",
            ]
        elif bridge_required:
            kind = "supported_mission"
            criteria = [
                "Begin by showing what you already understand about the foundation.",
                "Use the built-in bridge before dependent work if that foundation is not secure yet.",
                "Demonstrate the investigation's central idea through the real outcome.",
            ]
        elif source == "interest":
            kind = "interest_mission"
            criteria = [
                "Learn the key idea before beginning the project.",
                "Make or decide something real using what you learned.",
            ]
        else:
            kind = "exploration_mission"
            criteria = [
                "Complete the shared lesson experience.",
                "Create one useful summary, model, plan, or reflection.",
            ]

        interest_note = next((interest for interest in interests if interest.lower() in item.title.lower()), "")
        return {
            "canonical_ready": availability.ready,
            "canonical_slug": availability.slug,
            "mission_kind": kind,
            "success_criteria": criteria,
            "portfolio_prompt": self.curator.contribution_for(item.title, item.track, source),
            "next_action": "Open the saved lesson" if availability.ready else "Prepare and save the canonical lesson",
            "personalization_reason": (
                f"Chosen for your interest in {interest_note}." if interest_note
                else f"Chosen from your grade {grade_level} readiness, current mastery, and credit path."
            ),
            "resource_packet": resource_packet or {"topic": item.title, "track": item.track, "sources": [], "rules": []},
        }


mission_architect = MissionArchitectAgent()
