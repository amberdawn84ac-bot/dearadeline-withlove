"""
External Books Service — Open Library API fallback for low pgvector matches.

Provides seamless external book discovery when internal pgvector search
returns insufficient high-confidence results.
"""

import logging
from typing import List, Dict, Optional
import httpx

logger = logging.getLogger(__name__)

OPEN_LIBRARY_BASE = "https://openlibrary.org"
MIN_CONFIDENCE_THRESHOLD = 0.78


async def fetch_external_books(
    query: str,
    limit: int = 10,
) -> List[Dict]:
    """
    Search Open Library API for books when pgvector returns low-confidence matches.
    
    Maps Open Library results to internal Book format for Discover section compatibility.
    
    Args:
        query: Search query (HyDE-generated hypothetical book summary)
        limit: Maximum number of external books to return
        
    Returns:
        List of book dictionaries matching internal Book format with is_external=True
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Search by subject/topic
            search_url = f"{OPEN_LIBRARY_BASE}/search.json"
            params = {
                "q": query,
                "limit": limit,
                "has_fulltext": "true",  # Only books with readable content
            }
            
            logger.info(f"[ExternalBooks] Querying Open Library: {query[:50]}...")
            response = await client.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            docs = data.get("docs", [])
            books = []
            
            for doc in docs[:limit]:
                # Extract cover URL if available
                cover_id = doc.get("cover_i")
                cover_url = None
                if cover_id:
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                
                # Map to internal Book format
                book = {
                    "id": f"ol:{doc.get('key', '').replace('/works/', '')}",
                    "title": doc.get("title", "Unknown Title"),
                    "author": ", ".join(doc.get("author_name", ["Unknown Author"])),
                    "lexile_level": _estimate_lexile(doc),
                    "grade_band": _infer_grade_band(doc),
                    "track": _infer_track(doc),
                    "cover_url": cover_url,
                    "relevance_score": 0.75,  # Baseline for external matches
                    "source_url": f"{OPEN_LIBRARY_BASE}{doc.get('key', '')}",
                    "source_library": "Open Library",
                    "is_external": True,
                }
                books.append(book)
            
            logger.info(f"[ExternalBooks] Found {len(books)} external books")
            return books
            
    except httpx.TimeoutException:
        logger.error("[ExternalBooks] Open Library API timeout")
        return []
    except httpx.HTTPStatusError as e:
        logger.error(f"[ExternalBooks] Open Library API error: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"[ExternalBooks] Failed to fetch external books: {e}")
        return []


def _estimate_lexile(doc: Dict) -> int:
    """Estimate Lexile level based on Open Library metadata heuristics."""
    subjects = " ".join(doc.get("subject", [])).lower()
    
    # Check for explicit reading level indicators
    if any(x in subjects for x in ["beginning reader", "early reader", "easy reader"]):
        return 250
    if any(x in subjects for x in ["children", "juvenile", "picture book", "ages 4-8"]):
        return 400
    if any(x in subjects for x in ["middle grade", "ages 9-12", "middle school"]):
        return 700
    if any(x in subjects for x in ["young adult", "teen", "ya", "ages 13-17"]):
        return 850
    if any(x in subjects for x in ["college", "university", "academic", "scholarly"]):
        return 1100
    
    # Default based on first publish year (classics tend to be higher)
    year = doc.get("first_publish_year", 2000)
    if year < 1900:
        return 950  # Very old classics
    elif year < 1950:
        return 850  # Mid-century classics
    else:
        return 700  # Modern books


def _infer_grade_band(doc: Dict) -> str:
    """Infer grade band from subjects and reading level."""
    subjects = " ".join(doc.get("subject", [])).lower()
    
    if any(x in subjects for x in ["children", "juvenile", "picture book", "ages 4-8", "early reader"]):
        return "K-2"
    elif any(x in subjects for x in ["middle grade", "ages 9-12", "middle school"]):
        return "3-5"
    elif any(x in subjects for x in ["young adult", "teen", "ya", "ages 13-17", "high school"]):
        return "9-12"
    else:
        return "6-8"


def _infer_track(doc: Dict) -> str:
    """Infer curriculum track from subjects and topics."""
    subjects = " ".join(doc.get("subject", [])).lower()
    
    # Truth-History indicators
    if any(x in subjects for x in [
        "history", "biography", "war", "civilization", "ancient", 
        "medieval", "american history", "world history", "historical"
    ]):
        return "Truth-History"
    
    # Discipleship indicators
    if any(x in subjects for x in [
        "christian", "bible", "theology", "faith", "religion", 
        "spiritual", "devotional", "prayer", "worship"
    ]):
        return "Discipleship"
    
    # Natural Sciences indicators
    if any(x in subjects for x in [
        "science", "nature", "physics", "biology", "chemistry", 
        "astronomy", "earth science", "natural history", "environment"
    ]):
        return "Natural Sciences"
    
    # Applied Mathematics indicators
    if any(x in subjects for x in [
        "mathematics", "math", "geometry", "algebra", "calculus", 
        "statistics", "engineering", "technology"
    ]):
        return "Applied Mathematics"
    
    # Creative Economy indicators
    if any(x in subjects for x in [
        "business", "economics", "finance", "entrepreneurship", 
        "marketing", "management", "career"
    ]):
        return "Creative Economy"
    
    # Health & Wholeness indicators
    if any(x in subjects for x in [
        "health", "medicine", "wellness", "nutrition", "fitness", 
        "mental health", "healing", "holistic"
    ]):
        return "Health_Wholeness"
    
    # Stewardship & Sustainability indicators
    if any(x in subjects for x in [
        "gardening", "agriculture", "sustainability", "homesteading", 
        "permaculture", "ecology", "conservation"
    ]):
        return "Stewardship_Sustainability"
    
    # Default to English Literature for fiction/novels
    if any(x in subjects for x in ["fiction", "novel", "literature", "poetry", "drama"]):
        return "English Literature"
    
    return "English Literature"  # Safe default


async def should_fallback_to_external(pgvector_results: List[Dict]) -> bool:
    """
    Determine if we should fetch external books based on pgvector results.
    
    Triggers if:
    - Fewer than 3 results total
    - Fewer than 3 results with confidence > MIN_CONFIDENCE_THRESHOLD
    
    Args:
        pgvector_results: Results from internal pgvector semantic search
        
    Returns:
        True if external fallback should be triggered
    """
    if len(pgvector_results) < 3:
        logger.info(f"[ExternalBooks] Triggering fallback: only {len(pgvector_results)} internal results")
        return True
    
    high_confidence = [
        r for r in pgvector_results 
        if r.get("relevance_score", 0) > MIN_CONFIDENCE_THRESHOLD
    ]
    
    if len(high_confidence) < 3:
        logger.info(
            f"[ExternalBooks] Triggering fallback: only {len(high_confidence)} "
            f"high-confidence results (> {MIN_CONFIDENCE_THRESHOLD})"
        )
        return True
    
    return False
