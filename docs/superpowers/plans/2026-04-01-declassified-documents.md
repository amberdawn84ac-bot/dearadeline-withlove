# Declassified Government Documents Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate declassified government documents (NARA, CIA FOIA, FBI Vault, Congressional Record, Federal Register, DNSA) as first-class primary sources in Hippocampus, queried in parallel with all other evidence at the 0.82 Witness Protocol threshold. When no sources clear 0.82, trigger a deep web search across government archives that acquires and embeds new primary documents — making the system self-improving.

**Architecture:** Hippocampus stores all source types (including `DECLASSIFIED_GOV`) in the same `hippocampus_documents` table with a new `source_type` column. `search_witnesses()` queries all source types in a single unified search at 0.82+. When nothing clears the threshold, a deep web search hunts across NARA, CIA FOIA, FBI Vault, Congressional Record, archive.org, and DNSA — found documents are embedded and persisted to Hippocampus immediately, then returned to the student. If the deep search also fails, the student gets a RESEARCH_MISSION.

**Tech Stack:** pgvector (Hippocampus), Tavily (deep web search), OpenAI text-embedding-3-small, Pydantic + FastAPI (adeline-brain), React + TypeScript (adeline-ui), NARA/CIA/FBI APIs.

---

## Search Flow (Revised)

```
1. Unified Hippocampus query (all source types at >= 0.82)
   └─ Found? → Return results ranked by similarity. Done.
   └─ Empty? → Step 2

2. Deep web search for primary documents
   Search in parallel:
     - NARA catalog (archives.gov)
     - CIA FOIA Reading Room
     - FBI Vault
     - Congressional Record (congress.gov)
     - Federal Register (federalregister.gov)
     - archive.org
     - DNSA (nsarchive.gwu.edu)
   For each result:
     - Scrape text
     - Embed with text-embedding-3-small
     - Cosine similarity against query embedding
     - If >= 0.82 → Persist to Hippocampus + return as VERIFIED evidence
   └─ Found? → Return newly acquired results. Done.
   └─ Empty? → Step 3

3. RESEARCH_MISSION — student goes and finds it themselves
```

---

### Task 1: Add `source_type` Column to HippocampusDocument

**Files:**
- Modify: `adeline-brain/app/connections/pgvector_client.py`
- Modify: `adeline-brain/app/schemas/api_models.py`
- Create: `adeline-brain/tests/test_hippocampus_source_type.py`

- [ ] **Step 1: Write failing test for source_type filtering**

Create `adeline-brain/tests/test_hippocampus_source_type.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.connections.pgvector_client import HippocampusDocument


def test_hippocampus_document_has_source_type():
    """HippocampusDocument model must have a source_type column."""
    columns = {c.name for c in HippocampusDocument.__table__.columns}
    assert "source_type" in columns, "HippocampusDocument missing source_type column"


def test_hippocampus_document_source_type_default():
    """source_type should default to PRIMARY_SOURCE for backward compat."""
    doc = HippocampusDocument(
        source_title="Test",
        source_url="https://example.com",
        track="TRUTH_HISTORY",
        chunk="test chunk",
        embedding=[0.1] * 1536,
    )
    assert doc.source_type == "PRIMARY_SOURCE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adeline-brain && python -m pytest tests/test_hippocampus_source_type.py -v`

Expected: FAIL — `AssertionError: HippocampusDocument missing source_type column`

- [ ] **Step 3: Add SourceType enum to api_models.py**

Add to `adeline-brain/app/schemas/api_models.py` after the `EvidenceVerdict` enum:

```python
class SourceType(str, Enum):
    """What kind of archive this evidence came from."""
    PRIMARY_SOURCE    = "PRIMARY_SOURCE"
    DECLASSIFIED_GOV  = "DECLASSIFIED_GOV"
    ARCHIVE_ORG       = "ARCHIVE_ORG"
    ACADEMIC_JOURNAL  = "ACADEMIC_JOURNAL"
    PERSONAL_COLLECTION = "PERSONAL_COLLECTION"

SOURCE_TYPE_LABELS = {
    "PRIMARY_SOURCE":      "Primary Source",
    "DECLASSIFIED_GOV":    "Declassified Document",
    "ARCHIVE_ORG":         "Archive.org",
    "ACADEMIC_JOURNAL":    "Academic Journal",
    "PERSONAL_COLLECTION": "Personal Collection",
}

DECLASSIFIED_COLLECTIONS = {
    "NARA":                "https://catalog.archives.gov/search",
    "CIA_FOIA":            "https://www.cia.gov/information-freedom/records-available-online/",
    "FBI_VAULT":           "https://vault.fbi.gov/",
    "CONGRESSIONAL_RECORD":"https://www.congress.gov/congressional-record/",
    "FEDERAL_REGISTER":    "https://www.federalregister.gov/",
    "DNSA":                "https://nsarchive.gwu.edu/",
}
```

- [ ] **Step 4: Add `source_type` column to HippocampusDocument**

Edit `adeline-brain/app/connections/pgvector_client.py`. Add `source_type` column to `HippocampusDocument`:

