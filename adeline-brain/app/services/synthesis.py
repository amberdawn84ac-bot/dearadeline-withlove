"""Shared, non-curricular language-model client.

Lesson authorship must go through the canonical experience builder.  This
module exists only so conversational and other bounded features do not depend
on the retired specialist lesson orchestrator.
"""
from __future__ import annotations

import asyncio
import logging

from app.config import ADELINE_MODEL, GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL, GOOGLE_API_KEY

logger = logging.getLogger(__name__)


class SynthesisError(RuntimeError):
    pass


def _client():
    import openai

    api_key = GEMINI_API_KEY or GOOGLE_API_KEY
    if not api_key:
        raise SynthesisError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    model = ADELINE_MODEL if ADELINE_MODEL.lower().startswith("gemini") else GEMINI_MODEL
    return openai.AsyncOpenAI(api_key=api_key, base_url=GEMINI_BASE_URL), model


async def synthesize(system: str, user: str, max_tokens: int = 6000) -> str:
    """Return one complete, non-empty synthesis response, retrying once."""
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
