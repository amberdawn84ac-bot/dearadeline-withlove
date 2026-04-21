import pytest
from app.utils.stream_parser import parse_stream


async def _collect(chunks: list[str]) -> list[dict]:
    """Feed chunks through the parser and collect all events."""
    async def gen():
        for c in chunks:
            yield c
    return [e async for e in parse_stream(gen())]


def _text(events: list[dict]) -> str:
    """Concatenate all text deltas — callers should use this, not index into events."""
    return "".join(e["delta"] for e in events if e["type"] == "text")


def _blocks(events: list[dict]) -> list[dict]:
    return [e["block"] for e in events if e["type"] == "block"]


@pytest.mark.asyncio
async def test_text_only():
    events = await _collect(["Hello ", "world."])
    assert all(e["type"] == "text" for e in events)
    assert _text(events) == "Hello world."


@pytest.mark.asyncio
async def test_block_only():
    block_json = '{"block_type": "PRIMARY_SOURCE", "content": "test"}'
    events = await _collect([f"<BLOCK>{block_json}</BLOCK>"])
    blocks = _blocks(events)
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == "PRIMARY_SOURCE"


@pytest.mark.asyncio
async def test_text_then_block_then_text():
    block_json = '{"block_type": "QUIZ", "content": "q?"}'
    events = await _collect([f"Before. <BLOCK>{block_json}</BLOCK> After."])
    # Content checks — not brittle on exact event count
    assert "Before." in _text(events)
    assert "After." in _text(events)
    assert len(_blocks(events)) == 1
    # Block must appear between the two text segments
    block_idx  = next(i for i, e in enumerate(events) if e["type"] == "block")
    before_txt = "".join(e["delta"] for e in events[:block_idx]  if e["type"] == "text")
    after_txt  = "".join(e["delta"] for e in events[block_idx+1:] if e["type"] == "text")
    assert "Before." in before_txt
    assert "After." in after_txt


@pytest.mark.asyncio
async def test_block_split_across_chunks():
    block_json = '{"block_type": "LAB_MISSION", "content": "do this"}'
    mid = len(block_json) // 2
    chunks = [
        "Lead-in. <BLOCK>",
        block_json[:mid],
        block_json[mid:],
        "</BLOCK> Follow-up.",
    ]
    events = await _collect(chunks)
    assert "Lead-in." in _text(events)
    assert "Follow-up." in _text(events)
    blocks = _blocks(events)
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == "LAB_MISSION"


@pytest.mark.asyncio
async def test_malformed_block_emitted_as_text():
    events = await _collect(["<BLOCK>not json</BLOCK>"])
    assert all(e["type"] == "text" for e in events)
    assert len(_blocks(events)) == 0


@pytest.mark.asyncio
async def test_multiple_blocks():
    b1 = '{"block_type": "PRIMARY_SOURCE", "content": "a"}'
    b2 = '{"block_type": "QUIZ", "content": "b"}'
    events = await _collect([f"Text. <BLOCK>{b1}</BLOCK> Middle. <BLOCK>{b2}</BLOCK> End."])
    blocks = _blocks(events)
    assert len(blocks) == 2
    assert blocks[0]["block_type"] == "PRIMARY_SOURCE"
    assert blocks[1]["block_type"] == "QUIZ"
    assert "Text." in _text(events)
    assert "End." in _text(events)