```python
class HippocampusDocument(Base):
    """
    A verified source document chunk stored with its embedding vector.
    This is what the Witness Protocol searches against.
    """
    __tablename__ = "hippocampus_documents"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_title  = Column(String, nullable=False)
    source_url    = Column(String, nullable=False, default="")
    track         = Column(String, nullable=False)
    chunk         = Column(String, nullable=False)
    embedding     = Column(Vector(EMBEDDING_DIM), nullable=False)
    source_type   = Column(String, nullable=False, default="PRIMARY_SOURCE")  # ← NEW
    # WitnessCitation fields
    citation_author       = Column(String, nullable=False, default="")
    citation_year         = Column(Integer, nullable=True)
    citation_archive_name = Column(String, nullable=False, default="")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 5: Update `upsert_document()` to accept `source_type`**

Edit the `upsert_document` method in `HippocampusClient`:

```python
async def upsert_document(
    self,
    source_title: str,
    track: str,
    chunk: str,
    embedding: list[float],
    citation_author: str = "",
    citation_year: Optional[int] = None,
    citation_archive_name: str = "",
    source_url: str = "",
    source_type: str = "PRIMARY_SOURCE",  # ← NEW
) -> str:
    """Insert a verified source document chunk with its embedding."""
    async with self._session_factory() as session:
        doc = HippocampusDocument(
            source_title=source_title,
            source_url=source_url,
            track=track,
            chunk=chunk,
            embedding=embedding,
            source_type=source_type,  # ← NEW
            citation_author=citation_author,
            citation_year=citation_year,
            citation_archive_name=citation_archive_name,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return str(doc.id)
```

- [ ] **Step 6: Update `similarity_search()` to return `source_type`**

Edit the `similarity_search` method to include `source_type` in its SELECT and return:

```python
async def similarity_search(
    self, query_embedding: list[float], track: str, top_k: int = 5
) -> list[dict]:
    """
    Cosine similarity search against the Hippocampus corpus.
    Returns chunks sorted by similarity (highest first).
    Queries ALL source types — declassified docs are first-class.
    """
    async with self._session_factory() as session:
        result = await session.execute(
            text("""
                SELECT
                    id::text,
                    source_title,
                    source_url,
                    chunk,
                    source_type,
                    citation_author,
                    citation_year,
                    citation_archive_name,
                    1 - (embedding <=> CAST(:embedding AS vector)) AS similarity_score
                FROM hippocampus_documents
                WHERE track = :track
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            {
                "embedding": str(query_embedding),
                "track": track,
                "top_k": top_k,
            },
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd adeline-brain && python -m pytest tests/test_hippocampus_source_type.py -v`

Expected: PASS — both tests green

- [ ] **Step 8: Commit**

```bash
git add adeline-brain/app/connections/pgvector_client.py adeline-brain/app/schemas/api_models.py adeline-brain/tests/test_hippocampus_source_type.py
git commit -m "feat: Add source_type column to HippocampusDocument for declassified gov docs"
```

---

### Task 2: Add SourceType to TypeScript Evidence Schema

**Files:**
- Modify: `adeline-core/src/schemas/evidence.ts`

- [ ] **Step 1: Add SourceType enum and DECLASSIFIED_COLLECTIONS to evidence.ts**

Edit `adeline-core/src/schemas/evidence.ts` to add after the `EvidenceSchema` definition:

```typescript
/**
 * What kind of archive this evidence came from.
 * Used for UI badging — does NOT affect authority or Witness Protocol threshold.
 */
export enum SourceType {
  PRIMARY_SOURCE = "PRIMARY_SOURCE",
  DECLASSIFIED_GOV = "DECLASSIFIED_GOV",
  ARCHIVE_ORG = "ARCHIVE_ORG",
  ACADEMIC_JOURNAL = "ACADEMIC_JOURNAL",
  PERSONAL_COLLECTION = "PERSONAL_COLLECTION",
}

export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  [SourceType.PRIMARY_SOURCE]: "Primary Source",
  [SourceType.DECLASSIFIED_GOV]: "Declassified Document",
  [SourceType.ARCHIVE_ORG]: "Archive.org",
  [SourceType.ACADEMIC_JOURNAL]: "Academic Journal",
  [SourceType.PERSONAL_COLLECTION]: "Personal Collection",
};

/** Government declassified document collections for deep web search. */
export const DECLASSIFIED_COLLECTIONS = {
  NARA: "https://catalog.archives.gov/search",
  CIA_FOIA: "https://www.cia.gov/information-freedom/records-available-online/",
  FBI_VAULT: "https://vault.fbi.gov/",
  CONGRESSIONAL_RECORD: "https://www.congress.gov/congressional-record/",
  FEDERAL_REGISTER: "https://www.federalregister.gov/",
  DNSA: "https://nsarchive.gwu.edu/",
} as const;
```

- [ ] **Step 2: Build adeline-core to verify types compile**

Run: `cd adeline-core && pnpm build`

Expected: Build succeeds with no type errors

- [ ] **Step 3: Commit**

```bash
git add adeline-core/src/schemas/evidence.ts
git commit -m "feat: Add SourceType enum and DECLASSIFIED_COLLECTIONS to evidence schema"
```

---

### Task 3: Rewrite SearchWitnesses with Deep Web Search Acquisition

**Files:**
- Modify: `adeline-brain/app/tools/researcher.py`
- Create: `adeline-brain/tests/test_researcher_deep_search.py`

This is the critical task. The current `search_witnesses()` only searches Tavily when the orchestrator calls it after an ARCHIVE_SILENT verdict. The revised version:
1. Gets called the same way (topic, track, query_embedding, lesson_id)
2. First queries Hippocampus for ALL source types at 0.82+
3. If Hippocampus is empty, runs a deep web search across government archives + archive.org
4. Found documents are **embedded and persisted to Hippocampus** (self-improving)
5. Returns WitnessResult or None (RESEARCH_MISSION)

- [ ] **Step 1: Write failing tests for deep search behavior**

Create `adeline-brain/tests/test_researcher_deep_search.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tools.researcher import (
    search_witnesses,
    _deep_search_primary_sources,
    DEEP_SEARCH_DOMAINS,
)


def test_deep_search_domains_include_gov_archives():
    """Deep search must include all declassified source domains."""
    assert "archives.gov" in DEEP_SEARCH_DOMAINS
    assert "cia.gov" in DEEP_SEARCH_DOMAINS
    assert "vault.fbi.gov" in DEEP_SEARCH_DOMAINS
    assert "congress.gov" in DEEP_SEARCH_DOMAINS
    assert "federalregister.gov" in DEEP_SEARCH_DOMAINS
    assert "nsarchive.gwu.edu" in DEEP_SEARCH_DOMAINS
    assert "archive.org" in DEEP_SEARCH_DOMAINS
    assert "gutenberg.org" in DEEP_SEARCH_DOMAINS


@pytest.mark.asyncio
@patch("app.tools.researcher._embed")
@patch("app.tools.researcher._tavily_search")
@patch("app.tools.researcher._scrape_text")
async def test_deep_search_persists_to_hippocampus(
    mock_scrape, mock_tavily, mock_embed
):
    """
    When deep search finds a document that clears 0.82,
    it must persist the document to Hippocampus before returning.
    """
    mock_tavily.return_value = [
        {
            "url": "https://catalog.archives.gov/id/2723456",
            "title": "Civil Rights Act - 1964",
            "content": "Full text of the Civil Rights Act legislative history...",
        }
    ]
    mock_scrape.return_value = "Full text of the Civil Rights Act legislative history..."
    # Return a vector that will produce high cosine similarity
    mock_embed.return_value = [0.9] * 1536

    with patch("app.tools.researcher.hippocampus") as mock_hippo:
        mock_hippo.upsert_document = AsyncMock(return_value="new-doc-id")

        result = await _deep_search_primary_sources(
            topic="civil rights act 1964",
            track="TRUTH_HISTORY",
            query_embedding=[0.9] * 1536,
            lesson_id="lesson-123",
        )

        # Must have called upsert_document to persist the found source
        mock_hippo.upsert_document.assert_called_once()
        call_kwargs = mock_hippo.upsert_document.call_args
        assert call_kwargs[1]["source_type"] in ("DECLASSIFIED_GOV", "ARCHIVE_ORG", "PRIMARY_SOURCE")


@pytest.mark.asyncio
@patch("app.tools.researcher.hippocampus")
async def test_search_witnesses_queries_hippocampus_first(mock_hippo):
    """
    search_witnesses must query Hippocampus for ALL source types first,
    before attempting any deep web search.
    """
    # Hippocampus returns a high-similarity result
    mock_hippo.similarity_search = AsyncMock(return_value=[
        {
            "id": "existing-doc-id",
            "source_title": "NARA Declassified Doc",
            "source_url": "https://archives.gov/doc/123",
            "chunk": "Verified declassified content...",
            "source_type": "DECLASSIFIED_GOV",
            "citation_author": "NARA",
            "citation_year": 1964,
            "citation_archive_name": "NARA",
            "similarity_score": 0.88,
        }
    ])

    result = await search_witnesses(
        topic="civil rights act 1964",
        track="TRUTH_HISTORY",
        query_embedding=[0.9] * 1536,
        lesson_id="lesson-123",
    )

    # Hippocampus was queried
    mock_hippo.similarity_search.assert_called_once()
    # Result came from Hippocampus, not deep search
    assert result is not None
    assert result.evidence.verdict.value == "VERIFIED"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd adeline-brain && python -m pytest tests/test_researcher_deep_search.py -v`

Expected: FAIL — `ImportError: cannot import name '_deep_search_primary_sources'` and `DEEP_SEARCH_DOMAINS`

- [ ] **Step 3: Rewrite researcher.py**

Replace `adeline-brain/app/tools/researcher.py` with:

```python
"""
SearchWitnesses Tool — Adeline's Auto-Search & Acquisition Capability

Search flow:
  1. Query Hippocampus for ALL source types (PRIMARY_SOURCE, DECLASSIFIED_GOV, etc.)
     at >= 0.82 cosine similarity. Declassified docs are first-class, not fallback.
  2. If Hippocampus is empty: deep web search across government archives and
     public domain sources. Found documents are embedded and PERSISTED to
     Hippocampus — the system gets smarter with every miss.
  3. If deep search also fails: return None → RESEARCH_MISSION (student finds it).

Restricted domains for deep search:
  - archives.gov      (National Archives / NARA)
  - cia.gov           (CIA FOIA Reading Room)
  - vault.fbi.gov     (FBI Vault)
  - congress.gov      (Congressional Record)
  - federalregister.gov (Federal Register)
  - nsarchive.gwu.edu (Digital National Security Archive)
  - archive.org       (Internet Archive)
  - gutenberg.org     (Project Gutenberg)
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
from app.connections.pgvector_client import hippocampus

logger = logging.getLogger(__name__)

EMBED_MODEL       = "text-embedding-3-small"
TAVILY_URL        = "https://api.tavily.com/search"
MAX_CHUNK_CHARS   = 2000
SCRAPE_TIMEOUT    = 20.0
SEARCH_TIMEOUT    = 15.0

# Deep search: ALL approved primary-source domains
DEEP_SEARCH_DOMAINS = [
    "archives.gov",
    "cia.gov",
    "vault.fbi.gov",
    "congress.gov",
    "federalregister.gov",
    "nsarchive.gwu.edu",
    "archive.org",
    "gutenberg.org",
]

# Map domains to source_type for Hippocampus storage
_DOMAIN_SOURCE_TYPE = {
    "archives.gov":        "DECLASSIFIED_GOV",
    "cia.gov":             "DECLASSIFIED_GOV",
    "vault.fbi.gov":       "DECLASSIFIED_GOV",
    "congress.gov":        "DECLASSIFIED_GOV",
    "federalregister.gov": "DECLASSIFIED_GOV",
    "nsarchive.gwu.edu":   "DECLASSIFIED_GOV",
    "archive.org":         "ARCHIVE_ORG",
    "gutenberg.org":       "ARCHIVE_ORG",
}

_DOMAIN_LABELS = {
    "archives.gov":        "National Archives (NARA)",
    "cia.gov":             "CIA FOIA Reading Room",
    "vault.fbi.gov":       "FBI Vault",
    "congress.gov":        "Congressional Record",
    "federalregister.gov": "Federal Register",
    "nsarchive.gwu.edu":   "Digital National Security Archive",
    "archive.org":         "Internet Archive",
    "gutenberg.org":       "Project Gutenberg",
}


@dataclass
class WitnessResult:
    """A primary source that cleared the Witness Protocol threshold."""
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


def _domain_source_type(url: str) -> str:
    for domain, source_type in _DOMAIN_SOURCE_TYPE.items():
        if domain in url:
            return source_type
    return "PRIMARY_SOURCE"


async def _tavily_search(query: str, domains: list[str] | None = None) -> list[dict]:
    """Search Tavily restricted to specified primary-source domains."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning("[Researcher] TAVILY_API_KEY not set — skipping search")
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "include_domains": domains or DEEP_SEARCH_DOMAINS,
        "max_results": 5,
        "search_depth": "advanced",  # deep search uses advanced depth
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
    Create a (:Source) node in Neo4j and link it to the (:Lesson).
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


# ── Deep Web Search & Acquisition ─────────────────────────────────────────────

async def _deep_search_primary_sources(
    topic: str,
    track: str,
    query_embedding: list[float],
    lesson_id: str,
) -> Optional[WitnessResult]:
    """
    Deep web search across government archives and public domain sources.
    When a source clears the 0.82 threshold:
      1. Persist it to Hippocampus (so future queries find it)
      2. Link it to the lesson in Neo4j
      3. Return it as a WitnessResult

    This makes the system self-improving — every miss triggers a hunt,
    and every successful hunt permanently enriches the corpus.
    """
    logger.info(
        f"[Researcher] Deep web search — topic='{topic}' track={track} "
        f"domains={len(DEEP_SEARCH_DOMAINS)}"
    )

    results = await _tavily_search(topic, domains=DEEP_SEARCH_DOMAINS)
    if not results:
        logger.info("[Researcher] Deep search returned no results")
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
        logger.info(f"[Researcher] score={score:.3f} — '{title}' ({url})")

        if score >= TRUTH_THRESHOLD:
            source_type = _domain_source_type(url)
            archive_name = _domain_label(url)

            logger.info(
                f"[Researcher] WITNESS ACQUIRED — '{title}' "
                f"score={score:.3f} type={source_type}"
            )

            # ── Persist to Hippocampus (self-improving) ──────────────
            try:
                doc_id = await hippocampus.upsert_document(
                    source_title=title,
                    track=track,
                    chunk=excerpt[:MAX_CHUNK_CHARS],
                    embedding=source_embedding,
                    source_type=source_type,
                    citation_author=archive_name,
                    citation_archive_name=archive_name,
                    source_url=url,
                )
                logger.info(
                    f"[Researcher] Persisted to Hippocampus — "
                    f"doc_id={doc_id} source_type={source_type}"
                )
            except Exception as e:
                logger.warning(f"[Researcher] Hippocampus persist failed (non-fatal): {e}")

            # ── Link to lesson in Neo4j ──────────────────────────────
            await _link_source_to_lesson(lesson_id, url, title, score, track)

            return WitnessResult(
                evidence=Evidence(
                    source_id=str(uuid.uuid4()),
                    source_title=title,
                    source_url=url,
                    witness_citation=WitnessCitation(
                        archive_name=archive_name,
                    ),
                    similarity_score=min(score, 1.0),
                    verdict=EvidenceVerdict.VERIFIED,
                    chunk=excerpt[:1000],
                ),
                source_url=url,
                title=title,
                similarity_score=score,
            )

    logger.info("[Researcher] Deep search — no sources cleared threshold")
    return None


# ── Public API ─────────────────────────────────────────────────────────────────

async def search_witnesses(
    topic: str,
    track: str,
    query_embedding: list[float],
    lesson_id: str,
) -> Optional[WitnessResult]:
    """
    Search for a primary source on `topic`.

    Flow:
      1. Query Hippocampus (all source types, including DECLASSIFIED_GOV) at >= 0.82
      2. If empty: deep web search across government archives → persist found docs
      3. If still empty: return None → RESEARCH_MISSION

    Called by orchestrator agents when Hippocampus returns ARCHIVE_SILENT.
    """
    logger.info(
        f"[Researcher] Searching — topic='{topic}' track={track}"
    )

    # ── Step 1: Unified Hippocampus query (all source types) ─────────
    hippocampus_results = await hippocampus.similarity_search(
        query_embedding=query_embedding,
        track=track,
        top_k=5,
    )

    # Check if any result clears the threshold
    for row in hippocampus_results:
        score = row.get("similarity_score", 0.0)
        if score >= TRUTH_THRESHOLD:
            title = row["source_title"]
            url   = row.get("source_url", "")
            source_type = row.get("source_type", "PRIMARY_SOURCE")

            logger.info(
                f"[Researcher] HIPPOCAMPUS HIT — '{title}' "
                f"score={score:.3f} type={source_type}"
            )
            await _link_source_to_lesson(lesson_id, url, title, score, track)

            return WitnessResult(
                evidence=Evidence(
                    source_id=row.get("id", str(uuid.uuid4())),
                    source_title=title,
                    source_url=url,
                    witness_citation=WitnessCitation(
                        author=row.get("citation_author", ""),
                        year=row.get("citation_year"),
                        archive_name=row.get("citation_archive_name", ""),
                    ),
                    similarity_score=min(score, 1.0),
                    verdict=EvidenceVerdict.VERIFIED,
                    chunk=row.get("chunk", ""),
                ),
                source_url=url,
                title=title,
                similarity_score=score,
            )

    # ── Step 2: Deep web search + acquire ────────────────────────────
    logger.info("[Researcher] Hippocampus empty — launching deep web search")
    result = await _deep_search_primary_sources(
        topic=topic,
        track=track,
        query_embedding=query_embedding,
        lesson_id=lesson_id,
    )
    if result:
        return result

    # ── Step 3: Nothing found — RESEARCH_MISSION ─────────────────────
    logger.info("[Researcher] No sources found — RESEARCH_MISSION")
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd adeline-brain && python -m pytest tests/test_researcher_deep_search.py -v`

Expected: All 3 tests pass

- [ ] **Step 5: Run existing researcher tests to check backward compat**

Run: `cd adeline-brain && python -m pytest tests/ -k researcher -v`

Expected: All researcher tests pass

- [ ] **Step 6: Commit**

```bash
git add adeline-brain/app/tools/researcher.py adeline-brain/tests/test_researcher_deep_search.py
git commit -m "feat: SearchWitnesses queries all source types + deep web search acquisition"
```

---

### Task 4: Create DeclassifiedDocument Parser for Seed Scripts

**Files:**
- Create: `adeline-brain/scripts/utils/__init__.py`
- Create: `adeline-brain/scripts/utils/document_parser.py`
- Create: `adeline-brain/tests/test_document_parser.py`

- [ ] **Step 1: Write failing test for DeclassifiedDocument**

Create `adeline-brain/tests/test_document_parser.py`:

```python
import pytest
from scripts.utils.document_parser import DeclassifiedDocument


def test_declassified_document_creation():
    """Test DeclassifiedDocument initialization."""
    doc = DeclassifiedDocument(
        doc_id="2723456",
        title="Civil Rights Act Legislative History - 1964",
        body="Congress debates voting rights amendments...",
        source_collection="NARA",
        citation_author="U.S. Congress",
        citation_year=1964,
        source_url="https://catalog.archives.gov/id/2723456",
    )
    assert doc.doc_id == "2723456"
    assert doc.title == "Civil Rights Act Legislative History - 1964"
    assert doc.source_collection == "NARA"


def test_declassified_document_to_hippocampus_kwargs():
    """Test serialization to kwargs for hippocampus.upsert_document()."""
    doc = DeclassifiedDocument(
        doc_id="12345",
        title="MKUltra Program Overview",
        body="Central Intelligence Agency program...",
        source_collection="CIA_FOIA",
        citation_author="CIA",
        citation_year=1972,
        source_url="https://www.cia.gov/readingroom/document/12345",
    )
    kwargs = doc.to_hippocampus_kwargs(
        track="TRUTH_HISTORY",
        embedding=[0.1] * 1536,
    )
    assert kwargs["source_type"] == "DECLASSIFIED_GOV"
    assert kwargs["source_title"] == "MKUltra Program Overview"
    assert kwargs["citation_author"] == "CIA"
    assert kwargs["citation_archive_name"] == "CIA FOIA"
    assert kwargs["track"] == "TRUTH_HISTORY"
    assert len(kwargs["embedding"]) == 1536
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd adeline-brain && python -m pytest tests/test_document_parser.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create the parser module**

Create `adeline-brain/scripts/utils/__init__.py` (empty file).

Create `adeline-brain/scripts/utils/document_parser.py`:

```python
"""
DeclassifiedDocument — data class for ingesting government documents into Hippocampus.
Used by seed scripts to batch-embed declassified docs from NARA, CIA FOIA, FBI Vault, etc.
"""
from dataclasses import dataclass
from typing import Optional

# Map collection names to citation archive labels
_COLLECTION_LABELS = {
    "NARA":                "National Archives (NARA)",
    "CIA_FOIA":            "CIA FOIA",
    "FBI_VAULT":           "FBI Vault",
    "CONGRESSIONAL_RECORD":"Congressional Record",
    "FEDERAL_REGISTER":    "Federal Register",
    "DNSA":                "Digital National Security Archive",
}


@dataclass
class DeclassifiedDocument:
    """Represents a declassified government document for Hippocampus ingestion."""
    doc_id: str
    title: str
    body: str
    source_collection: str  # NARA, CIA_FOIA, FBI_VAULT, etc.
    citation_author: str
    citation_year: int
    source_url: str
    citation_archive_name: Optional[str] = None

    def __post_init__(self):
        if not self.citation_archive_name:
            self.citation_archive_name = _COLLECTION_LABELS.get(
                self.source_collection, self.source_collection
            )

    def to_hippocampus_kwargs(self, track: str, embedding: list[float]) -> dict:
        """
        Serialize to keyword arguments for hippocampus.upsert_document().
        All declassified docs get source_type="DECLASSIFIED_GOV".
        """
        return {
            "source_title": self.title,
            "track": track,
            "chunk": self.body[:2000],
            "embedding": embedding,
            "source_type": "DECLASSIFIED_GOV",
            "citation_author": self.citation_author,
            "citation_year": self.citation_year,
            "citation_archive_name": self.citation_archive_name,
            "source_url": self.source_url,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd adeline-brain && python -m pytest tests/test_document_parser.py -v`

Expected: PASS — both tests green

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/scripts/utils/__init__.py adeline-brain/scripts/utils/document_parser.py adeline-brain/tests/test_document_parser.py
git commit -m "feat: Add DeclassifiedDocument parser for seed scripts"
```

---

### Task 5: Create Seed Scripts for NARA, CIA FOIA, FBI Vault

**Files:**
- Create: `adeline-brain/scripts/seed_declassified_nara.py`
- Create: `adeline-brain/scripts/seed_declassified_cia.py`
- Create: `adeline-brain/scripts/seed_declassified_fbi.py`
- Create: `adeline-brain/scripts/seed_declassified_all.py`

- [ ] **Step 1: Create NARA seed script**

Create `adeline-brain/scripts/seed_declassified_nara.py`:

```python
"""
Seed NARA declassified documents into Hippocampus.
Uses the NARA Catalog API: https://catalog.archives.gov/api/v1/
"""
import asyncio
import os
import logging

import httpx
import openai

from scripts.utils.document_parser import DeclassifiedDocument
from app.connections.pgvector_client import hippocampus

logger = logging.getLogger(__name__)

NARA_API = "https://catalog.archives.gov/api/v1/"
EMBED_MODEL = "text-embedding-3-small"

# Sample NAIDs for initial seeding — civil rights, justice, government history
SEED_NAIDS = [
    # Civil Rights Act records
    "299868",    # Civil Rights Act of 1964
    "595381",    # Voting Rights Act of 1965
    # Constitutional amendments
    "1408913",   # 13th Amendment
    "1408914",   # 14th Amendment
    "1408915",   # 15th Amendment
    # Executive orders
    "304124",    # Executive Order 9981 (desegregation of military)
]

# Which tracks these documents support
NARA_TRACKS = ["TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "GOVERNMENT_ECONOMICS"]


async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return resp.data[0].embedding


async def fetch_nara_document(naid: str) -> DeclassifiedDocument | None:
    """Fetch a NARA document by NAID from the catalog API."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{NARA_API}?naIds={naid}")
            resp.raise_for_status()
            data = resp.json()

        results = data.get("opaResponse", {}).get("results", {}).get("result", [])
        if not results:
            logger.warning(f"[NARA] No result for NAID {naid}")
            return None

        record = results[0] if isinstance(results, list) else results
        desc = record.get("description", {}).get("item", {})
        if not desc:
            desc = record.get("description", {}).get("fileUnit", {})

        title = desc.get("title", f"NARA Document {naid}")
        scope_note = desc.get("scopeAndContentNote", "")
        production_date = desc.get("productionDateArray", {})
        year_str = production_date.get("proposableQualifiableDate", {}).get("year", "")

        body = scope_note or title
        year = int(year_str) if year_str and year_str.isdigit() else 0

        return DeclassifiedDocument(
            doc_id=naid,
            title=title,
            body=body,
            source_collection="NARA",
            citation_author="National Archives",
            citation_year=year,
            source_url=f"https://catalog.archives.gov/id/{naid}",
        )
    except Exception as e:
        logger.warning(f"[NARA] Failed to fetch NAID {naid}: {e}")
        return None


async def seed_nara_documents(
    naids: list[str] | None = None,
    tracks: list[str] | None = None,
):
    """Seed NARA documents into Hippocampus for specified tracks."""
    naids = naids or SEED_NAIDS
    tracks = tracks or NARA_TRACKS

    await hippocampus.connect()
    seeded = 0

    for naid in naids:
        doc = await fetch_nara_document(naid)
        if not doc:
            continue

        try:
            embedding = await _embed(doc.body)
        except Exception as e:
            logger.warning(f"[NARA] Embedding failed for {naid}: {e}")
            continue

        # Seed into each relevant track
        for track in tracks:
            kwargs = doc.to_hippocampus_kwargs(track=track, embedding=embedding)
            doc_id = await hippocampus.upsert_document(**kwargs)
            logger.info(f"[NARA] Seeded {naid} → {track} (doc_id={doc_id})")
            seeded += 1

    logger.info(f"[NARA] Done — seeded {seeded} document-track pairs")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_nara_documents())
```

- [ ] **Step 2: Create CIA FOIA seed script**

Create `adeline-brain/scripts/seed_declassified_cia.py`:

```python
"""
Seed CIA FOIA Reading Room documents into Hippocampus.
CIA docs are typically PDFs — we use Tavily to find and extract them.
"""
import asyncio
import os
import logging

import httpx
import openai
from bs4 import BeautifulSoup

from scripts.utils.document_parser import DeclassifiedDocument
from app.connections.pgvector_client import hippocampus

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"
TAVILY_URL = "https://api.tavily.com/search"

# Seed topics for CIA FOIA documents
SEED_TOPICS = [
    "CIA FOIA MKUltra program declassified",
    "CIA FOIA Bay of Pigs invasion declassified",
    "CIA FOIA COINTELPRO documents declassified",
    "CIA FOIA Cold War intelligence operations declassified",
]

CIA_TRACKS = ["TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"]


async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return resp.data[0].embedding


async def _tavily_search_cia(query: str) -> list[dict]:
    """Search Tavily restricted to CIA FOIA domain."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "include_domains": ["cia.gov"],
        "max_results": 3,
        "search_depth": "advanced",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
            return resp.json().get("results", [])
    except Exception as e:
        logger.warning(f"[CIA] Tavily search failed: {e}")
        return []


async def seed_cia_foia_documents(
    topics: list[str] | None = None,
    tracks: list[str] | None = None,
):
    """Seed CIA FOIA documents into Hippocampus."""
    topics = topics or SEED_TOPICS
    tracks = tracks or CIA_TRACKS

    await hippocampus.connect()
    seeded = 0

    for topic in topics:
        results = await _tavily_search_cia(topic)
        for result in results:
            url = result.get("url", "")
            title = result.get("title", "CIA FOIA Document")
            excerpt = result.get("content", "")
            if not excerpt or len(excerpt) < 50:
                continue

            doc = DeclassifiedDocument(
                doc_id=url.split("/")[-1] or str(seeded),
                title=title,
                body=excerpt,
                source_collection="CIA_FOIA",
                citation_author="Central Intelligence Agency",
                citation_year=0,
                source_url=url,
            )

            try:
                embedding = await _embed(doc.body)
            except Exception as e:
                logger.warning(f"[CIA] Embedding failed: {e}")
                continue

            for track in tracks:
                kwargs = doc.to_hippocampus_kwargs(track=track, embedding=embedding)
                doc_id = await hippocampus.upsert_document(**kwargs)
                logger.info(f"[CIA] Seeded '{title}' → {track} (doc_id={doc_id})")
                seeded += 1

    logger.info(f"[CIA] Done — seeded {seeded} document-track pairs")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_cia_foia_documents())
```

- [ ] **Step 3: Create FBI Vault seed script**

Create `adeline-brain/scripts/seed_declassified_fbi.py`:

```python
"""
Seed FBI Vault documents into Hippocampus.
FBI Vault documents are accessed via Tavily domain-restricted search.
"""
import asyncio
import os
import logging

import httpx
import openai

from scripts.utils.document_parser import DeclassifiedDocument
from app.connections.pgvector_client import hippocampus

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"
TAVILY_URL = "https://api.tavily.com/search"

SEED_TOPICS = [
    "FBI Vault civil rights movement documents",
    "FBI Vault COINTELPRO files declassified",
    "FBI Vault Martin Luther King Jr surveillance",
    "FBI Vault Freedom of Information declassified",
]

FBI_TRACKS = ["TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"]


async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return resp.data[0].embedding


async def _tavily_search_fbi(query: str) -> list[dict]:
    """Search Tavily restricted to FBI Vault domain."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "include_domains": ["vault.fbi.gov"],
        "max_results": 3,
        "search_depth": "advanced",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
            return resp.json().get("results", [])
    except Exception as e:
        logger.warning(f"[FBI] Tavily search failed: {e}")
        return []


async def seed_fbi_vault_documents(
    topics: list[str] | None = None,
    tracks: list[str] | None = None,
):
    """Seed FBI Vault documents into Hippocampus."""
    topics = topics or SEED_TOPICS
    tracks = tracks or FBI_TRACKS

    await hippocampus.connect()
    seeded = 0

    for topic in topics:
        results = await _tavily_search_fbi(topic)
        for result in results:
            url = result.get("url", "")
            title = result.get("title", "FBI Vault Document")
            excerpt = result.get("content", "")
            if not excerpt or len(excerpt) < 50:
                continue

            doc = DeclassifiedDocument(
                doc_id=url.split("/")[-1] or str(seeded),
                title=title,
                body=excerpt,
                source_collection="FBI_VAULT",
                citation_author="Federal Bureau of Investigation",
                citation_year=0,
                source_url=url,
            )

            try:
                embedding = await _embed(doc.body)
            except Exception as e:
                logger.warning(f"[FBI] Embedding failed: {e}")
                continue

            for track in tracks:
                kwargs = doc.to_hippocampus_kwargs(track=track, embedding=embedding)
                doc_id = await hippocampus.upsert_document(**kwargs)
                logger.info(f"[FBI] Seeded '{title}' → {track} (doc_id={doc_id})")
                seeded += 1

    logger.info(f"[FBI] Done — seeded {seeded} document-track pairs")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_fbi_vault_documents())
