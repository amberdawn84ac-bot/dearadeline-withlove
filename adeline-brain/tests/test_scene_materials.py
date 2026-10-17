import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api import classrooms as api
from app.curriculum.classroom import CLASSROOM_VERSION
from app.curriculum.scene_materials import (
    MaterialDraft,
    attached_sources,
    available_sources,
    resolve_materials,
)
from tests.test_classroom import blueprint, scene


def test_saved_scene_gets_actual_promised_book_and_map():
    saved = scene(0)
    saved["actions"] = [
        {
            "role_id": "peer",
            "text": "I've got Julius Caesar from Project Gutenberg ready, and a map of the Roman Republic displayed.",
        }
    ]
    resources = attached_sources(saved)
    assert [r["kind"] for r in resources] == ["link", "image"]
    assert resources[0]["url"].startswith("https://www.gutenberg.org/")
    assert resources[1]["image_url"].startswith("https://upload.wikimedia.org/")
    assert resources[1]["license_url"]
    assert attached_sources({"actions": [{"text": "A map of Rome in 200 CE."}]}) == []


def test_examples_are_delivered_and_labelled_instead_of_inventing_a_source():
    draft = MaterialDraft(
        examples=[
            {
                "title": "Ethos",
                "text": "A carpenter explains their experience building safe stairs.",
            }
        ]
    )
    resources = resolve_materials(draft, available_sources())
    assert resources[0]["content"].startswith("A carpenter")
    assert "Illustrative example" in resources[0]["attribution"]
    with pytest.raises(ValueError, match="unsupplied source"):
        resolve_materials(
            MaterialDraft(source_ids=["made-up-map"]), available_sources()
        )
    with pytest.raises(ValueError, match="usable"):
        resolve_materials(MaterialDraft(), available_sources())


def fake_document():
    return dict(
        format_version=CLASSROOM_VERSION,
        phase="ready",
        blueprint=blueprint(),
        scenes=[scene(i) for i in range(4)],
        responses={"s0": {"text": "Saved work"}},
    )


def setup_connection(monkeypatch, doc):
    conn = AsyncMock()
    conn.transaction = MagicMock(return_value=AsyncMock())
    conn.fetchrow.return_value = {"id": "experience", "metadataJson": doc}
    monkeypatch.setattr(api, "get_db_conn", AsyncMock(return_value=conn))
    monkeypatch.setattr("app.services.rate_limit.enforce_rate_limit", AsyncMock())
    return conn


@pytest.mark.asyncio
async def test_scene_materials_are_saved_once_without_changing_work(monkeypatch):
    doc = fake_document()
    conn = setup_connection(monkeypatch, doc)
    generate = AsyncMock(
        return_value=MaterialDraft(
            examples=[
                {
                    "title": "Logos",
                    "text": "Compare the stated costs of two illustrative repair options.",
                }
            ]
        )
    )
    monkeypatch.setattr(api, "generate_json", generate)
    body = api.MaterialRequest(scene_id="s0")
    first = await api.scene_materials("child", "unit", body, _user="child")
    second = await api.scene_materials("child", "unit", body, _user="child")
    assert first == second
    generate.assert_awaited_once()
    assert "question" not in generate.call_args.args[2]["scene"]
    stored = json.loads(conn.execute.call_args.args[2])
    assert stored["responses"] == {"s0": {"text": "Saved work"}}
    assert "resources" not in stored["scenes"][1]
    public = api.public_state(
        {"id": "experience", "title": "Mixtures", "metadata": stored}
    )
    assert public["classroom"]["scenes"][0]["resources"] == first
    assert "answer" not in public["classroom"]["scenes"][3]["question"]


@pytest.mark.asyncio
async def test_missing_or_retired_experience_cannot_generate_materials(monkeypatch):
    setup_connection(monkeypatch, {"phase": "ready", "format_version": "old"})
    generate = AsyncMock()
    monkeypatch.setattr(api, "generate_json", generate)
    with pytest.raises(HTTPException) as error:
        await api.scene_materials(
            "child", "unit", api.MaterialRequest(scene_id="s0"), _user="child"
        )
    assert error.value.status_code == 409
    generate.assert_not_awaited()
