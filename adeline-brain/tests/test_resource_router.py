import pytest

from app.services.resource_router import ResourceQuery, ResourceRouter, _curated, _youtube_resources, resource_block_for_lesson


class DummyClient:
    pass


@pytest.mark.asyncio
async def test_makecode_is_a_game_builder_with_portfolio_evidence():
    results = await _curated(ResourceQuery(
        topic="build a conservation of energy arcade game",
        track="CREATION_SCIENCE",
        resource_types=("GAME_BUILDER",),
    ), DummyClient())
    makecode = next(item for item in results if item.id == "makecode:arcade")
    assert makecode.resource_type == "GAME_BUILDER"
    assert makecode.game_mode == "BUILD"
    assert "playable project" in makecode.portfolio_output.lower()


@pytest.mark.asyncio
async def test_commercial_context_forces_phet_to_link():
    results = await _curated(ResourceQuery(
        topic="conservation of energy physics",
        track="CREATION_SCIENCE",
        commercial_context=True,
    ), DummyClient())
    phet = next(item for item in results if item.id == "phet:search")
    assert phet.use_mode == "LINK"
    assert phet.license == "CC BY-NC 4.0"


@pytest.mark.asyncio
async def test_provider_failure_does_not_break_router(monkeypatch):
    async def broken(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.services.resource_router._loc", broken)
    packet = await ResourceRouter().search(ResourceQuery(
        topic="build a game",
        track="CREATIVE_ECONOMY",
        resource_types=("GAME_BUILDER",),
    ))
    assert any(item["id"] == "makecode:arcade" for item in packet["resources"])
    assert "loc" in packet["provider_failures"]


@pytest.mark.asyncio
async def test_lesson_resource_block_is_live_not_canonical_content(monkeypatch):
    async def fake_search(_query):
        return {"resources": [{"id": "makecode:arcade"}], "rules": ["unknown means link"]}

    monkeypatch.setattr("app.services.resource_router.resource_router.search", fake_search)
    block = await resource_block_for_lesson("energy", "CREATION_SCIENCE", "8")
    assert block["block_type"] == "RESOURCE_COLLECTION"
    assert block["canonical_format_version"] == 6
    assert block["metadata"]["resources"][0]["id"] == "makecode:arcade"


def test_science_youtube_is_restricted_to_approved_channels():
    videos = _youtube_resources(ResourceQuery(topic="chemical reactions", track="CREATION_SCIENCE"))
    providers = {video.provider for video in videos}
    assert providers == {"Science Buddies", "The Royal Institution", "HHMI BioInteractive"}
    assert all(video.license == "YOUTUBE_LINK_OR_OFFICIAL_EMBED" for video in videos)


def test_history_youtube_requires_evidence_checking():
    videos = _youtube_resources(ResourceQuery(topic="Great Depression", track="TRUTH_HISTORY"))
    assert {video.provider for video in videos} >= {"Voices of the Past", "U.S. National Archives"}
    assert all("verify" in video.mastery_prompt.lower() for video in videos)


@pytest.mark.asyncio
async def test_curated_science_sources_include_models_experiments_and_real_data():
    results = await _curated(ResourceQuery(topic="diffusion", track="CREATION_SCIENCE"), DummyClient())
    ids = {item.id for item in results}
    assert {"concord:models", "science-buddies:projects", "hhmi:biointeractive", "bhl:search"} <= ids


@pytest.mark.asyncio
async def test_curated_history_sources_include_docsteach_and_dpla():
    results = await _curated(ResourceQuery(topic="Great Depression", track="TRUTH_HISTORY"), DummyClient())
    ids = {item.id for item in results}
    assert {"docsteach:primary", "dpla:search"} <= ids
