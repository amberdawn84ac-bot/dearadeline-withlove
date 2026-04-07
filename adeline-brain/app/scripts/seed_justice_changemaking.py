"""
Justice & Change-making Track Seed Script

Seeds Hippocampus with primary sources for JUSTICE_CHANGEMAKING track:
- Lobbying disclosure forms (OpenSecrets, Senate Lobbying Database)
- Civil rights testimonies (Library of Congress)
- Legislative history (Congress.gov, GovTrack)
- Court opinions (CourtListener, Supreme Court)
- Investigative reports (ProPublica, Corporate Accountability)

Uses Tavily API for web search and document acquisition.
Implements rate limiting, error handling, and retry logic.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional

import httpx
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.connections.pgvector_client import hippocampus
from app.tools.justice_parser import chunk_justice_document, clean_text
from app.utils.rate_limiter import TokenBucket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Rate limiting: 5 requests per second for Tavily
rate_limiter = TokenBucket(capacity=5, refill_rate=5)

# Justice-specific search domains
JUSTICE_DOMAINS = {
    "lobbying": [
        "opensecrets.org",
        "senate.gov/legislative/Public_Disclosure/LDA_reports.htm",
        "lobbyingdisclosure.house.gov",
    ],
    "civil_rights": [
        "loc.gov/collections/civil-rights-history-project",
        "archives.gov/research/african-americans",
        "naacp.org",
    ],
    "legislative": [
        "congress.gov",
        "govtrack.us",
        "federalregister.gov",
    ],
    "courts": [
        "courtlistener.com",
        "supremecourt.gov",
        "ca*.uscourts.gov",
    ],
    "investigative": [
        "propublica.org",
        "citizen.org",
        "corpwatch.org",
    ],
}

# Curated search queries for each category
JUSTICE_QUERIES = {
    "lobbying": [
        "pharmaceutical lobbying disclosure 2020-2024",
        "fossil fuel industry lobbying expenditures",
        "tech company lobbying Congress",
        "defense contractor lobbying reports",
        "agricultural lobbying disclosure forms",
    ],
    "civil_rights": [
        "civil rights movement oral histories",
        "voting rights testimonies Congress",
        "desegregation case testimonies",
        "fair housing discrimination cases",
        "employment discrimination testimonies",
    ],
    "legislative": [
        "Clean Air Act legislative history",
        "Affordable Care Act floor debate",
        "Civil Rights Act 1964 committee reports",
        "Dodd-Frank Wall Street Reform debate",
        "Voting Rights Act legislative record",
    ],
    "courts": [
        "Citizens United v FEC opinion",
        "Brown v Board of Education decision",
        "Shelby County v Holder opinion",
        "Roe v Wade Supreme Court decision",
        "Obergefell v Hodges marriage equality",
    ],
    "investigative": [
        "ProPublica pharmaceutical pricing investigation",
        "corporate tax avoidance investigative report",
        "environmental justice pollution study",
        "prison industrial complex investigation",
        "food industry lobbying influence report",
    ],
}


# ── Tavily Search ─────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def search_tavily(
    query: str,
    domains: Optional[List[str]] = None,
    max_results: int = 5
) -> List[Dict]:
    """
    Search using Tavily API with domain filtering.
    Returns list of search results with content.
    """
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set - skipping search")
        return []
    
    await rate_limiter.acquire()
    
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_raw_content": True,
        }
        
        if domains:
            payload["include_domains"] = domains
        
        try:
            response = await client.post(
                "https://api.tavily.com/search",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get("results", []):
                if result.get("raw_content"):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("raw_content", ""),
                        "published_date": result.get("published_date"),
                    })
            
            logger.info(f"[Tavily] Found {len(results)} results for: {query[:50]}...")
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[Tavily] HTTP error: {e.response.status_code}")
            if e.response.status_code == 429:
                await asyncio.sleep(5)  # Rate limit backoff
            raise
        except Exception as e:
            logger.error(f"[Tavily] Search failed: {e}")
            raise


# ── Embedding ─────────────────────────────────────────────────────────────────

async def embed_text(text: str) -> List[float]:
    """Generate embedding using OpenAI text-embedding-3-small."""
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000],  # Truncate to model limit
    )
    return response.data[0].embedding


# ── Seeding Logic ─────────────────────────────────────────────────────────────

async def seed_category(
    category: str,
    queries: List[str],
    domains: List[str],
    source_type: str,
) -> int:
    """
    Seed documents for a specific justice category.
    Returns count of documents seeded.
    """
    logger.info(f"[Justice] Seeding category: {category}")
    total_seeded = 0
    
    for query in queries:
        try:
            # Search for documents
            results = await search_tavily(query, domains=domains, max_results=3)
            
            for result in results:
                try:
                    # Clean and chunk document
                    cleaned_text = clean_text(result["content"])
                    
                    if len(cleaned_text) < 500:
                        logger.debug(f"[Justice] Skipping short document: {result['title']}")
                        continue
                    
                    chunks = chunk_justice_document(
                        cleaned_text,
                        source_type=source_type,
                        metadata={
                            "source_title": result["title"],
                            "source_url": result["url"],
                            "category": category,
                            "published_date": result.get("published_date"),
                        }
                    )
                    
                    # Embed and upsert each chunk
                    for chunk in chunks:
                        try:
                            embedding = await embed_text(chunk["text"])
                            
                            # Determine source type based on category
                            if category == "investigative":
                                source_type = "INVESTIGATIVE_REPORT"
                            elif category == "courts":
                                source_type = "LEGAL_DOCUMENT"
                            elif category == "legislative":
                                source_type = "LEGISLATIVE_RECORD"
                            elif category == "lobbying":
                                source_type = "DISCLOSURE_FORM"
                            elif category == "civil_rights":
                                source_type = "TESTIMONY"
                            else:
                                source_type = "DOCUMENT"
                            
                            await hippocampus.upsert_document(
                                source_id=f"justice-{category}-{hash(chunk['text']) % 1000000}",
                                source_title=chunk["metadata"].get("source_title", result["title"]),
                                source_url=chunk["metadata"].get("source_url", result["url"]),
                                chunk=chunk["text"],
                                embedding=embedding,
                                track="JUSTICE_CHANGEMAKING",
                                citation_author=chunk["metadata"].get("speaker") or chunk["metadata"].get("registrant") or "Unknown",
                                citation_year=_extract_year(result.get("published_date")),
                                citation_archive_name=category.replace("_", " ").title(),
                                source_type=source_type,
                            )
                            
                            total_seeded += 1
                            logger.info(f"[Justice] Seeded chunk from: {result['title'][:60]}...")
                            
                        except Exception as e:
                            logger.error(f"[Justice] Failed to embed/upsert chunk: {e}")
                            continue
                    
                    # Rate limit between documents
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"[Justice] Failed to process document {result['title']}: {e}")
                    continue
            
            # Rate limit between queries
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"[Justice] Failed to search query '{query}': {e}")
            continue
    
    logger.info(f"[Justice] Category '{category}' complete: {total_seeded} chunks seeded")
    return total_seeded


async def main():
    """Main seeding orchestrator."""
    logger.info("[Justice] Starting JUSTICE_CHANGEMAKING track seeding")
    
    # Connect to Hippocampus
    await hippocampus.connect()
    
    total_seeded = 0
    
    # Seed each category
    categories = [
        ("lobbying", JUSTICE_QUERIES["lobbying"], JUSTICE_DOMAINS["lobbying"], "lobbying_disclosure"),
        ("civil_rights", JUSTICE_QUERIES["civil_rights"], JUSTICE_DOMAINS["civil_rights"], "civil_rights_testimony"),
        ("legislative", JUSTICE_QUERIES["legislative"], JUSTICE_DOMAINS["legislative"], "legislative_history"),
        ("courts", JUSTICE_QUERIES["courts"], JUSTICE_DOMAINS["courts"], "court_opinion"),
        ("investigative", JUSTICE_QUERIES["investigative"], JUSTICE_DOMAINS["investigative"], "investigative_report"),
    ]
    
    for category, queries, domains, source_type in categories:
        try:
            count = await seed_category(category, queries, domains, source_type)
            total_seeded += count
        except Exception as e:
            logger.error(f"[Justice] Category '{category}' failed: {e}")
            continue
    
    logger.info(f"[Justice] Seeding complete: {total_seeded} total chunks seeded")


def _extract_year(date_str: Optional[str]) -> Optional[int]:
    """Extract year from date string."""
    if not date_str:
        return None
    try:
        # Try parsing ISO format
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.year
    except:
        # Try extracting 4-digit year
        import re
        match = re.search(r'(19|20)\d{2}', date_str)
        return int(match.group(0)) if match else None


if __name__ == "__main__":
    asyncio.run(main())
