import pytest

from app.api.conversation import _infer_tracks, _requested_resource_types, _wants_outside_resource
from app.services.resource_router import ResourceQuery, _curated


def test_coding_request_is_routed_to_creative_economy():
    message = "Can I learn coding by building a game?"
    assert _wants_outside_resource(message)
    assert _infer_tracks(message, None) == ["CREATIVE_ECONOMY"]
    assert "GAME_BUILDER" in _requested_resource_types(message)


def test_cancer_learning_request_is_routed_to_science():
    message = "I want to learn about cancer and Ewing sarcoma."
    assert _infer_tracks(message, None) == ["CREATION_SCIENCE"]


@pytest.mark.asyncio
async def test_elementary_game_does_not_offer_makecode_arcade():
    packet = await _curated(
        ResourceQuery(topic="play a game about patterns", track="APPLIED_MATHEMATICS", grade_level="1", resource_types=("GAME",)),
        None,
    )
    ids = {item.id for item in packet}
    assert "pbskids:games" in ids
    assert "makecode:arcade" not in ids


@pytest.mark.asyncio
async def test_middle_school_coding_includes_creation_tools():
    packet = await _curated(
        ResourceQuery(topic="learn coding", track="CREATIVE_ECONOMY", grade_level="7", resource_types=("GAME_BUILDER",)),
        None,
    )
    ids = {item.id for item in packet}
    assert "makecode:arcade" in ids
    assert "codeorg:learn" in ids
