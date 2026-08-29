import pytest

from app.curriculum.family_style import CANONICAL_FORMAT_VERSION
from app.services.resource_router import (
    ResourceQuery,
    ResourceRouter,
    _curated,
    _curated_archive_evidence,
    _youtube_resources,
    resource_block_for_lesson,
    resource_block_from_packet,
)


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
    assert block["canonical_format_version"] == CANONICAL_FORMAT_VERSION
    assert block["experience_stage"] == "RESOURCE"
    assert block["metadata"]["resources"][0]["id"] == "makecode:arcade"


def test_math_resource_block_requires_fresh_demonstration_after_play():
    block = resource_block_from_packet({
        "track": "APPLIED_MATHEMATICS",
        "resources": [{"id": "mathigon-polypad", "resource_type": "MANIPULATIVE"}],
        "rules": ["Playing is practice, not mastery."],
    })

    assert block["title"] == "Play with the idea, then prove it"
    assert "fresh case" in block["content"]
    assert block["metadata"]["requires_evidence"] is True
    assert block["metadata"]["exact_target_required"] is True


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
async def test_math_resources_are_part_of_the_broader_router_not_a_four_site_whitelist():
    results = await _curated(ResourceQuery(
        topic="ratios percentages and package claims",
        track="APPLIED_MATHEMATICS",
        grade_level="7",
    ), DummyClient())
    ids = {item.id for item in results}

    assert {"mathigon:polypad", "nrich:investigations"} <= ids
    assert {"makecode:arcade", "khan:practice", "concord:models"} <= ids


@pytest.mark.asyncio
async def test_curated_history_sources_include_docsteach_and_dpla():
    results = await _curated(ResourceQuery(topic="Great Depression", track="TRUTH_HISTORY"), DummyClient())
    ids = {item.id for item in results}
    assert {"docsteach:primary", "dpla:search"} <= ids


def test_robber_baron_evidence_pack_uses_item_pages_and_claim_boundaries():
    results = _curated_archive_evidence(ResourceQuery(
        topic="railroads monopoly Standard Oil",
        track="TRUTH_HISTORY",
        resource_types=("PRIMARY_SOURCE",),
    ))

    assert {item.id for item in results} == {
        "archives:pacific-railway-act-1862",
        "archives:interstate-commerce-act-1887",
        "loc:2001695241",
        "loc:2007675471",
    }
    assert all(item.availability == "VERIFIED_ARCHIVE_ITEM" for item in results)
    assert all(item.source_item_id and item.holding_institution for item in results)
    assert all("search?" not in item.source_url for item in results)
    assert all(item.evidence_scope for item in results)


def test_archive_evidence_pack_does_not_leak_into_unrelated_history():
    assert _curated_archive_evidence(ResourceQuery(
        topic="The Boston Tea Party",
        track="TRUTH_HISTORY",
    )) == []


@pytest.mark.asyncio
async def test_router_keeps_verified_archive_items_when_live_loc_api_fails(monkeypatch):
    async def broken(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    async def empty(*_args, **_kwargs):
        return []

    monkeypatch.setattr("app.services.resource_router._loc", broken)
    for provider in ("_smithsonian", "_nasa", "_inaturalist", "_curated"):
        monkeypatch.setattr(f"app.services.resource_router.{provider}", empty)

    packet = await ResourceRouter().search(ResourceQuery(
        topic="railroads monopoly Standard Oil",
        track="TRUTH_HISTORY",
        resource_types=("PRIMARY_SOURCE",),
        interactive_preferred=False,
        limit=8,
    ))

    assert packet["provider_failures"] == ["loc"]
    assert len(packet["resources"]) == 4
    assert all(
        item["availability"] == "VERIFIED_ARCHIVE_ITEM"
        for item in packet["resources"]
    )


@pytest.mark.asyncio
async def test_verified_items_outrank_archive_search_pages(monkeypatch):
    async def empty(*_args, **_kwargs):
        return []

    for provider in ("_loc", "_smithsonian", "_nasa", "_inaturalist"):
        monkeypatch.setattr(f"app.services.resource_router.{provider}", empty)

    packet = await ResourceRouter().search(ResourceQuery(
        topic="railroads monopoly Standard Oil corporate power",
        track="TRUTH_HISTORY",
        resource_types=("PRIMARY_SOURCE",),
        interactive_preferred=False,
        limit=8,
    ))

    assert [
        item["availability"] for item in packet["resources"][:4]
    ] == ["VERIFIED_ARCHIVE_ITEM"] * 4
