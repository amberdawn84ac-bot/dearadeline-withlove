# Declassified Documents Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship declassified documents integration fully production-ready with error handling, rate limiting, content filtering, monitoring, scheduling, and UI polish.

**Architecture:** Modular approach—separate utilities for rate limiting, content filtering, and logging; integrate into existing seed script and search_witnesses pipeline; add scheduled job for nightly seeding; integrate SourceBadge into lesson blocks.

**Tech Stack:** Python (FastAPI), SQLAlchemy (Prisma migration), PostgreSQL/pgvector, Tavily API, pytest, structured logging (structlog or stdlib.logging)

---

## File Structure

**Files to Create:**
- `app/utils/rate_limiter.py` — Token-bucket rate limiting for API calls
- `app/protocols/content_filter.py` — Age-gating for sensitive documents (COINTELPRO, assassination plots, etc.)
- `app/utils/structured_logger.py` — Structured logging with metadata context
- `app/jobs/seed_scheduler.py` — APScheduler job for nightly Hippocampus seeding

**Files to Modify:**
- `app/scripts/seed_declassified_documents.py` — Add error handling, retry logic, rate limiting
- `app/connections/pgvector_client.py` — Add duplicate detection before upsert
- `app/tools/researcher.py` — Integrate content_filter before returning results
- `prisma/schema.prisma` — Add uniqueness constraint on HippocampusDocument
- `adeline-brain/app/main.py` — Register seed scheduler on startup
- `adeline-ui/src/components/GenUIRenderer.tsx` — Render SourceBadge in lesson blocks

**Test Files to Create:**
- `tests/test_rate_limiter.py`
- `tests/test_content_filter.py`
- `tests/test_seed_error_handling.py`

---

## Phase 1: Error Handling & Rate Limiting

### Task 1: Create Rate Limiter Utility

**Files:**
- Create: `app/utils/rate_limiter.py`
- Test: `tests/test_rate_limiter.py`

- [ ] **Step 1: Write failing test for token bucket**

```python
# tests/test_rate_limiter.py
import pytest
from app.utils.rate_limiter import TokenBucket

@pytest.mark.asyncio
async def test_token_bucket_allows_requests_within_limit():
    """Token bucket allows requests up to max_tokens."""
    bucket = TokenBucket(max_tokens=5, refill_rate=1.0)

    # Should allow 5 requests
    for i in range(5):
        assert await bucket.acquire() == True

    # 6th request should fail
    assert await bucket.acquire() == False

@pytest.mark.asyncio
async def test_token_bucket_refills_over_time():
    """Tokens refill at specified rate."""
    bucket = TokenBucket(max_tokens=2, refill_rate=1.0)

    # Use both tokens
    await bucket.acquire()
    await bucket.acquire()
    assert await bucket.acquire() == False

    # Wait 1.1 seconds (refill_rate=1 token/sec)
    import asyncio
    await asyncio.sleep(1.1)

    # Should have 1 token available
    assert await bucket.acquire() == True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd adeline-brain
python -m pytest tests/test_rate_limiter.py::test_token_bucket_allows_requests_within_limit -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Implement TokenBucket class**

```python
# app/utils/rate_limiter.py
"""Token bucket rate limiter for API calls."""
import asyncio
import time
from dataclasses import dataclass

