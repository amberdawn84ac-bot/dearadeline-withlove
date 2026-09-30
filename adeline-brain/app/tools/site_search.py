"""Site-scoped page search for offline Hippocampus seed scripts.

The live researcher already uses DuckDuckGo. These seed scripts used to call
Tavily and would no-op without a key that production does not have.
"""
from __future__ import annotations

import asyncio
import re

import httpx


async def search_documents(query: str, domain: str | None = None, max_results: int = 3) -> list[dict]:
    """Return title, url, and page text. Snippets shorter than a real paragraph are fetched."""
    search_query = f"{query} site:{domain}" if domain else query

    def _search() -> list[dict]:
        from duckduckgo_search import DDGS

        rows = list(DDGS().text(search_query, max_results=max_results))
        found = []
        for row in rows:
            url = row.get("href") or ""
            if not url:
                continue
            if domain and domain not in url:
                continue
            found.append({
                "title": row.get("title") or "",
                "url": url,
                "content": row.get("body") or "",
            })
        return found

    results = await asyncio.get_event_loop().run_in_executor(None, _search)
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for result in results:
            if len(result["content"]) >= 400:
                continue
            try:
                response = await client.get(result["url"], headers={"User-Agent": "DearAdelineSeed/1.0"})
                if response.status_code != 200 or "html" not in response.headers.get("content-type", "text/html"):
                    continue
                text = _html_to_text(response.text)
                if len(text) > len(result["content"]):
                    result["content"] = text[:8000]
            except Exception:
                continue
    return results


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&", "&", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
