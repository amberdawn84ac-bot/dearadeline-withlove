"""
SearchWitnesses Tool — Adeline's Auto-Search Capability

When Adeline hits a knowledge gap (ARCHIVE_SILENT from the Hippocampus),
she searches for her own Witnesses from verified primary-source archives.

Restricted domains:
  - archive.org   (Internet Archive)
  - gutenberg.org (Project Gutenberg — public domain texts)
  - archives.gov  (National Archives — US government primary sources)

Flow:
  1. Tavily search with domain restriction
  2. Scrape text from top results (httpx + BeautifulSoup)
  3. Embed scraped content (OpenAI text-embedding-3-small)
  4. Cosine similarity against the original query embedding
  5. If score >= 0.85 → VERIFIED Evidence + Neo4j (:Source) node linked to (:Lesson)
  6. If no source clears threshold → return None (RESEARCH_MISSION falls through)
"""
import os
import uuid
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
import numpy as np
import openai
from bs4 import BeautifulSoup

from app.schemas.api_models import (
    Evidence, EvidenceVerdict, WitnessCitation, TRUTH_THRESHOLD,
)
from app.connections.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

EMBED_MODEL       = "text-embedding-3-small"
TAVILY_URL        = "https://api.tavily.com/search"
ALLOWED_DOMAINS   = ["archive.org", "gutenberg.org", "archives.gov"]
MAX_CHUNK_CHARS   = 2000   # Characters to embed from scraped page
SCRAPE_TIMEOUT    = 20.0   # Seconds before giving up on a page load
SEARCH_TIMEOUT    = 15.0   # Seconds for Tavily API call

_DOMAIN_LABELS = {
    "archive.org":   "Internet Archive",
    "gutenberg.org": "Project Gutenberg",
    "archives.gov":  "National Archives",
}


@dataclass
class WitnessResult:
    """A primary source that cleared the 0.85 Witness Protocol threshold."""
    evidence: Evidence
    source_url: str
    title: str
    similarity_score: float


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return resp.data[0].embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def _domain_label(url: str) -> str:
    for domain, label in _DOMAIN_LABELS.items():
        if domain in url:
            return label
    return "Verified Archive"


async def _tavily_search(query: str) -> list[dict]:
    """Search Tavily restricted to approved primary-source archives."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning("[Researcher] TAVILY_API_KEY not set — skipping auto-search")
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "include_domains": ALLOWED_DOMAINS,
        "max_results": 3,
        "search_depth": "basic",
    }

    try:
        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT) as client:
            resp = await client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
            return resp.json().get("results", [])
    except Exception as e:
        logger.warning(f"[Researcher] Tavily search failed: {e}")
        return []


async def _scrape_text(url: str) -> str:
    """Fetch URL and extract readable plain text."""
    try:
        async with httpx.AsyncClient(
            timeout=SCRAPE_TIMEOUT,
            headers={"User-Agent": "DearAdeline/2.0 Educational Research Bot"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)[:MAX_CHUNK_CHARS]
    except Exception as e:
        logger.warning(f"[Researcher] Scrape failed for {url}: {e}")
        return ""


async def _link_source_to_lesson(
    lesson_id: str, url: str, title: str, score: float, track: str
) -> None:
    """
    Create a temporary (:Source) node in Neo4j and link it to the (:Lesson).
    Fire-and-forget: errors are logged but never surface to the student.
    """
    try:
        await neo4j_client.run(
            """
            MERGE (l:Lesson {id: $lesson_id})
            SET l.track = $track, l.updated_at = datetime()
            MERGE (s:Source {url: $url})
            SET s.title      = $title,
                s.similarity_score = $score,
                s.found_at   = datetime(),
                s.status     = "auto_found"
            MERGE (l)-[:USED_SOURCE]->(s)
            """,
            {
                "lesson_id": lesson_id,
                "track": track,
                "url": url,
                "title": title,
                "score": round(score, 4),
            },
        )
        logger.info(f"[Researcher] Neo4j Source node created — {url}")
    except Exception as e:
        logger.warning(f"[Researcher] Neo4j link failed (non-fatal): {e}")


# ── Public API ─────────────────────────────────────────────────────────────────

async def search_witnesses(
    topic: str,
    track: str,
    query_embedding: list[float],
    lesson_id: str,
) -> Optional[WitnessResult]:
    """
    Search approved archives for a primary source on `topic`.

    Returns a WitnessResult when a source scores >= 0.85 against the
    original lesson query embedding, or None if no qualifying source is found.

    Called by the orchestrator agents when Hippocampus returns ARCHIVE_SILENT.
    """
    logger.info(
        f"[Researcher] Searching for a Primary Source — "
        f"topic='{topic}' track={track}"
    )

    results = await _tavily_search(topic)
    if not results:
        logger.info("[Researcher] No archive results — knowledge gap persists")
        return None

    for result in results:
        url   = result.get("url", "")
        title = result.get("title", "Untitled Source")

        # Prefer Tavily's excerpt; scrape if too short
        excerpt = result.get("content", "")
        if len(excerpt) < 100:
            excerpt = await _scrape_text(url)
        if not excerpt:
            continue

        try:
            source_embedding = await _embed(excerpt)
        except Exception as e:
            logger.warning(f"[Researcher] Embedding failed for {url}: {e}")
            continue

        score = _cosine_similarity(query_embedding, source_embedding)
        logger.info(
            f"[Researcher] score={score:.3f} — '{title}' ({url})"
        )

        if score >= TRUTH_THRESHOLD:
            logger.info(
                f"[Researcher] ✓ WITNESS FOUND — '{title}' score={score:.3f}"
            )
            await _link_source_to_lesson(lesson_id, url, title, score, track)

            return WitnessResult(
                evidence=Evidence(
                    source_id=str(uuid.uuid4()),
                    source_title=title,
                    source_url=url,
                    witness_citation=WitnessCitation(
                        archive_name=_domain_label(url),
                    ),
                    similarity_score=min(score, 1.0),
                    verdict=EvidenceVerdict.VERIFIED,
                    chunk=excerpt[:1000],
                ),
                source_url=url,
                title=title,
                similarity_score=score,
            )

    logger.info("[Researcher] No sources cleared the 0.85 threshold — RESEARCH_MISSION")
    return None