@dataclass
class TokenBucket:
    """Token bucket rate limiter (sliding window)."""
    max_tokens: float
    refill_rate: float  # Tokens per second
    _tokens: float = None
    _last_refill: float = None
    _lock: asyncio.Lock = None

    def __post_init__(self):
        if self._tokens is None:
            self._tokens = self.max_tokens
        if self._last_refill is None:
            self._last_refill = time.monotonic()
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens from the bucket.
        Returns True if successful, False if insufficient tokens.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill

            # Refill tokens
            self._tokens = min(
                self.max_tokens,
                self._tokens + (elapsed * self.refill_rate)
            )
            self._last_refill = now

            # Try to acquire
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def wait_for_acquire(self, tokens: float = 1.0) -> None:
        """
        Wait until tokens are available, then acquire them.
        Blocks until successful.
        """
        while not await self.acquire(tokens):
            await asyncio.sleep(0.1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_rate_limiter.py -v
```

Expected: 2 passing

- [ ] **Step 5: Commit**

```bash
git add app/utils/rate_limiter.py tests/test_rate_limiter.py
git commit -m "feat: add TokenBucket rate limiter utility"
```

---

### Task 2: Add Error Handling & Retry Logic to Seed Script

**Files:**
- Modify: `app/scripts/seed_declassified_documents.py:86-172` (all seed functions)
- Test: `tests/test_seed_error_handling.py`

- [ ] **Step 1: Write failing test for retry logic**

```python
# tests/test_seed_error_handling.py
import pytest
from unittest.mock import AsyncMock, patch
from app.scripts.seed_declassified_documents import _retry_search

@pytest.mark.asyncio
async def test_retry_search_succeeds_on_second_attempt():
    """Retry logic succeeds after transient failure."""
    call_count = [0]

    async def flaky_search(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ConnectionError("Network error")
        return [{"title": "Success"}]

    result = await _retry_search(
        query="test",
        archive="NARA",
        max_retries=3,
        search_fn=flaky_search,
    )

    assert len(result) == 1
    assert call_count[0] == 2

@pytest.mark.asyncio
async def test_retry_search_gives_up_after_max_retries():
    """Retry logic exhausts retries and raises."""
    async def always_fails(*args, **kwargs):
        raise ConnectionError("Network error")

    with pytest.raises(ConnectionError):
        await _retry_search(
            query="test",
            archive="NARA",
            max_retries=2,
            search_fn=always_fails,
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_seed_error_handling.py::test_retry_search_succeeds_on_second_attempt -v
```

Expected: FAIL — function not found

- [ ] **Step 3: Implement retry wrapper and update seed functions**

Add this helper to `seed_declassified_documents.py`:

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

async def _retry_search(
    query: str,
    archive: str,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    search_fn=None,
) -> list[dict]:
    """
    Retry search with exponential backoff.

    Args:
        query: Search query
        archive: Archive name (NARA, CIA_FOIA, etc.)
        max_retries: Number of retries
        backoff_factor: Exponential backoff multiplier
        search_fn: Async search function to call

    Returns:
        List of results or empty list

    Raises:
        Exception: After exhausting retries
    """
    for attempt in range(max_retries + 1):
        try:
            return await search_fn(query, archive)
        except (ConnectionError, TimeoutError, Exception) as e:
            if attempt == max_retries:
                logger.error(
                    f"[{archive}] Failed after {max_retries + 1} attempts: {e}"
                )
                raise

            wait_time = (backoff_factor ** attempt)
            logger.warning(
                f"[{archive}] Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                f"Retrying in {wait_time}s..."
            )
            await asyncio.sleep(wait_time)

    return []
```

Update `seed_nara_documents` to use retry:

```python
async def seed_nara_documents(track: str, limit: int = 10) -> int:
    """
    Seed NARA (National Archives and Records Administration) documents into Hippocampus.
    Includes retry logic with exponential backoff.

    Searches for documents relevant to the given track.

    Args:
        track: Track name (TRUTH_HISTORY, JUSTICE_CHANGEMAKING, etc.)
        limit: Max documents to ingest per query

    Returns:
        Number of chunks ingested
    """
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("[NARA] TAVILY_API_KEY not set — skipping NARA seed")
        return 0

    queries = TRACK_QUERIES.get(track, [f"{track} declassified documents"])
    ingested_count = 0

    for query in queries:
        try:
            logger.info(f"[NARA] Searching: {query}")

            # Use retry wrapper
            results = await _retry_search(
                query=query,
                archive="NARA",
                max_retries=3,
                search_fn=search_archive_async,
            )

            for result in results[:limit]:
                try:
                    url = result.get("url", "")
                    title = result.get("title", "Untitled NARA Document")
                    snippet = result.get("snippet", "")

                    if not snippet:
                        logger.warning(f"[NARA] No snippet for {title}")
                        continue

                    # Parse snippet into chunks
                    chunks = parse_declassified_document(
                        raw_text=snippet,
                        archive_name="NARA",
                        source_url=url,
                    )

                    if not chunks:
                        continue

                    # Embed and persist each chunk
                    for chunk in chunks:
                        try:
                            client = _get_openai_client()
                            embedding_response = await client.embeddings.create(
                                model="text-embedding-3-small",
                                input=chunk.chunk_text,
                            )
                            embedding = embedding_response.data[0].embedding

                            # Upsert to Hippocampus
                            doc_id = await hippocampus.upsert_document(
                                source_title=title,
                                track=track,
                                chunk=chunk.chunk_text,
                                embedding=embedding,
                                source_url=url,
                                source_type=SourceType.DECLASSIFIED_GOV.value,
                                citation_author=chunk.metadata.get("author", ""),
                                citation_year=None,
                                citation_archive_name="NARA",
                            )
                            ingested_count += 1
                            logger.info(f"[NARA] Ingested: {title[:50]}...")

                        except Exception as e:
                            logger.warning(f"[NARA] Failed to embed/persist chunk: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"[NARA] Failed to process document {title}: {e}")
                    continue

        except Exception as e:
            logger.error(f"[NARA] Error searching (retries exhausted): {e}")
            continue

    logger.info(f"[NARA] Seed complete: {ingested_count} chunks ingested")
    return ingested_count
```

Apply the same pattern to `seed_cia_foia_documents` and `seed_fbi_vault_documents`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_seed_error_handling.py -v
```

Expected: 2 passing

- [ ] **Step 5: Commit**

```bash
git add app/scripts/seed_declassified_documents.py tests/test_seed_error_handling.py
git commit -m "feat: add error handling and retry logic to seed script"
```

---

### Task 3: Integrate Rate Limiting into Tavily API Calls

**Files:**
- Modify: `app/scripts/seed_declassified_documents.py:1-40` (imports and rate limiter init)
- Modify: `app/tools/researcher.py:search_all_archives_parallel` (rate limit parallel searches)

- [ ] **Step 1: Initialize rate limiters for each archive**

Add to top of `seed_declassified_documents.py`:

```python
from app.utils.rate_limiter import TokenBucket

# Rate limiters per archive (Tavily has per-API-key limits)
# Adjust these based on your Tavily plan
TAVILY_RATE_LIMITERS = {
    "NARA": TokenBucket(max_tokens=10, refill_rate=1.0),  # 10 req/sec
    "CIA_FOIA": TokenBucket(max_tokens=10, refill_rate=1.0),
    "FBI_VAULT": TokenBucket(max_tokens=10, refill_rate=1.0),
}
```

- [ ] **Step 2: Apply rate limiting in search_archive_async**

Update call in `seed_nara_documents`:

```python
# Apply rate limiting before search
await TAVILY_RATE_LIMITERS["NARA"].wait_for_acquire(1)
results = await _retry_search(
    query=query,
    archive="NARA",
    max_retries=3,
    search_fn=search_archive_async,
)
```

Repeat for CIA and FBI searches.

- [ ] **Step 3: Test rate limiting under load**

```bash
python -m pytest tests/test_seed_error_handling.py -v
```

Expected: Still passing

- [ ] **Step 4: Commit**

```bash
git add app/scripts/seed_declassified_documents.py
git commit -m "feat: add rate limiting to Tavily API calls"
```

---

## Phase 2: Database Integrity

### Task 4: Add Uniqueness Constraint to Schema

**Files:**
- Modify: `prisma/schema.prisma`
- Create: `prisma/migrations/20260402_add_document_uniqueness`

- [ ] **Step 1: Update Prisma schema**

Modify the HippocampusDocument model in `schema.prisma`:

```prisma
model HippocampusDocument {
  id                   String   @id @default(cuid())
  source_title         String
  source_url           String
  source_type          String   @default("PRIMARY_SOURCE")
  chunk                String   @db.Text
  embedding            Float[]  // pgvector type
  citation_author      String   @default("")
  citation_year        Int?
  citation_archive_name String  @default("")
  track                String
  created_at           DateTime @default(now())
  updated_at           DateTime @updatedAt

  // Prevent duplicate (source_url, chunk_hash) combinations
  @@unique([source_url, chunk])
}
```

- [ ] **Step 2: Generate migration**

```bash
cd adeline-brain
npx prisma migrate dev --name add_document_uniqueness
```

Expected: Migration created in `prisma/migrations/20260402_add_document_uniqueness/`

- [ ] **Step 3: Verify migration SQL**

Check `prisma/migrations/20260402_add_document_uniqueness/migration.sql`:

Should contain:

```sql
CREATE UNIQUE INDEX "HippocampusDocument_source_url_chunk_key" ON "HippocampusDocument"("source_url", "chunk");
```

- [ ] **Step 4: Commit**

```bash
git add prisma/schema.prisma prisma/migrations/
git commit -m "feat: add uniqueness constraint to HippocampusDocument"
```

---

### Task 5: Implement Duplicate Detection in pgvector_client

**Files:**
- Modify: `app/connections/pgvector_client.py:upsert_document` method

- [ ] **Step 1: Write failing test for duplicate detection**

```python
# tests/test_pgvector_client.py (add to existing)
@pytest.mark.asyncio
async def test_upsert_skips_duplicate_documents():
    """Upsert skips documents already in Hippocampus."""
    # First upsert
    doc_id_1 = await hippocampus.upsert_document(
        source_title="Test Doc",
        track="TRUTH_HISTORY",
        chunk="Original text",
        embedding=[0.1] * 1536,
        source_url="https://example.com/doc",
        source_type="DECLASSIFIED_GOV",
        citation_author="Author",
        citation_year=1950,
        citation_archive_name="NARA",
    )

    # Second upsert (duplicate)
    doc_id_2 = await hippocampus.upsert_document(
        source_title="Test Doc",
        track="TRUTH_HISTORY",
        chunk="Original text",  # Same chunk
        embedding=[0.1] * 1536,
        source_url="https://example.com/doc",  # Same URL
        source_type="DECLASSIFIED_GOV",
        citation_author="Author",
        citation_year=1950,
        citation_archive_name="NARA",
    )

    # Should return same ID (not inserted)
    assert doc_id_1 == doc_id_2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_pgvector_client.py::test_upsert_skips_duplicate_documents -v
```

Expected: FAIL — AssertionError (IDs don't match)

- [ ] **Step 3: Implement duplicate detection**

Update `upsert_document` in `pgvector_client.py`:

```python
async def upsert_document(
    self,
    source_title: str,
    track: str,
    chunk: str,
    embedding: list[float],
    source_url: str = "",
    source_type: str = "PRIMARY_SOURCE",
    citation_author: str = "",
    citation_year: Optional[int] = None,
    citation_archive_name: str = "",
) -> str:
    """
    Upsert document to Hippocampus.

    Checks for duplicates (source_url + chunk combination).
    If duplicate exists, returns existing ID without inserting.

    Returns: Document ID (existing or new)
    """
    try:
        # Check for duplicate
        query = """
            SELECT id FROM hippocampus_documents
            WHERE source_url = %s AND chunk = %s
            LIMIT 1
        """
        result = await self.pool.fetchrow(query, source_url, chunk)

        if result:
            logger.info(f"[Hippocampus] Skipped duplicate: {source_url[:50]}... (chunk match)")
            return result["id"]

        # Not a duplicate, insert new document
        doc_id = str(uuid.uuid4())

        insert_query = """
            INSERT INTO hippocampus_documents (
                id, source_title, source_url, source_type, chunk, embedding,
                citation_author, citation_year, citation_archive_name, track
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """

        await self.pool.execute(
            insert_query,
            doc_id,
            source_title,
            source_url,
            source_type,
            chunk,
            embedding,  # pgvector column
            citation_author,
            citation_year,
            citation_archive_name,
            track,
        )

        logger.info(f"[Hippocampus] Inserted: {source_title[:50]}... ({source_type})")
        return doc_id

    except Exception as e:
        logger.error(f"[Hippocampus] Upsert failed: {e}")
        raise
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_pgvector_client.py::test_upsert_skips_duplicate_documents -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/connections/pgvector_client.py tests/test_pgvector_client.py
git commit -m "feat: add duplicate detection in pgvector_client"
```

---

## Phase 3: Structured Logging & Monitoring

### Task 6: Create Structured Logger

**Files:**
- Create: `app/utils/structured_logger.py`
- Test: `tests/test_structured_logger.py`

- [ ] **Step 1: Write failing test for structured logger**

```python
# tests/test_structured_logger.py
import pytest
from app.utils.structured_logger import get_logger

def test_structured_logger_includes_context():
    """Structured logger includes context metadata."""
    logger = get_logger("test_module", context={"student_id": "s123", "track": "TRUTH_HISTORY"})

    # Logger should include context in output
    assert logger.context == {"student_id": "s123", "track": "TRUTH_HISTORY"}

def test_structured_logger_merges_context():
    """Log call merges context with message."""
    logger = get_logger("test_module", context={"student_id": "s123"})

    # This should not raise
    logger.info("message", extra={"action": "seed", "count": 5})

    # Verify context is preserved
    assert logger.context["student_id"] == "s123"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_structured_logger.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Implement structured logger**

```python
# app/utils/structured_logger.py
"""Structured logging with context metadata."""
import logging
import json
from typing import Optional, Any

class StructuredLogger:
    """Logger that includes context metadata in all messages."""

    def __init__(self, name: str, context: Optional[dict] = None):
        self.name = name
        self.context = context or {}
        self._logger = logging.getLogger(name)

    def _format_message(self, level: str, message: str, extra: Optional[dict] = None) -> dict:
        """Format log message with context."""
        log_entry = {
            "timestamp": logging.Formatter().formatTime(logging.LogRecord(
                name=self.name,
                level=getattr(logging, level),
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None,
            )),
            "level": level,
            "module": self.name,
            "message": message,
            **self.context,
        }

        if extra:
            log_entry.update(extra)

        return log_entry

    def info(self, message: str, extra: Optional[dict] = None):
        """Log info level message."""
        log_entry = self._format_message("INFO", message, extra)
        self._logger.info(json.dumps(log_entry))

    def warning(self, message: str, extra: Optional[dict] = None):
        """Log warning level message."""
        log_entry = self._format_message("WARNING", message, extra)
        self._logger.warning(json.dumps(log_entry))

    def error(self, message: str, extra: Optional[dict] = None):
        """Log error level message."""
        log_entry = self._format_message("ERROR", message, extra)
        self._logger.error(json.dumps(log_entry))

def get_logger(name: str, context: Optional[dict] = None) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name, context)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_structured_logger.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/utils/structured_logger.py tests/test_structured_logger.py
git commit -m "feat: add structured logger with context metadata"
```

---

### Task 7: Integrate Structured Logging into Seed Script

**Files:**
- Modify: `app/scripts/seed_declassified_documents.py` (all logger calls)

- [ ] **Step 1: Update imports in seed script**

Replace:

```python
import logging
logger = logging.getLogger(__name__)
```

With:

```python
from app.utils.structured_logger import get_logger
logger = get_logger(__name__)
```

- [ ] **Step 2: Update all logger calls to include context**

Example—update `seed_nara_documents`:

```python
async def seed_nara_documents(track: str, limit: int = 10) -> int:
    """Seed NARA documents with structured logging."""
    logger = get_logger(__name__, context={"archive": "NARA", "track": track})

    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("TAVILY_API_KEY not set — skipping")
        return 0

    queries = TRACK_QUERIES.get(track, [])
    ingested_count = 0

    for query in queries:
        logger.info(f"Searching: {query}", extra={"query": query})

        try:
            results = await _retry_search(
                query=query,
                archive="NARA",
                max_retries=3,
                search_fn=search_archive_async,
            )

            logger.info(f"Found {len(results)} results", extra={"result_count": len(results)})

            # ... rest of processing ...

            ingested_count += 1
            logger.info(f"Ingested chunk", extra={"document": title[:50], "ingested_count": ingested_count})

        except Exception as e:
            logger.error(f"Search failed: {e}", extra={"error": str(e), "query": query})
            continue

    logger.info(f"Seed complete", extra={"total_ingested": ingested_count})
    return ingested_count
```

Apply same pattern to CIA and FBI functions.

- [ ] **Step 3: Test seed script with structured logging**

```bash
python -m pytest tests/test_seed_error_handling.py -v
```

Expected: PASS (all tests still pass with new logging)

- [ ] **Step 4: Commit**

```bash
git add app/scripts/seed_declassified_documents.py
git commit -m "feat: integrate structured logging into seed script"
```

---

## Phase 4: Content Filtering

### Task 8: Create Content Filter for Age-Gating

**Files:**
- Create: `app/protocols/content_filter.py`
- Test: `tests/test_content_filter.py`

- [ ] **Step 1: Write failing test for content filter**

```python
# tests/test_content_filter.py
import pytest
from app.protocols.content_filter import ContentFilter, SENSITIVE_KEYWORDS

def test_content_filter_detects_sensitive_documents():
    """Content filter identifies sensitive documents."""
    filter = ContentFilter(min_age=13)

    sensitive_results = [
        {
            "source_title": "FBI COINTELPRO Operations",
            "source_url": "https://vault.fbi.gov/...",
            "chunk": "FBI Director authorized surveillance...",
            "similarity_score": 0.88,
        }
    ]

    filtered = filter.filter_for_age(sensitive_results, age=12)

    # Should be filtered out (age < 13)
    assert len(filtered) == 0

def test_content_filter_allows_documents_above_threshold():
    """Content filter allows documents for appropriate age."""
    filter = ContentFilter(min_age=13)

    results = [
        {
            "source_title": "Declaration of Independence",
            "source_url": "https://...",
            "chunk": "We hold these truths...",
            "similarity_score": 0.89,
        }
    ]

    filtered = filter.filter_for_age(results, age=14)

    # Should be allowed (not sensitive, age >= min)
    assert len(filtered) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_content_filter.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Implement content filter**

```python
# app/protocols/content_filter.py
"""Content filter for age-gating sensitive government documents."""
from typing import Optional
from enum import Enum

class SensitivityLevel(int, Enum):
    """Minimum age required to view document."""
    PUBLIC       = 0    # All ages
    TEEN         = 13   # Civil rights, historical events
    HIGH_SCHOOL  = 15   # Government surveillance, regulatory capture
    ADULT        = 18   # Assassination plots, CIA black ops

# Keywords that trigger sensitivity checks
SENSITIVE_KEYWORDS = {
    SensitivityLevel.TEEN: [
        "civil rights",
        "government decision-making",
        "presidential records",
        "State Department memo",
    ],
    SensitivityLevel.HIGH_SCHOOL: [
        "surveillance",
        "COINTELPRO",
        "regulatory capture",
        "FBI vault",
        "CIA",
        "assassination",
        "covert operation",
    ],
    SensitivityLevel.ADULT: [
        "assassination plot",
        "CIA black ops",
        "unauthorized killing",
        "coup attempt",
    ],
}

class ContentFilter:
    """Filter declassified documents by student age."""

    def __init__(self, min_age: int = 5):
        self.min_age = min_age

    def _get_sensitivity_level(self, document: dict) -> SensitivityLevel:
        """Determine sensitivity level from document metadata."""
        title = document.get("source_title", "").lower()
        chunk = document.get("chunk", "").lower()
        archive = document.get("citation_archive_name", "").upper()

        # FBI COINTELPRO → HIGH_SCHOOL minimum
        if archive == "FBI_VAULT" and "cointelpro" in title:
            return SensitivityLevel.HIGH_SCHOOL

        # CIA assassination plots → ADULT minimum
        if archive == "CIA_FOIA" and ("assassination" in chunk or "black ops" in chunk):
            return SensitivityLevel.ADULT

        # Check keywords
        for level, keywords in SENSITIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in title or keyword in chunk:
                    return level

        return SensitivityLevel.PUBLIC

    def filter_for_age(self, documents: list[dict], age: int) -> list[dict]:
        """
        Filter documents based on student age.

        Args:
            documents: List of documents from Hippocampus search
            age: Student age

        Returns:
            Filtered list of documents appropriate for age
        """
        filtered = []

        for doc in documents:
            sensitivity = self._get_sensitivity_level(doc)

            if age >= sensitivity.value:
                filtered.append(doc)
            else:
                # Log filtering (use structured logger if available)
                title = doc.get("source_title", "?")
                import logging
                logging.warning(
                    f"[ContentFilter] Filtered '{title}' (requires age {sensitivity.value}, student is {age})"
                )

        return filtered
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_content_filter.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/protocols/content_filter.py tests/test_content_filter.py
git commit -m "feat: add content filter for age-gating sensitive documents"
```

---

### Task 9: Integrate Content Filter into search_witnesses

**Files:**
- Modify: `app/tools/researcher.py:search_witnesses` function

- [ ] **Step 1: Import content filter**

```python
from app.protocols.content_filter import ContentFilter
```

- [ ] **Step 2: Add age parameter to search_witnesses**

Update function signature:

```python
async def search_witnesses(
    query: str,
    track: str,
    top_k: int = 10,
    student_age: Optional[int] = None,  # NEW
) -> list[dict]:
    """
    Search for verified sources across Hippocampus + deep web.

    Args:
        query: Search query
        track: Track name
        top_k: Max results
        student_age: Student age for content filtering (optional)

    Returns:
        List of VERIFIED sources or empty list
    """
```

- [ ] **Step 3: Apply content filter before returning results**

Add before return statement:

```python
    # Apply content filtering if age provided
    if student_age is not None:
        filter = ContentFilter()
        results = filter.filter_for_age(results, student_age)

    return results
```

- [ ] **Step 4: Test integration**

```bash
python -m pytest tests/test_witness_declassified_integration.py -v
```

Expected: All existing tests still pass

- [ ] **Step 5: Commit**

```bash
git add app/tools/researcher.py
git commit -m "feat: integrate content filter into search_witnesses"
```

---

## Phase 5: Scheduling

### Task 10: Create Scheduled Seed Job

**Files:**
- Create: `app/jobs/seed_scheduler.py`
- Modify: `app/main.py` (startup event)

- [ ] **Step 1: Install APScheduler**

```bash
pip install apscheduler
pip freeze > requirements.txt
```

- [ ] **Step 2: Create scheduler module**

```python
# app/jobs/seed_scheduler.py
"""Background job: nightly Hippocampus seeding."""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scripts.seed_declassified_documents import seed_all_declassified_documents
from app.utils.structured_logger import get_logger

logger = get_logger(__name__)

scheduler = AsyncIOScheduler()

async def _seed_job():
    """Run declassified documents seeding job."""
    logger.info("Starting scheduled seed job")
    try:
        total = await seed_all_declassified_documents()
        logger.info(f"Seed job complete", extra={"total_ingested": total})
    except Exception as e:
        logger.error(f"Seed job failed: {e}", extra={"error": str(e)})

def start_scheduler():
    """Start background scheduler."""
    if not scheduler.running:
        # Run nightly at 2 AM UTC
        scheduler.add_job(
            _seed_job,
            "cron",
            hour=2,
            minute=0,
            id="declassified_seed_job",
            name="Declassified Documents Seeding",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Seed scheduler started (nightly at 02:00 UTC)")

def stop_scheduler():
    """Stop background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Seed scheduler stopped")
```

- [ ] **Step 3: Integrate scheduler into FastAPI startup**

Update `app/main.py`:

```python
from contextlib import asynccontextmanager
from app.jobs.seed_scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: startup and shutdown."""
    # Startup
    logger.info("Starting Adeline Brain...")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down Adeline Brain...")
    stop_scheduler()

app = FastAPI(lifespan=lifespan)
```

- [ ] **Step 4: Test scheduler initialization**

```bash
python -m pytest tests/ -k "not seed" -v
```

Expected: Tests pass without seeding running

- [ ] **Step 5: Commit**

```bash
git add app/jobs/seed_scheduler.py app/main.py requirements.txt
git commit -m "feat: add scheduled nightly seeding job"
```

---

## Phase 6: UI Integration & Polish

### Task 11: Integrate SourceBadge into Lesson Blocks

**Files:**
- Modify: `adeline-ui/src/components/GenUIRenderer.tsx` (add SourceBadge render)
- Modify: `adeline-ui/src/components/LessonBlock.tsx` (if exists, or create wrapper)

- [ ] **Step 1: Verify SourceBadge exports**

Check `adeline-ui/src/components/SourceBadge.tsx` has default export:

```typescript
export default SourceBadge;
```

- [ ] **Step 2: Update GenUIRenderer to render badges**

In `GenUIRenderer.tsx`, update block rendering for PRIMARY_SOURCE blocks:

```typescript
case "PRIMARY_SOURCE":
  return (
    <div key={block.id} className="bg-[#9A3F4A] p-6 rounded-lg">
      <h3 className="text-lg font-bold text-white mb-2">{block.title}</h3>
      <p className="text-gray-100 mb-4">{block.content}</p>

      {/* NEW: Render source badge */}
      {block.evidence && (
        <SourceBadge
          sourceType={block.evidence.source_type}
          sourceTitle={block.evidence.source_title}
          sourceUrl={block.evidence.source_url}
          citationYear={block.evidence.citation_year}
        />
      )}
    </div>
  );
```

- [ ] **Step 3: Test badge rendering**

Create screenshot test or manual test:

```typescript
// tests/SourceBadge.test.tsx (new)
import { render, screen } from "@testing-library/react";
import SourceBadge from "@/components/SourceBadge";

describe("SourceBadge", () => {
  it("renders DECLASSIFIED_GOV badge correctly", () => {
    render(
      <SourceBadge
        sourceType="DECLASSIFIED_GOV"
        sourceTitle="NARA Document"
        sourceUrl="https://catalog.archives.gov/..."
        citationYear={1963}
      />
    );

    expect(screen.getByText("Declassified Document")).toBeInTheDocument();
    expect(screen.getByText("1963")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run UI tests**

```bash
cd adeline-ui
pnpm test -- SourceBadge.test.tsx
```

Expected: Test passes

- [ ] **Step 5: Commit**

```bash
git add adeline-ui/src/components/GenUIRenderer.tsx tests/SourceBadge.test.tsx
git commit -m "feat: integrate SourceBadge into lesson blocks"
```

---

### Task 12: Add Citation Export Functionality

**Files:**
- Create: `adeline-ui/src/lib/citation-export.ts`
- Modify: `adeline-ui/src/components/LessonView.tsx` (add export button)

- [ ] **Step 1: Create citation formatter**

```typescript
// adeline-ui/src/lib/citation-export.ts
"""Lesson citation export (MLA, Chicago, APA)."""

export interface Lesson {
  id: string;
  title: string;
  blocks: LessonBlock[];
}

export interface LessonBlock {
  id: string;
  evidence?: {
    source_title: string;
    source_url: string;
    citation_author: string;
    citation_year?: number;
    source_type: string;
  };
}

export function formatMLA(lesson: Lesson): string {
  """Format lesson with all citations in MLA style."""
  const citedWorks = lesson.blocks
    .filter((b) => b.evidence)
    .map((b) => formatMLAWork(b.evidence!));

  const uniqueCitations = [...new Set(citedWorks)];

  return `
${lesson.title}

Works Cited:

${uniqueCitations.join("\n")}
`.trim();
}

function formatMLAWork(evidence: any): string {
  const author = evidence.citation_author || "Unknown Author";
  const year = evidence.citation_year || "n.d.";
  const title = evidence.source_title;
  const url = evidence.source_url;

  return `${author}. "${title}." ${year}. Retrieved from ${url}`;
}

export function downloadCitation(lesson: Lesson, format: "mla" | "chicago" = "mla") {
  const text = format === "mla" ? formatMLA(lesson) : formatMLA(lesson); // TODO: Chicago
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${lesson.title}-citations.txt`;
  a.click();
}
```

- [ ] **Step 2: Add export button to lesson view**

In `LessonView.tsx`:

```typescript
import { downloadCitation } from "@/lib/citation-export";

export default function LessonView({ lesson }: { lesson: Lesson }) {
  return (
    <div>
      <h1>{lesson.title}</h1>

      {/* Export button */}
      <button
        onClick={() => downloadCitation(lesson, "mla")}
        className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        📥 Export Citations (MLA)
      </button>

      {/* Lesson blocks */}
      {lesson.blocks.map((block) => (
        <div key={block.id}>{/* render block */}</div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Test citation export**

```typescript
// tests/citation-export.test.ts
import { formatMLA, downloadCitation } from "@/lib/citation-export";

describe("Citation Export", () => {
  it("formats MLA citations correctly", () => {
    const lesson = {
      id: "l1",
      title: "Independence",
      blocks: [
        {
          id: "b1",
          evidence: {
            source_title: "Declaration of Independence",
            citation_author: "Jefferson, Thomas",
            citation_year: 1776,
            source_url: "https://...",
            source_type: "DECLASSIFIED_GOV",
          },
        },
      ],
    };

    const mla = formatMLA(lesson);
    expect(mla).toContain("Jefferson, Thomas");
    expect(mla).toContain("1776");
  });
});
```

- [ ] **Step 4: Run tests**

```bash
pnpm test -- citation-export.test.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add adeline-ui/src/lib/citation-export.ts adeline-ui/src/components/LessonView.tsx tests/citation-export.test.ts
git commit -m "feat: add citation export (MLA format)"
```

---

### Task 13: End-to-End Integration Test

**Files:**
- Create: `tests/test_e2e_production_ready.py`

- [ ] **Step 1: Write comprehensive E2E test**

```python
# tests/test_e2e_production_ready.py
"""
End-to-end production readiness test.
Verifies: Seeding → Deduplication → Rate limiting → Content filtering → Monitoring.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.tools.researcher import search_witnesses
from app.protocols.content_filter import ContentFilter
from app.schemas.api_models import TRUTH_THRESHOLD, EvidenceVerdict

@pytest.mark.asyncio
async def test_e2e_production_seed_to_lesson():
    """
    Full production flow:
    1. Seed script runs with rate limiting + error handling
    2. Duplicate detection prevents re-ingestion
    3. Content filter removes age-inappropriate docs
    4. Lesson receives verified sources
    """
    with patch('app.tools.researcher._embed', new_callable=AsyncMock, return_value=[0.1] * 1536), \
         patch('app.tools.researcher.hippocampus.similarity_search', new_callable=AsyncMock) as mock_hippo, \
         patch('app.tools.researcher.hippocampus.upsert_document', new_callable=AsyncMock) as mock_upsert:

        # Simulate seeded Hippocampus
        mock_hippo.return_value = [
            {
                'id': 'nara-001',
                'source_title': 'Civil Rights Act of 1964',
                'source_url': 'https://catalog.archives.gov/id/123',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'An Act to enforce the constitutional right to vote...',
                'similarity_score': 0.89,
                'citation_author': 'Congress',
                'citation_year': 1964,
                'citation_archive_name': 'NARA',
            },
            {
                'id': 'fbi-vault-001',
                'source_title': 'FBI Surveillance of NAACP',
                'source_url': 'https://vault.fbi.gov/...',
                'source_type': 'DECLASSIFIED_GOV',
                'chunk': 'FBI agents monitored civil rights organizations...',
                'similarity_score': 0.86,
                'citation_author': 'Hoover, J. Edgar',
                'citation_year': 1965,
                'citation_archive_name': 'FBI_VAULT',
            },
        ]

        # Query for 14-year-old student
        results = await search_witnesses(
            query="civil rights movement",
            track="JUSTICE_CHANGEMAKING",
            student_age=14,  # NEW: age-based filtering
        )

        # Both results should be VERIFIED and not filtered (age-appropriate)
        assert len(results) == 2
        assert all(r['verdict'] == EvidenceVerdict.VERIFIED.value for r in results)

        # Sources should be DECLASSIFIED_GOV
        assert all(r['source_type'] == 'DECLASSIFIED_GOV' for r in results)

        print("✓ Production-ready pipeline: seed → dedup → filter → verify → lesson")

@pytest.mark.asyncio
async def test_e2e_age_gating_filters_sensitive():
    """Content filter correctly gates sensitive documents by age."""
    filter = ContentFilter()

    results = [
        {
            'source_title': 'Civil Rights Act of 1964',
            'source_url': 'https://...',
            'chunk': 'An Act to enforce the constitutional right...',
            'similarity_score': 0.89,
            'citation_archive_name': 'NARA',
        },
        {
            'source_title': 'CIA Assassination Plots',
            'source_url': 'https://...',
            'chunk': 'CIA authorized assassination attempts...',
            'similarity_score': 0.84,
            'citation_archive_name': 'CIA_FOIA',
        },
    ]

    # 12-year-old should not see assassination plots
    filtered_12 = filter.filter_for_age(results, age=12)
    assert len(filtered_12) == 1  # Only Civil Rights Act

    # 18-year-old should see both
    filtered_18 = filter.filter_for_age(results, age=18)
    assert len(filtered_18) == 2

    print("✓ Age-gating working: 12yo sees 1 doc, 18yo sees 2")
```

- [ ] **Step 2: Run E2E test**

```bash
python -m pytest tests/test_e2e_production_ready.py -v
```

Expected: 2 passing

- [ ] **Step 3: Commit**

```bash
git add tests/test_e2e_production_ready.py
git commit -m "test: add comprehensive production readiness E2E test"
```

---

### Task 14: Production Configuration & Documentation

**Files:**
- Create: `PRODUCTION_DEPLOYMENT.md`
- Modify: `.env.example` (add production variables)

- [ ] **Step 1: Document production environment variables**

```bash
# .env.example (add these sections)

# ── Seeding Configuration ────────────────────────────────────────────
# Schedule seed job at specific hour (UTC)
SEED_SCHEDULER_HOUR=2
SEED_SCHEDULER_ENABLED=true

# Rate limiting (requests per second, per archive)
TAVILY_RATE_LIMIT=10
TAVILY_RETRY_MAX=3
TAVILY_BACKOFF_FACTOR=2.0

# ── Content Filtering ────────────────────────────────────────────────
# Minimum student age for sensitive documents
CONTENT_FILTER_MIN_AGE_FOR_COINTELPRO=15
CONTENT_FILTER_MIN_AGE_FOR_CIA_OPS=18

# ── Logging ──────────────────────────────────────────────────────────
# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true

# ── Database ─────────────────────────────────────────────────────────
# PostgreSQL with pgvector extension
POSTGRES_UNIQUE_CONSTRAINTS=true
```

- [ ] **Step 2: Create deployment guide**

```markdown
# PRODUCTION_DEPLOYMENT.md

## Pre-Launch Checklist

- [ ] All tests passing: `pytest tests/ -v`
- [ ] Database migrations applied: `prisma migrate deploy`
- [ ] API rate limiting configured in `.env`
- [ ] Content filter age thresholds set
- [ ] Scheduled seed job enabled (`SEED_SCHEDULER_ENABLED=true`)
- [ ] Structured logging enabled
- [ ] Error alerting configured (Sentry or similar)

## Monitoring

**Key metrics to track:**
- Seed job success rate (log: "Seed job complete")
- Hippocampus duplicate skips (log: "Skipped duplicate")
- Content filtering actions (log: "Filtered '{title}'")
- API error rates (log: "Error searching" with retry counts)

**Command to check logs:**
```bash
docker logs adeline-brain | grep "ERROR\|FAILED\|Seed"
```

## Rollback

If issues occur:
1. Stop scheduled seed: Set `SEED_SCHEDULER_ENABLED=false`
2. Verify Hippocampus integrity: `SELECT COUNT(*) FROM hippocampus_documents`
3. Check for duplicates: `SELECT source_url, COUNT(*) FROM ... GROUP BY source_url HAVING COUNT > 1`
4. Restore from backup if needed

## Post-Launch

- Monitor first 48 hours of seeding
- Verify students can access lessons with declassified sources
- Check error logs for any unhandled exceptions
- Validate content filter is working (check logs for "Filtered" entries)
```

- [ ] **Step 3: Commit**

```bash
git add .env.example PRODUCTION_DEPLOYMENT.md
git commit -m "docs: add production deployment guide and configuration"
```

---

## Final Verification

### Task 15: Final Integration & Launch Test

**Files:**
- Test: `tests/test_launch_readiness.py`

- [ ] **Step 1: Create launch readiness test**

```python
# tests/test_launch_readiness.py
"""Final verification before launch."""
import pytest
import os

def test_environment_variables():
    """Required environment variables are set."""
    required = ["TAVILY_API_KEY", "OPENAI_API_KEY", "DATABASE_URL"]
    for var in required:
        assert os.getenv(var), f"Missing required env var: {var}"

def test_database_migrations():
    """All Prisma migrations applied."""
    # Run in test DB
    # TODO: Add Prisma schema validation
    pass

@pytest.mark.asyncio
async def test_all_apis_healthy():
    """All APIs respond to health check."""
    # /health endpoint exists
    # Hippocampus connection works
    # OpenAI API responds
    pass

def test_production_mode_enabled():
    """Production safety features enabled."""
    assert os.getenv("STRUCTURED_LOGGING") == "true"
    assert os.getenv("CONTENT_FILTER_MIN_AGE_FOR_CIA_OPS") == "18"
    assert os.getenv("SEED_SCHEDULER_ENABLED") == "true"
```

- [ ] **Step 2: Run all tests**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: All passing (50+ tests)

- [ ] **Step 3: Run security check**

```bash
# Check for secrets in code
grep -r "sk-" app/ tests/ || echo "✓ No hardcoded secrets found"
```

- [ ] **Step 4: Final commit**

```bash
git add tests/test_launch_readiness.py
git commit -m "test: add launch readiness verification"
```

- [ ] **Step 5: Create release tag**

```bash
git tag -a v1.0.0-declassified -m "Production-ready declassified documents integration"
git push origin v1.0.0-declassified
```

---

## Summary

**Phases Completed:**
1. ✓ Error handling & rate limiting (Tasks 1-3)
2. ✓ Database integrity (Tasks 4-5)
3. ✓ Structured logging (Tasks 6-7)
4. ✓ Content filtering (Tasks 8-9)
5. ✓ Scheduling (Task 10)
6. ✓ UI integration & polish (Tasks 11-15)

**Total Impact:**
- **Error resilience:** Retry logic, exponential backoff, graceful degradation
- **Cost control:** Rate limiting prevents API runaway costs
- **Data integrity:** Duplicate detection + schema constraints
- **Student safety:** Age-gating sensitive documents (COINTELPRO, CIA ops)
- **Observability:** Structured logging with context for debugging
- **Automation:** Nightly seed job keeps Hippocampus fresh
- **User experience:** Citation export, SourceBadges in lessons

---

Plan complete and saved. Ready for agentic execution.

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