```

- [ ] **Step 4: Create orchestrator script**

Create `adeline-brain/scripts/seed_declassified_all.py`:

```python
"""
Seed ALL declassified document collections into Hippocampus.
Run this once to bootstrap the corpus, then the deep web search
in researcher.py will continue acquiring documents automatically.
"""
import asyncio
import logging

from scripts.seed_declassified_nara import seed_nara_documents
from scripts.seed_declassified_cia import seed_cia_foia_documents
from scripts.seed_declassified_fbi import seed_fbi_vault_documents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_all():
    """Seed all declassified collections sequentially."""
    logger.info("=== Seeding Declassified Documents ===")

    logger.info("\n--- NARA (National Archives) ---")
    await seed_nara_documents()

    logger.info("\n--- CIA FOIA Reading Room ---")
    await seed_cia_foia_documents()

    logger.info("\n--- FBI Vault ---")
    await seed_fbi_vault_documents()

    logger.info("\n=== All declassified sources seeded ===")


if __name__ == "__main__":
    asyncio.run(seed_all())
```

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/scripts/seed_declassified_nara.py adeline-brain/scripts/seed_declassified_cia.py adeline-brain/scripts/seed_declassified_fbi.py adeline-brain/scripts/seed_declassified_all.py
git commit -m "feat: Add seed scripts for NARA, CIA FOIA, FBI Vault declassified docs"
```

