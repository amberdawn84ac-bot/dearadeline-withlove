"""
Stream parser — splits Adeline's streamed response into text and block events.

Handles <BLOCK>...</BLOCK> tags that may span multiple chunks.
Yields dicts suitable for direct SSE emission:
  {"type": "text",  "delta": "..."}
  {"type": "block", "block": {...}}

Text events are emitted as they arrive — multiple small deltas are intentional
and create the live typing feel in the UI. Never buffer text to merge it.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)

_BLOCK_OPEN  = "<BLOCK>"
_BLOCK_CLOSE = "</BLOCK>"
_OPEN_LEN    = len(_BLOCK_OPEN)
_CLOSE_LEN   = len(_BLOCK_CLOSE)


async def parse_stream(
    chunks: AsyncIterator[str],
) -> AsyncIterator[dict]:
    """
    Async generator — consumes a stream of text chunks and yields
    {"type": "text", "delta": str} and {"type": "block", "block": dict} events.

    Safe tail: keeps the last (_OPEN_LEN - 1) chars buffered when not inside
    a block tag, so partial opening tags are never emitted prematurely.
    Multiple text events per chunk are normal — callers should append deltas.
    """
    buffer   = ""
    in_block = False

    async for chunk in chunks:
        buffer += chunk

        while True:
            if not in_block:
                tag_start = buffer.find(_BLOCK_OPEN)
                if tag_start == -1:
                    # No block tag — emit everything except the safe tail
                    safe_end = max(0, len(buffer) - (_OPEN_LEN - 1))
                    if safe_end > 0:
                        yield {"type": "text", "delta": buffer[:safe_end]}
                        buffer = buffer[safe_end:]
                    break
                if tag_start > 0:
                    yield {"type": "text", "delta": buffer[:tag_start]}
                buffer   = buffer[tag_start + _OPEN_LEN:]
                in_block = True

            else:
                tag_end = buffer.find(_BLOCK_CLOSE)
                if tag_end == -1:
                    break
                block_content = buffer[:tag_end].strip()
                buffer        = buffer[tag_end + _CLOSE_LEN:]
                in_block      = False
                try:
                    yield {"type": "block", "block": json.loads(block_content)}
                except json.JSONDecodeError:
                    logger.warning("[stream_parser] Malformed block JSON — emitting as text")
                    yield {"type": "text", "delta": f"{_BLOCK_OPEN}{block_content}{_BLOCK_CLOSE}"}

    # Flush remainder
    if buffer.strip() and not in_block:
        yield {"type": "text", "delta": buffer}
