"""Shared language-model transport for Adeline's curricular intelligence.

Adeline's conversation is curricular: it teaches, notices learning in ordinary
life, connects that learning to the plan, and hands demonstrated work to the
portfolio/registrar flow. Canonical investigation authorship still goes through
the Canonical Experience Author; this transport simply keeps curricular chat
from depending on the retired lesson orchestrator.
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator

from app.config import ADELINE_MODEL, GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL, GOOGLE_API_KEY

logger = logging.getLogger(__name__)
_MAX_CONCURRENT_SYNTHESIS = max(1, int(os.getenv("AI_MAX_CONCURRENCY", "20")))
_synthesis_slots = asyncio.Semaphore(_MAX_CONCURRENT_SYNTHESIS)


class SynthesisError(RuntimeError):
    pass


def _client():
    import openai

    api_key = GEMINI_API_KEY or GOOGLE_API_KEY
    if not api_key:
        raise SynthesisError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    model = ADELINE_MODEL if ADELINE_MODEL.lower().startswith("gemini") else GEMINI_MODEL
    return openai.AsyncOpenAI(
        api_key=api_key,
        base_url=GEMINI_BASE_URL,
        timeout=45.0,
        max_retries=0,
    ), model


async def synthesize(system: str, user: str, max_tokens: int = 6000) -> str:
    """Run the caller's curriculum-aware system prompt and retry once."""
    try:
        await asyncio.wait_for(_synthesis_slots.acquire(), timeout=10.0)
    except asyncio.TimeoutError as exc:
        raise SynthesisError("The learning service is busy; please retry shortly") from exc
    try:
        client, model = _client()
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                )
                choice = response.choices[0]
                content = choice.message.content or ""
                finish_reason = getattr(choice, "finish_reason", None)
                if finish_reason and finish_reason != "stop":
                    raise SynthesisError(f"model stopped with finish_reason={finish_reason!r}")
                if not content.strip():
                    raise SynthesisError("model returned empty content")
                return content
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    logger.warning("Synthesis failed (%s); retrying", exc)
                    await asyncio.sleep(1)
        raise SynthesisError(f"model unavailable after two attempts: {last_error}")
    finally:
        _synthesis_slots.release()


async def stream_synthesis(system: str, user: str, max_tokens: int = 2000) -> AsyncIterator[str]:
    """Stream model deltas while keeping the same concurrency and timeout policy."""
    try:
        await asyncio.wait_for(_synthesis_slots.acquire(), timeout=10.0)
    except asyncio.TimeoutError as exc:
        raise SynthesisError("The learning service is busy; please retry shortly") from exc
    try:
        client, model = _client()
        stream = await client.chat.completions.create(
            model=model, max_tokens=max_tokens, stream=True,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        received = False
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                received = True
                yield delta
        if not received:
            raise SynthesisError("model returned no streamed content")
    finally:
        _synthesis_slots.release()