---

### Task 6: Add SourceBadge React Component

**Files:**
- Create: `adeline-ui/src/components/SourceBadge.tsx`
- Modify: `adeline-ui/src/components/GenUIRenderer.tsx`

- [ ] **Step 1: Create SourceBadge component**

Create `adeline-ui/src/components/SourceBadge.tsx`:

```tsx
import React from "react";

type SourceType =
  | "PRIMARY_SOURCE"
  | "DECLASSIFIED_GOV"
  | "ARCHIVE_ORG"
  | "ACADEMIC_JOURNAL"
  | "PERSONAL_COLLECTION";

interface SourceBadgeProps {
  sourceType: SourceType;
  sourceTitle: string;
  sourceUrl?: string;
  citationYear?: number;
}

const BADGE_STYLES: Record<SourceType, string> = {
  PRIMARY_SOURCE: "bg-green-100 text-green-800",
  DECLASSIFIED_GOV: "bg-red-100 text-red-800",
  ARCHIVE_ORG: "bg-blue-100 text-blue-800",
  ACADEMIC_JOURNAL: "bg-purple-100 text-purple-800",
  PERSONAL_COLLECTION: "bg-gray-100 text-gray-800",
};

const BADGE_ICONS: Record<SourceType, string> = {
  PRIMARY_SOURCE: "\u{1F4C4}",      // 📄
  DECLASSIFIED_GOV: "\u{1F3DB}",    // 🏛️
  ARCHIVE_ORG: "\u{1F5C2}",         // 🗂️
  ACADEMIC_JOURNAL: "\u{1F4DA}",    // 📚
  PERSONAL_COLLECTION: "\u{1F4DD}", // 📝
};

const BADGE_LABELS: Record<SourceType, string> = {
  PRIMARY_SOURCE: "Primary Source",
  DECLASSIFIED_GOV: "Declassified Document",
  ARCHIVE_ORG: "Archive.org",
  ACADEMIC_JOURNAL: "Academic Journal",
  PERSONAL_COLLECTION: "Personal Collection",
};

export function SourceBadge({
  sourceType,
  sourceTitle,
  sourceUrl,
  citationYear,
}: SourceBadgeProps) {
  const style = BADGE_STYLES[sourceType] ?? BADGE_STYLES.PRIMARY_SOURCE;
  const icon = BADGE_ICONS[sourceType] ?? BADGE_ICONS.PRIMARY_SOURCE;
  const label = BADGE_LABELS[sourceType] ?? "Source";

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${style}`}
    >
      <span>{icon}</span>
      <span>{label}</span>
      {citationYear ? (
        <span className="text-xs opacity-75">({citationYear})</span>
      ) : null}
      {sourceUrl ? (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-1 underline hover:opacity-75"
          title={sourceTitle}
        >
          View source
        </a>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 2: Import SourceBadge in GenUIRenderer**

Read `adeline-ui/src/components/GenUIRenderer.tsx` to find where PRIMARY_SOURCE blocks are rendered, then add:

```tsx
import { SourceBadge } from "./SourceBadge";
```

In the PRIMARY_SOURCE block rendering section, add after the block content:

```tsx
{block.evidence && block.evidence.length > 0 && (
  <div className="mt-3 flex flex-wrap gap-2">
    {block.evidence.map((ev, i) => (
      <SourceBadge
        key={ev.source_id || i}
        sourceType={ev.source_type ?? "PRIMARY_SOURCE"}
        sourceTitle={ev.source_title}
        sourceUrl={ev.source_url}
        citationYear={ev.witness_citation?.year}
      />
    ))}
  </div>
)}
```

- [ ] **Step 3: Verify UI compiles**

Run: `cd adeline-ui && pnpm build`

Expected: Build succeeds with no type errors

- [ ] **Step 4: Commit**

```bash
git add adeline-ui/src/components/SourceBadge.tsx adeline-ui/src/components/GenUIRenderer.tsx
git commit -m "feat: Add SourceBadge component for evidence source type display"
```

---

### Task 7: Integration Tests — Witness Protocol + Deep Search

**Files:**
- Create: `adeline-brain/tests/test_witness_declassified_integration.py`

- [ ] **Step 1: Write integration tests**

Create `adeline-brain/tests/test_witness_declassified_integration.py`:

```python
"""
Integration tests: Witness Protocol treats declassified sources as first-class,
and deep web search acquires + persists new documents.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.protocols.witness import evaluate_evidence, EvidenceVerdict
from app.tools.researcher import search_witnesses, _deep_search_primary_sources, DEEP_SEARCH_DOMAINS


# ── Witness Protocol accepts declassified sources ──────────────────────

def test_witness_protocol_verifies_declassified_source():
    """Declassified source at 0.88 must be VERIFIED — not treated differently."""
    evidence = evaluate_evidence(
        source_id="nara-2723456",
        source_title="Civil Rights Act - 1964 Legislative Record",
        similarity_score=0.88,
        chunk="Full text of the Civil Rights Act...",
        source_url="https://catalog.archives.gov/id/2723456",
        citation_author="National Archives",
        citation_year=1964,
        citation_archive_name="NARA",
    )
    assert evidence.verdict == EvidenceVerdict.VERIFIED
    assert evidence.similarity_score == 0.88


def test_witness_protocol_rejects_low_similarity_declassified():
    """Declassified source at 0.65 must be ARCHIVE_SILENT — same rules as any source."""
    evidence = evaluate_evidence(
        source_id="cia-12345",
        source_title="CIA FOIA Document",
        similarity_score=0.65,
        chunk="Some declassified content...",
        source_url="https://cia.gov/readingroom/12345",
        citation_author="CIA",
        citation_year=1972,
        citation_archive_name="CIA FOIA",
    )
    assert evidence.verdict == EvidenceVerdict.ARCHIVE_SILENT


# ── Deep search domains ───────────────────────────────────────────────

def test_deep_search_includes_all_government_archives():
    """Deep search must cover all six government archive domains."""
    gov_domains = {"archives.gov", "cia.gov", "vault.fbi.gov",
                   "congress.gov", "federalregister.gov", "nsarchive.gwu.edu"}
    assert gov_domains.issubset(set(DEEP_SEARCH_DOMAINS))


def test_deep_search_includes_public_domain_archives():
    """Deep search must also include archive.org and gutenberg.org."""
    assert "archive.org" in DEEP_SEARCH_DOMAINS
    assert "gutenberg.org" in DEEP_SEARCH_DOMAINS


# ── Deep search acquires and persists ─────────────────────────────────

@pytest.mark.asyncio
@patch("app.tools.researcher._embed")
@patch("app.tools.researcher._tavily_search")
@patch("app.tools.researcher.hippocampus")
@patch("app.tools.researcher.neo4j_client")
async def test_deep_search_acquires_and_persists_source(
    mock_neo4j, mock_hippo, mock_tavily, mock_embed
):
    """
    When deep search finds a document clearing 0.82,
    it must:
      1. Persist to Hippocampus with correct source_type
      2. Return a WitnessResult with VERIFIED verdict
    """
    mock_tavily.return_value = [
        {
            "url": "https://catalog.archives.gov/id/299868",
            "title": "Civil Rights Act of 1964",
            "content": "An act to enforce the constitutional right to vote...",
        }
    ]
    query_emb = [0.9] * 1536
    mock_embed.return_value = query_emb  # Same vector = similarity 1.0
    mock_hippo.upsert_document = AsyncMock(return_value="new-doc-id")
    mock_neo4j.run = AsyncMock()

    result = await _deep_search_primary_sources(
        topic="civil rights act 1964",
        track="TRUTH_HISTORY",
        query_embedding=query_emb,
        lesson_id="lesson-123",
    )

    assert result is not None
    assert result.evidence.verdict == EvidenceVerdict.VERIFIED
    assert result.evidence.source_title == "Civil Rights Act of 1964"

    # Verify persisted to Hippocampus
    mock_hippo.upsert_document.assert_called_once()
    call_kwargs = mock_hippo.upsert_document.call_args[1]
    assert call_kwargs["source_type"] == "DECLASSIFIED_GOV"
    assert call_kwargs["track"] == "TRUTH_HISTORY"


# ── Full search_witnesses flow ────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.tools.researcher.hippocampus")
@patch("app.tools.researcher.neo4j_client")
async def test_search_witnesses_returns_hippocampus_hit_first(mock_neo4j, mock_hippo):
    """
    When Hippocampus already has a DECLASSIFIED_GOV source at 0.88,
    search_witnesses must return it without deep searching.
    """
    mock_hippo.similarity_search = AsyncMock(return_value=[
        {
            "id": "existing-doc",
            "source_title": "Voting Rights Act of 1965",
            "source_url": "https://catalog.archives.gov/id/595381",
            "chunk": "An act to enforce the fifteenth amendment...",
            "source_type": "DECLASSIFIED_GOV",
            "citation_author": "National Archives",
            "citation_year": 1965,
            "citation_archive_name": "NARA",
            "similarity_score": 0.88,
        }
    ])
    mock_neo4j.run = AsyncMock()

    result = await search_witnesses(
        topic="voting rights act 1965",
        track="TRUTH_HISTORY",
        query_embedding=[0.9] * 1536,
        lesson_id="lesson-456",
    )

    assert result is not None
    assert result.evidence.verdict == EvidenceVerdict.VERIFIED
    assert result.evidence.source_title == "Voting Rights Act of 1965"
    # Hippocampus was queried — deep search was NOT triggered
    mock_hippo.similarity_search.assert_called_once()


@pytest.mark.asyncio
@patch("app.tools.researcher._deep_search_primary_sources")
@patch("app.tools.researcher.hippocampus")
async def test_search_witnesses_triggers_deep_search_on_miss(mock_hippo, mock_deep):
    """
    When Hippocampus returns nothing above threshold,
    search_witnesses must trigger deep web search.
    """
    mock_hippo.similarity_search = AsyncMock(return_value=[
        {
            "id": "weak-doc",
            "source_title": "Vaguely related doc",
            "source_url": "",
            "chunk": "...",
            "source_type": "PRIMARY_SOURCE",
            "citation_author": "",
            "citation_year": None,
            "citation_archive_name": "",
            "similarity_score": 0.55,  # Below threshold
        }
    ])
    mock_deep.return_value = None  # Deep search also fails

    result = await search_witnesses(
        topic="obscure historical event",
        track="TRUTH_HISTORY",
        query_embedding=[0.5] * 1536,
        lesson_id="lesson-789",
    )

    # Result is None → RESEARCH_MISSION
    assert result is None
    # Deep search WAS triggered
    mock_deep.assert_called_once()
```

- [ ] **Step 2: Run integration tests**

Run: `cd adeline-brain && python -m pytest tests/test_witness_declassified_integration.py -v`

Expected: All 6 tests pass

- [ ] **Step 3: Run full test suite**

Run: `cd adeline-brain && python -m pytest tests/ -v`

Expected: All tests pass, no regressions

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/tests/test_witness_declassified_integration.py
git commit -m "test: Integration tests for Witness Protocol + deep web search acquisition"
```

---

## Summary

| # | Task | What It Does |
|---|------|-------------|
| 1 | Add `source_type` to HippocampusDocument | New column so Hippocampus can store + return source type |
| 2 | Add SourceType to TypeScript | Enum + DECLASSIFIED_COLLECTIONS in adeline-core |
| 3 | Rewrite SearchWitnesses | Unified Hippocampus query → deep web search acquisition → RESEARCH_MISSION |
| 4 | DeclassifiedDocument parser | Data class for seed scripts |
| 5 | Seed scripts (NARA, CIA, FBI) | Bootstrap the corpus with declassified documents |
| 6 | SourceBadge component | UI badging for evidence source type |
| 7 | Integration tests | Verify the full flow works end-to-end |

**Self-improving loop:** After initial seeding (Task 5), the deep web search in Task 3 continues acquiring new documents automatically whenever a student asks about something not yet in Hippocampus. Every miss makes the system smarter.
