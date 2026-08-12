"""Small accountable agent team for the personalized mission lifecycle.

These agents make decisions and contracts; specialist lesson agents still teach,
and RegistrarAgent remains the only authority that awards credit.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

from app.agents.resource_intelligence import ResourceIntelligenceAgent


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


class GameSmithAgent:
    """Build safe declarative mini-game blueprints from curriculum missions."""

    _TEMPLATES = {
        "TRUTH_HISTORY": "investigation_adventure",
        "JUSTICE_CHANGEMAKING": "investigation_adventure",
        "GOVERNMENT_ECONOMICS": "journey_simulation",
        "APPLIED_MATHEMATICS": "maze_quest",
        "CREATION_SCIENCE": "systems_builder",
        "HEALTH_NATUROPATHY": "maze_quest",
        "HOMESTEADING": "journey_simulation",
        "ENGLISH_LITERATURE": "investigation_adventure",
        "CREATIVE_ECONOMY": "market_simulation",
        "DISCIPLESHIP": "journey_simulation",
    }

    def blueprint_for(self, item: Any, canonical_slug_value: str, grade_level: str) -> dict[str, Any]:
        template = self._TEMPLATES.get(item.track, "matching_challenge")
        return {
            "template": template,
            "title": f"Play: {item.title}",
            "learning_objective": item.description,
            "content_source": {"type": "canonical_lesson", "slug": canonical_slug_value},
            "grade_level": grade_level,
            "play_time_minutes": 6,
            "rules": [
                "Every correct move must depend on lesson content, not luck.",
                "Give a useful explanation after each choice.",
                "Respond to mistakes inside the world without lowering the truth standard.",
            ],
            "win_condition": "Use the lesson correctly to solve the interactive challenge.",
            "runtime": "declarative_only",
        }

    def _fallback_2d(self, canonical: dict[str, Any], game_kind: str) -> dict[str, Any]:
        """Always-playable level assembled only from canonical block titles/content."""
        blocks = list(canonical.get("blocks", []))
        source_items = []
        for index, block in enumerate(blocks[:6]):
            title = str(block.get("title") or f"Lesson discovery {index + 1}")[:34]
            content = re.sub(r"\s+", " ", str(block.get("content", ""))).strip()
            effect = (content.split(".")[0] or f"You recovered {title}")[:120] + "."
            source_items.append((title, effect))
        while len(source_items) < 6:
            source_items.append((f"Lesson discovery {len(source_items) + 1}", "This connects another part of the lesson."))
        coordinates = [(2, 6), (4, 2), (7, 6), (9, 3), (3, 1), (8, 1)]
        sprites = ["scroll", "journal", "tool", "map", "lantern", "key"]
        return {
            "mechanic": "top_down_2d",
            "game_kind": game_kind,
            "scenario": f"Explore {canonical.get('title') or canonical.get('topic')} and recover the ideas that unlock the destination.",
            "world": {"width": 12, "height": 8, "theme": str(canonical.get("track", "learning")).lower()},
            "player": {"x": 0, "y": 7, "sprite": "explorer"},
            "goal": {"x": 11, "y": 0, "label": "Complete the mission"},
            "obstacles": [
                {"x": x, "y": y, "sprite": "tree"}
                for x, y in [(5, 0), (5, 1), (5, 2), (5, 4), (5, 5), (5, 6), (1, 3), (2, 3), (8, 4), (9, 4), (10, 4)]
            ],
            "objects": [
                {"id": f"lesson-object-{index + 1}", "x": coordinates[index][0], "y": coordinates[index][1],
                 "sprite": sprites[index], "label": title, "effect": effect, "value": 1}
                for index, (title, effect) in enumerate(source_items)
            ],
            "required_objects": 4,
            "success_message": "You used the lesson to unlock the destination.",
        }

    async def build_playable(self, topic: str, track: str, grade_level: str) -> dict[str, Any]:
        """Create or reuse a playable, declarative game grounded in a canonical."""
        availability = await CurriculumLibrarianAgent().lookup(topic, track)
        shell = self.blueprint_for(
            type("GameTopic", (), {"title": topic, "track": track, "description": f"Practice {topic} through play."})(),
            availability.slug,
            grade_level,
        )
        if not availability.ready:
            return {**shell, "canonical_ready": False, "rounds": []}

        from app.connections.canonical_store import canonical_store
        from app.connections.redis_client import redis_client

        cache_key = f"minigame:{availability.slug}:grade:{grade_level}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        canonical = await canonical_store.get(availability.slug)
        lesson_text = "\n\n".join(
            str(block.get("content", "")) for block in (canonical or {}).get("blocks", [])
        )[:9000]
        from app.agents.orchestrator import _synthesis_call
        game_kind = shell["template"]
        schema = (
            'Return {"game":{"mechanic":"top_down_2d","game_kind":"GAME_KIND","scenario":"...",'
            '"world":{"width":12,"height":8,"theme":"..."},"player":{"x":1,"y":6,"sprite":"..."},'
            '"goal":{"x":10,"y":1,"label":"..."},"obstacles":[{"x":3,"y":4,"sprite":"..."}],'
            '"objects":[{"id":"...","x":2,"y":5,"sprite":"...","label":"...","effect":"...",'
            '"value":1}],"required_objects":4,"success_message":"..."}}. '
            "Use exactly 6 lesson-grounded objects and 8-14 obstacles. Positions must stay inside the world, "
            "must not overlap the player or goal, and must leave a navigable path. The player moves freely "
            "through the 2D world, interacts with objects, and reaches the goal after collecting or using enough."
        ).replace("GAME_KIND", game_kind)
        prompt = (
            f"Build one playable 2D {game_kind} mini-game from the verified lesson. {schema} "
            "This is not a quiz: do not output questions, answer choices, rounds, sorting, matching, or trivia. Every object and "
            "consequence must depend on the lesson. Never add facts absent from the lesson. Keep labels concise "
            "and suitable for grade " + grade_level + ".\n\nLESSON:\n" + lesson_text
        )
        try:
            raw = await _synthesis_call(
                "You are GameSmith, a curriculum-grounded educational game designer. Output strict JSON only.",
                prompt,
                max_tokens=1800,
            )
            parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            game_data = parsed.get("game", {})
            valid = game_data if (
                game_data.get("mechanic") == "top_down_2d"
                and game_data.get("game_kind") == game_kind
                and game_data.get("scenario")
                and len(game_data.get("objects", [])) == 6
            ) else {}
        except Exception:
            valid = {}
        if not valid:
            valid = self._fallback_2d(canonical or {}, game_kind)
        game = {**shell, "canonical_ready": True, "interactive": valid}
        if valid:
            try:
                await redis_client.set(cache_key, json.dumps(game), ex=60 * 60 * 24 * 30)
            except Exception:
                pass
        return game


class MissionArchitectAgent:
    """Turn ranked curriculum suggestions into finishable learner missions."""

    def __init__(self) -> None:
        self.librarian = CurriculumLibrarianAgent()
        self.curator = PortfolioCuratorAgent()
        self.gamesmith = GameSmithAgent()
        self.resource_intelligence = ResourceIntelligenceAgent()

    def select_balanced(self, candidates: list[Any], limit: int) -> list[Any]:
        """Own final mission choice: priority first, with cross-track variety."""
        ranked = sorted(candidates, key=lambda item: item.priority, reverse=True)
        chosen: list[Any] = []
        track_counts: dict[str, int] = {}
        for item in ranked:
            if track_counts.get(item.track, 0) < 2:
                chosen.append(item)
                track_counts[item.track] = track_counts.get(item.track, 0) + 1
            if len(chosen) >= limit:
                return chosen
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
        if source == "zpd":
            kind = "skill_mission"
            criteria = [
                "Use the central idea correctly in a new example.",
                "Explain why the example works in your own words.",
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
            "game_blueprint": self.gamesmith.blueprint_for(item, availability.slug, grade_level),
        }


mission_architect = MissionArchitectAgent()
