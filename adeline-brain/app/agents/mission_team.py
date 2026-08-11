"""Small accountable agent team for the personalized mission lifecycle.

These agents make decisions and contracts; specialist lesson agents still teach,
and RegistrarAgent remains the only authority that awards credit.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

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
        "TRUTH_HISTORY": "sort_and_match",
        "JUSTICE_CHANGEMAKING": "sort_and_match",
        "GOVERNMENT_ECONOMICS": "budget_balance",
        "APPLIED_MATHEMATICS": "route_builder",
        "CREATION_SCIENCE": "route_builder",
        "HEALTH_NATUROPATHY": "sort_and_match",
        "HOMESTEADING": "route_builder",
        "ENGLISH_LITERATURE": "sort_and_match",
        "CREATIVE_ECONOMY": "budget_balance",
        "DISCIPLESHIP": "choice_consequence",
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
                "Adjust the next round after two misses without lowering the truth standard.",
            ],
            "win_condition": "Use the lesson correctly to solve the interactive challenge.",
            "runtime": "declarative_only",
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
        mechanic = shell["template"]
        schemas = {
            "sort_and_match": (
                'Return {"game":{"mechanic":"sort_and_match","scenario":"...","zones":[{"id":"...","label":"..."}],'
                '"items":[{"id":"...","label":"...","detail":"...","correct_zone":"..."}],"success_message":"..."}}. '
                "Use 2-4 zones and exactly 6 items. The player drags each item into a zone."
            ),
            "route_builder": (
                'Return {"game":{"mechanic":"route_builder","scenario":"...","grid_size":5,'
                '"start":{"x":0,"y":4},"goal":{"x":4,"y":0},"obstacles":[{"x":1,"y":3}],'
                '"max_moves":10,"success_message":"..."}}. The route and obstacles must model a real constraint from the lesson.'
            ),
            "budget_balance": (
                'Return {"game":{"mechanic":"budget_balance","scenario":"...","budget":100,'
                '"required_value":10,"options":[{"id":"...","label":"...","cost":20,"value":3,"consequence":"..."}],'
                '"success_message":"..."}}. Use exactly 6 options; the player must meet required_value without overspending.'
            ),
            "choice_consequence": (
                'Return {"game":{"mechanic":"choice_consequence","scenario":"...",'
                '"choices":[{"id":"...","label":"...","consequence":"...","wisdom_score":2}],'
                '"success_message":"..."}}. Use exactly 4 meaningful choices with wisdom_score 0-3.'
            ),
        }
        prompt = (
            f"Build one interactive {mechanic} mini-game from the verified lesson. {schemas[mechanic]} "
            "This is not a quiz: do not output questions, answer choices, rounds, or trivia. Every object and "
            "consequence must depend on the lesson. Never add facts absent from the lesson. Keep labels concise "
            "and suitable for grade " + grade_level + ".\n\nLESSON:\n" + lesson_text
        )
        raw = await _synthesis_call(
            "You are GameSmith, a curriculum-grounded educational game designer. Output strict JSON only.",
            prompt,
            max_tokens=1800,
        )
        try:
            parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            game_data = parsed.get("game", {})
            valid = game_data if game_data.get("mechanic") == mechanic and game_data.get("scenario") else {}
        except (json.JSONDecodeError, AttributeError, TypeError):
            valid = {}
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
        return [
            item.model_copy(update=self._mission_contract(item, found, grade_level, interests))
            for item, found in zip(suggestions, availability)
        ]

    def _mission_contract(
        self,
        item: Any,
        availability: CurriculumAvailability,
        grade_level: str,
        interests: list[str],
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
            "game_blueprint": self.gamesmith.blueprint_for(item, availability.slug, grade_level),
        }


mission_architect = MissionArchitectAgent()
