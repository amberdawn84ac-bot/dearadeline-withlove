import pytest

from app.agents.mission_team import (
    CurriculumAvailability,
    MissionArchitectAgent,
    PortfolioCuratorAgent,
)
from app.api.learning_plan import LessonSuggestion


def suggestion(**updates):
    values = {
        "id": "mission-1",
        "title": "Build a Garden Irrigation Plan",
        "track": "APPLIED_MATHEMATICS",
        "description": "Use ratios and measurement in a real plan.",
        "emoji": "📐",
        "priority": 0.9,
        "source": "interest",
        "sequence_policy": "SUPPORTED",
        "sequence_state": "BRIDGE_REQUIRED",
        "bridge_required": True,
    }
    values.update(updates)
    return LessonSuggestion(**values)


def test_portfolio_curator_uses_portfolio_language_for_visual_work():
    prompt = PortfolioCuratorAgent().contribution_for(
        "Build a Garden Irrigation Plan", "APPLIED_MATHEMATICS", "interest"
    )
    assert "Add a photo" in prompt
    assert "portfolio" in prompt
    assert "submit evidence" not in prompt.lower()


def test_mission_contract_has_a_finish_line_and_reuses_canonical():
    agent = MissionArchitectAgent()
    item = suggestion()
    update = agent._mission_contract(
        item,
        CurriculumAvailability(slug="abc123", ready=True),
        "8",
        ["gardening"],
    )
    assert update["canonical_ready"] is True
    assert update["next_action"] == "Open the saved lesson"
    assert len(update["success_criteria"]) == 3
    assert update["mission_kind"] == "supported_mission"
    assert "portfolio" in update["portfolio_prompt"]


def test_mission_architect_owns_priority_and_track_variety():
    agent = MissionArchitectAgent()
    candidates = [
        suggestion(id="math-1", priority=.99),
        suggestion(id="math-2", priority=.98),
        suggestion(id="math-3", priority=.97),
        suggestion(id="history", track="TRUTH_HISTORY", priority=.90),
    ]
    chosen = agent.select_balanced(candidates, 3)
    assert [item.id for item in chosen] == ["math-1", "history", "math-2"]


def test_mission_architect_never_selects_a_locked_hard_concept():
    agent = MissionArchitectAgent()
    locked = suggestion(
        id="locked",
        source="zpd",
        concept_id="fractions",
        sequence_policy="HARD",
        sequence_state="LOCKED",
        prerequisite_readiness=.4,
    )
    ready = suggestion(
        id="ready",
        source="zpd",
        concept_id="addition",
        sequence_policy="HARD",
        sequence_state="READY",
        prerequisite_readiness=1,
    )
    assert [item.id for item in agent.select_balanced([locked, ready], 2)] == ["ready"]


@pytest.mark.asyncio
async def test_compose_preserves_ranking_and_enriches_each_mission(monkeypatch):
    agent = MissionArchitectAgent()

    async def ready(topic, track):
        return CurriculumAvailability(slug=f"{track}:{topic}", ready=True)

    monkeypatch.setattr(agent.librarian, "lookup", ready)
    ranked = [suggestion(id="first"), suggestion(id="second", title="Measure a Tiny House")]
    composed = await agent.compose(ranked, "8", ["gardening"])
    assert [item.id for item in composed] == ["first", "second"]
    assert all(item.canonical_ready for item in composed)
