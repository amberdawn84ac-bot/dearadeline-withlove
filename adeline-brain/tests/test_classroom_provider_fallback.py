"""Provider failover regression: independent quotas, preserved JSON validation."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from app.api import classrooms as api


class Result(BaseModel):
    answer: int


def manager_with(response=None, error=None):
    client = MagicMock()
    if error is not None:
        client.chat.completions.create = AsyncMock(side_effect=error)
    else:
        client.chat.completions.create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=json.dumps(response)),
                )],
            ),
        )
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=False)
    return manager, client


def rate_error(code, seconds=60):
    response = httpx.Response(
        429, headers={"retry-after": str(seconds)},
        request=httpx.Request("POST", "https://provider.test"),
    )
    return openai.RateLimitError(
        "Quota exhausted", response=response, body={"error": {"code": code}}
    )


@pytest.mark.asyncio
async def test_gemini_then_openai_credit_exhaustion_uses_groq(monkeypatch):
    monkeypatch.setattr(api, "GEMINI_API_KEY", "gemini-test")
    monkeypatch.setattr(api, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(api, "OPENAI_API_KEY", "openai-test")
    monkeypatch.setattr(api, "GROQ_API_KEY", "groq-test")
    monkeypatch.setattr(api, "_provider_retry_at", 0)
    monkeypatch.setattr(api, "_fallback_retry_at", 0)
    monkeypatch.setattr(api, "_groq_retry_at", 0)
    primary, primary_client = manager_with(error=rate_error("RESOURCE_EXHAUSTED"))
    backup, backup_client = manager_with(error=rate_error("credit_balance_exhausted"))
    third, third_client = manager_with(response={"answer": 42})
    with patch("openai.AsyncOpenAI", side_effect=[primary, backup, third]):
        answer = await api.generate_json("Answer the question.", Result, {"question": "6*7"})
    assert answer.answer == 42
    primary_client.chat.completions.create.assert_awaited_once()
    backup_client.chat.completions.create.assert_awaited_once()
    third_client.chat.completions.create.assert_awaited_once()
    assert third_client.chat.completions.create.await_args.kwargs["response_format"] == {
        "type": "json_object"
    }
    assert api._fallback_retry_at > 0


@pytest.mark.asyncio
async def test_groq_can_run_without_openai_or_gemini(monkeypatch):
    monkeypatch.setattr(api, "GEMINI_API_KEY", "")
    monkeypatch.setattr(api, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(api, "OPENAI_API_KEY", "")
    monkeypatch.setattr(api, "GROQ_API_KEY", "groq-test")
    monkeypatch.setattr(api, "_groq_retry_at", 0)
    third, client = manager_with(response={"answer": 9})
    with patch("openai.AsyncOpenAI", return_value=third):
        result = await api.generate_json("Return JSON.", Result, {})
    assert result.answer == 9
    client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_all_exhausted_returns_retryable_503(monkeypatch):
    monkeypatch.setattr(api, "GEMINI_API_KEY", "gemini-test")
    monkeypatch.setattr(api, "GOOGLE_API_KEY", "")
    monkeypatch.setattr(api, "OPENAI_API_KEY", "openai-test")
    monkeypatch.setattr(api, "GROQ_API_KEY", "groq-test")
    monkeypatch.setattr(api, "_provider_retry_at", 0)
    monkeypatch.setattr(api, "_fallback_retry_at", 0)
    monkeypatch.setattr(api, "_groq_retry_at", 0)
    clients = [
        manager_with(error=rate_error("RESOURCE_EXHAUSTED"))[0],
        manager_with(error=rate_error("insufficient_quota"))[0],
        manager_with(error=rate_error("rate_limit_exceeded"))[0],
    ]
    with patch("openai.AsyncOpenAI", side_effect=clients):
        with pytest.raises(HTTPException) as exc:
            await api.generate_json("Return JSON.", Result, {})
    assert exc.value.status_code == 503
    assert "Retry-After" in exc.value.headers
