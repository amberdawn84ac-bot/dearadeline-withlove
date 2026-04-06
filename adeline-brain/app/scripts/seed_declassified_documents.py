"""
Seed scripts for ingesting declassified government documents into Hippocampus.

Fetches documents from government archives (NARA, CIA FOIA, FBI Vault),
parses them using DeclassifiedDocument parser, embeds with text-embedding-3-small,
and persists to Hippocampus with source_type=DECLASSIFIED_GOV.

Usage:
    python -c "
    import asyncio
    from app.scripts.seed_declassified_documents import seed_all_declassified_documents
    asyncio.run(seed_all_declassified_documents())
    "
"""
import asyncio
import httpx
import logging
import os
import random
from typing import Optional, Callable, Any

from openai import AsyncOpenAI

from app.connections.pgvector_client import hippocampus
from app.tools.declassified_parser import parse_declassified_document
from app.tools.researcher import search_archive_async
from app.schemas.api_models import SourceType
from app.utils.structured_logger import get_structured_logger

logger = logging.getLogger(__name__)

# Lazy-initialize OpenAI client (defer until first use)
openai_client = None


def _get_openai_client():
    """Lazy-initialize OpenAI client on first use."""
    global openai_client
    if openai_client is None:
        openai_client = AsyncOpenAI()
    return openai_client


# ── Retry logic with exponential backoff ──────────────────────────────────

async def _retry_search(
    query: str,
    archive: str,
    max_retries: int,
    search_fn: Callable[..., Any],
    initial_delay: float = 0.5,
    retry_logger: Optional[logging.Logger] = None,
) -> list:
    """
    Retry search function with exponential backoff + jitter.

    Handles transient failures (ConnectionError, TimeoutError) gracefully.
    Non-transient errors are raised immediately without retry.

    Args:
        query: Search query
        archive: Archive name (for logging)
        max_retries: Maximum number of retries (not counting initial attempt)
        search_fn: Async search function to call
        initial_delay: Initial delay in seconds (default 0.5)
        retry_logger: Optional structured logger with context (uses module logger if None)

    Returns:
        List of search results

    Raises:
        ConnectionError if all retries exhausted
        TimeoutError if all retries exhausted
        Other exceptions are raised immediately without retry
    """
    log = retry_logger or logger
    attempt = 0
    while attempt < max_retries:
        try:
            return await search_fn(query)
        except (ConnectionError, TimeoutError) as e:
            attempt += 1
            if attempt >= max_retries:
                raise  # Re-raise on final attempt

            # Exponential backoff: 0.5s, 1s, 2s, 4s... with ±10% jitter
            delay = initial_delay * (2 ** (attempt - 1))
            jitter = delay * 0.1 * (random.random() - 0.5)
            sleep_time = delay + jitter

            log.warning(
                f"Search failed (attempt {attempt}/{max_retries}): {e}. "
                f"Retrying in {sleep_time:.2f}s..."
            )
            await asyncio.sleep(sleep_time)


# ── Search queries tailored to each track ──────────────────────────────────

TRACK_QUERIES = {
    "TRUTH_HISTORY": [
        "American history declassified documents",
        "presidential records foreign policy",
        "government decision-making Cold War",
        "State Department memos diplomatic history",
    ],
    "JUSTICE_CHANGEMAKING": [
        "civil rights movement declassified documents",
        "government surveillance COINTELPRO",
        "regulatory capture legislative history",
        "FBI civil rights surveillance documents",
    ],
}


# ── Utility functions ──────────────────────────────────────────────────────

async def fetch_document_text(url: str, fetch_logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Fetch document text from archive URL.

    Args:
        url: URL to fetch from
        fetch_logger: Optional structured logger with context (uses module logger if None)

    Returns:
        Document text if successful, None on failure
    """
    log = fetch_logger or logger
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                return response.text
            else:
                log.warning(f"HTTP {response.status_code}: {url}")
    except Exception as e:
        log.warning(f"Failed to fetch {url}: {e}")
    return None


# ── Seed functions for individual archives ──────────────────────────────────

async def seed_nara_documents(track: str, limit: int = 10) -> int:
    """
    Seed NARA (National Archives and Records Administration) documents into Hippocampus.

    Searches for documents relevant to the given track with retry logic for transient failures.

    Args:
        track: Track name (TRUTH_HISTORY, JUSTICE_CHANGEMAKING, etc.)
        limit: Max documents to ingest per query

    Returns:
        Number of chunks ingested
    """
    seed_logger = get_structured_logger(
        name="seed_nara",
        track=track,
        archive_name="NARA",
    )

    if not os.getenv("TAVILY_API_KEY"):
        seed_logger.warning("TAVILY_API_KEY not set — skipping NARA seed")
        return 0

    queries = TRACK_QUERIES.get(track, [f"{track} declassified documents"])
    ingested_count = 0

    for query in queries:
        try:
            seed_logger.info(f"Searching: {query}")

            async def nara_search(q):
                return await search_archive_async(q, "NARA")

            results = await _retry_search(
                query=query,
                archive="NARA",
                max_retries=3,
                search_fn=nara_search,
                retry_logger=seed_logger,
            )

            for result in results[:limit]:
                try:
                    url = result.get("url", "")
                    title = result.get("title", "Untitled NARA Document")

                    # Fetch full document text (not just snippet)
                    doc_text = await fetch_document_text(url, fetch_logger=seed_logger)
                    if not doc_text:
                        seed_logger.warning(f"Could not fetch full text for {title}")
                        continue

                    # Parse full document into chunks
                    chunks = parse_declassified_document(
                        raw_text=doc_text,
                        archive_name="NARA",
                        source_url=url,
                    )

                    if not chunks:
                        continue

                    # Embed and persist each chunk
                    for chunk in chunks:
                        try:
                            # Embed with text-embedding-3-small
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
                            seed_logger.info(f"Ingested: {title[:50]}...")

                        except Exception as e:
                            seed_logger.warning(f"Failed to embed/persist chunk: {e}")
                            continue

                except Exception as e:
                    seed_logger.warning(f"Failed to process document {title}: {e}")
                    continue

        except Exception as e:
            seed_logger.error(f"Error searching: {e}")
            continue

    seed_logger.info(f"Seed complete: {ingested_count} chunks ingested")
    return ingested_count


async def seed_cia_foia_documents(track: str, limit: int = 10) -> int:
    """
    Seed CIA FOIA documents into Hippocampus.

    Searches for declassified CIA documents relevant to the given track with retry logic for transient failures.

    Args:
        track: Track name (TRUTH_HISTORY, JUSTICE_CHANGEMAKING, etc.)
        limit: Max documents to ingest per query

    Returns:
        Number of chunks ingested
    """
    seed_logger = get_structured_logger(
        name="seed_cia_foia",
        track=track,
        archive_name="CIA_FOIA",
    )

    if not os.getenv("TAVILY_API_KEY"):
        seed_logger.warning("TAVILY_API_KEY not set — skipping CIA FOIA seed")
        return 0

    queries = TRACK_QUERIES.get(track, [f"{track} CIA documents"])
    ingested_count = 0

    for query in queries:
        try:
            seed_logger.info(f"Searching: {query}")

            async def cia_search(q):
                return await search_archive_async(q, "CIA_FOIA")

            results = await _retry_search(
                query=query,
                archive="CIA_FOIA",
                max_retries=3,
                search_fn=cia_search,
                retry_logger=seed_logger,
            )

            for result in results[:limit]:
                try:
                    url = result.get("url", "")
                    title = result.get("title", "Untitled CIA Document")

                    # Fetch full document text (not just snippet)
                    doc_text = await fetch_document_text(url, fetch_logger=seed_logger)
                    if not doc_text:
                        seed_logger.warning(f"Could not fetch full text for {title}")
                        continue

                    chunks = parse_declassified_document(
                        raw_text=doc_text,
                        archive_name="CIA_FOIA",
                        source_url=url,
                    )

                    if not chunks:
                        continue

                    for chunk in chunks:
                        try:
                            client = _get_openai_client()
                            embedding_response = await client.embeddings.create(
                                model="text-embedding-3-small",
                                input=chunk.chunk_text,
                            )
                            embedding = embedding_response.data[0].embedding

                            doc_id = await hippocampus.upsert_document(
                                source_title=title,
                                track=track,
                                chunk=chunk.chunk_text,
                                embedding=embedding,
                                source_url=url,
                                source_type=SourceType.DECLASSIFIED_GOV.value,
                                citation_author=chunk.metadata.get("author", ""),
                                citation_year=None,
                                citation_archive_name="CIA_FOIA",
                            )
                            ingested_count += 1
                            seed_logger.info(f"Ingested: {title[:50]}...")

                        except Exception as e:
                            seed_logger.warning(f"Failed to embed/persist chunk: {e}")
                            continue

                except Exception as e:
                    seed_logger.warning(f"Failed to process document {title}: {e}")
                    continue

        except Exception as e:
            seed_logger.error(f"Error searching: {e}")
            continue

    seed_logger.info(f"Seed complete: {ingested_count} chunks ingested")
    return ingested_count


async def seed_fbi_vault_documents(track: str, limit: int = 10) -> int:
    """
    Seed FBI Vault documents into Hippocampus.

    Primarily targets JUSTICE_CHANGEMAKING track (surveillance, civil rights, COINTELPRO)
    with retry logic for transient failures.

    Args:
        track: Track name (typically JUSTICE_CHANGEMAKING, TRUTH_HISTORY)
        limit: Max documents to ingest per query

    Returns:
        Number of chunks ingested
    """
    seed_logger = get_structured_logger(
        name="seed_fbi_vault",
        track=track,
        archive_name="FBI_VAULT",
    )

    if not os.getenv("TAVILY_API_KEY"):
        seed_logger.warning("TAVILY_API_KEY not set — skipping FBI Vault seed")
        return 0

    queries = TRACK_QUERIES.get(track, [f"{track} FBI documents"])
    ingested_count = 0

    for query in queries:
        try:
            seed_logger.info(f"Searching: {query}")

            async def fbi_search(q):
                return await search_archive_async(q, "FBI_VAULT")

            results = await _retry_search(
                query=query,
                archive="FBI_VAULT",
                max_retries=3,
                search_fn=fbi_search,
                retry_logger=seed_logger,
            )

            for result in results[:limit]:
                try:
                    url = result.get("url", "")
                    title = result.get("title", "Untitled FBI Document")

                    # Fetch full document text (not just snippet)
                    doc_text = await fetch_document_text(url, fetch_logger=seed_logger)
                    if not doc_text:
                        seed_logger.warning(f"Could not fetch full text for {title}")
                        continue

                    chunks = parse_declassified_document(
                        raw_text=doc_text,
                        archive_name="FBI_VAULT",
                        source_url=url,
                    )

                    if not chunks:
                        continue

                    for chunk in chunks:
                        try:
                            client = _get_openai_client()
                            embedding_response = await client.embeddings.create(
                                model="text-embedding-3-small",
                                input=chunk.chunk_text,
                            )
                            embedding = embedding_response.data[0].embedding

                            doc_id = await hippocampus.upsert_document(
                                source_title=title,
                                track=track,
                                chunk=chunk.chunk_text,
                                embedding=embedding,
                                source_url=url,
                                source_type=SourceType.DECLASSIFIED_GOV.value,
                                citation_author=chunk.metadata.get("author", ""),
                                citation_year=None,
                                citation_archive_name="FBI_VAULT",
                            )
                            ingested_count += 1
                            seed_logger.info(f"Ingested: {title[:50]}...")

                        except Exception as e:
                            seed_logger.warning(f"Failed to embed/persist chunk: {e}")
                            continue

                except Exception as e:
                    seed_logger.warning(f"Failed to process document {title}: {e}")
                    continue

        except Exception as e:
            seed_logger.error(f"Error searching: {e}")
            continue

    seed_logger.info(f"Seed complete: {ingested_count} chunks ingested")
    return ingested_count


# ── Master seed function ──────────────────────────────────────────────────

async def seed_all_declassified_documents() -> int:
    """
    Seed documents from all 3 primary archives for all relevant tracks.

    Runs all seeds in parallel for efficiency.

    Returns:
        Total number of chunks ingested across all archives
    """
    master_logger = get_structured_logger(
        name="seed_all",
    )

    master_logger.info("Starting declassified documents ingestion...")

    # Connect to Hippocampus
    await hippocampus.connect()
    master_logger.info("Connected to Hippocampus")

    tasks = [
        seed_nara_documents(track="TRUTH_HISTORY", limit=5),
        seed_cia_foia_documents(track="TRUTH_HISTORY", limit=5),
        seed_nara_documents(track="JUSTICE_CHANGEMAKING", limit=5),
        seed_cia_foia_documents(track="JUSTICE_CHANGEMAKING", limit=5),
        seed_fbi_vault_documents(track="JUSTICE_CHANGEMAKING", limit=5),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_count = sum(r for r in results if isinstance(r, int))
    master_logger.info(f"Complete: {total_count} total chunks ingested")
    return total_count
