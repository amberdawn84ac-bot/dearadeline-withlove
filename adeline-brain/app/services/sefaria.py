"""
Sefaria API Integration Service

Fetches biblical text (Everett Fox translation preferred) and commentary from Sefaria.org.
Provides lazy caching to Hippocampus for similarity search capability.

API Documentation: https://github.com/Sefaria/Sefaria-Project/wiki/API-Documentation
"""
import httpx
import logging
import re
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Sefaria API configuration
SEFARIA_API_BASE = "https://www.sefaria.org/api"
EVERETT_FOX_VERSION = "The_Five_Books_of_Moses,_by_Everett_Fox._New_York,_Schocken_Books,_1995"
EVERETT_FOX_PROPHETS = "The_Early_Prophets:_Joshua,_Judges,_Samuel,_and_Kings,_Everett_Fox,_2014"

# HTTP client timeout
API_TIMEOUT = 12.0


async def fetch_biblical_text(ref: str, version: str = EVERETT_FOX_VERSION) -> Optional[Dict]:
    """
    Fetch biblical text from Sefaria API.
    
    Args:
        ref: Biblical reference (e.g., "Genesis.1.1", "Isaiah.43.1")
        version: Translation version (defaults to Everett Fox)
    
    Returns:
        {
            "ref": "Genesis 1:1",
            "hebrew": "בְּרֵאשִׁית...",
            "english": "When God began to create...",
            "version_title": "The Five Books of Moses, by Everett Fox",
            "url": "https://www.sefaria.org/Genesis.1.1",
            "is_fox": True
        }
        
        Returns None if fetch fails.
    """
    normalized_ref = normalize_reference(ref)
    url = f"{SEFARIA_API_BASE}/texts/{normalized_ref}"
    
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        try:
            # Try with Everett Fox version first
            logger.info(f"[Sefaria] Fetching {normalized_ref} with version {version}")
            resp = await client.get(url, params={"version": f"english|{version}", "context": 0})
            
            if resp.status_code != 200:
                # Fallback: try Early Prophets version
                logger.info(f"[Sefaria] Trying Early Prophets version for {normalized_ref}")
                resp = await client.get(url, params={"version": f"english|{EVERETT_FOX_PROPHETS}", "context": 0})
            
            if resp.status_code != 200:
                # Fallback: get default English + Hebrew
                logger.info(f"[Sefaria] Falling back to default version for {normalized_ref}")
                resp = await client.get(url, params={"context": 0})
            
            if resp.status_code != 200:
                logger.error(f"[Sefaria] Failed to fetch {normalized_ref}: HTTP {resp.status_code}")
                return None
            
            data = resp.json()
            
            # Extract text (handle both string and array responses)
            hebrew = extract_text(data.get("he", ""))
            english = extract_text(data.get("text", ""))
            version_title = data.get("versionTitle", "")
            
            # Check if we got Everett Fox
            is_fox = "Everett" in version_title and "Fox" in version_title
            
            result = {
                "ref": data.get("ref", ref),
                "hebrew": hebrew,
                "english": english,
                "version_title": version_title,
                "url": f"https://www.sefaria.org/{normalized_ref}",
                "is_fox": is_fox,
            }
            
            logger.info(f"[Sefaria] Successfully fetched {normalized_ref} (Fox: {is_fox})")
            return result
            
        except Exception as e:
            logger.error(f"[Sefaria] Exception fetching {ref}: {e}")
            return None


async def fetch_commentary(ref: str, commentators: Optional[List[str]] = None) -> List[Dict]:
    """
    Fetch rabbinic commentary for a biblical reference.
    
    Args:
        ref: Biblical reference
        commentators: Optional list of specific commentators (e.g., ["Rashi", "Ibn Ezra"])
    
    Returns:
        List of commentary objects with text and attribution
    """
    normalized_ref = normalize_reference(ref)
    url = f"{SEFARIA_API_BASE}/links/{normalized_ref}"
    
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        try:
            resp = await client.get(url)
            
            if resp.status_code != 200:
                logger.error(f"[Sefaria] Failed to fetch commentary for {normalized_ref}: HTTP {resp.status_code}")
                return []
            
            data = resp.json()
            
            # Filter for commentary links
            commentary = []
            for link in data:
                if link.get("category") == "Commentary":
                    commentator = link.get("collectiveTitle", "")
                    
                    # Filter by commentators if specified
                    if commentators and commentator not in commentators:
                        continue
                    
                    commentary.append({
                        "ref": link.get("sourceRef"),
                        "text": link.get("text", ""),
                        "commentator": commentator,
                    })
            
            logger.info(f"[Sefaria] Found {len(commentary)} commentary entries for {normalized_ref}")
            return commentary
            
        except Exception as e:
            logger.error(f"[Sefaria] Exception fetching commentary for {ref}: {e}")
            return []


async def cache_to_hippocampus(ref: str, text_data: Dict, track: str) -> Optional[str]:
    """
    Lazy seed Sefaria text to Hippocampus for future similarity searches.
    Uses hippocampus.upsert_document() so the pgvector type is handled correctly.
    """
    from app.connections.pgvector_client import hippocampus
    from openai import AsyncOpenAI
    import os

    try:
        # Build chunk with Hebrew + English
        chunk = f"{text_data['ref']}\n\n"
        if text_data['hebrew']:
            chunk += f"Hebrew: {text_data['hebrew']}\n\n"
        chunk += f"English: {text_data['english']}"

        # Generate embedding
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=chunk,
        )
        embedding = resp.data[0].embedding

        # Upsert via the hippocampus client (handles pgvector type correctly)
        doc_id = await hippocampus.upsert_document(
            source_title=f"{text_data['ref']} ({text_data['version_title']})",
            track=track,
            chunk=chunk,
            embedding=embedding,
            source_url=text_data['url'],
            source_type="SEFARIA_TEXT",
            citation_author="Everett Fox (Translator)" if text_data['is_fox'] else "Sefaria",
            citation_year=1995 if text_data['is_fox'] else None,
            citation_archive_name="Sefaria / Schocken Books" if text_data['is_fox'] else "Sefaria.org",
        )

        logger.info(f"[Sefaria] Cached {ref} to Hippocampus: {doc_id}")
        return doc_id

    except Exception as e:
        logger.error(f"[Sefaria] Failed to cache {ref} to Hippocampus: {e}")
        return None


def normalize_reference(ref: str) -> str:
    """
    Normalize biblical reference for Sefaria API.
    
    Examples:
        "Isaiah 43:1" → "Isaiah.43.1"
        "Yeshayahu 43:1" → "Isaiah.43.1"
        "Genesis 1" → "Genesis.1"
    """
    # Map Hebrew names to English
    name_map = {
        "Yeshayahu": "Isaiah",
        "Yirmiyahu": "Jeremiah",
        "Yechezkel": "Ezekiel",
        "Bereshit": "Genesis",
        "Shemot": "Exodus",
        "Vayikra": "Leviticus",
        "Bamidbar": "Numbers",
        "Devarim": "Deuteronomy",
        "Yehoshua": "Joshua",
        "Shoftim": "Judges",
        "Shmuel": "Samuel",
        "Melachim": "Kings",
        "Tehillim": "Psalms",
        "Mishlei": "Proverbs",
    }
    
    for hebrew, english in name_map.items():
        ref = ref.replace(hebrew, english)
    
    # Replace spaces and colons with dots
    ref = ref.replace(" ", ".").replace(":", ".")
    
    return ref


def extract_text(data) -> str:
    """
    Extract text from Sefaria response (handles string, flat list, or nested list).

    Sefaria returns:
    - A string for single verses
    - A flat list of strings for verse ranges (["verse1", "verse2"])
    - A nested list for chapter-level refs ([["v1", "v2"], ["v3"]])
    """
    if isinstance(data, list):
        parts = []
        for item in data:
            if isinstance(item, list):
                parts.extend(str(v) for v in item if v)
            elif item:
                parts.append(str(item))
        return " ".join(parts)
    return str(data) if data else ""


def detect_biblical_reference(topic: str) -> Optional[str]:
    """
    Detect if topic contains a biblical reference.
    
    Args:
        topic: Lesson topic string
    
    Returns:
        Normalized reference or None
        
    Examples:
        "Tell me about Genesis 1:1" → "Genesis.1.1"
        "Isaiah 43:1 - Fear not" → "Isaiah.43.1"
        "Yeshayahu 43" → "Isaiah.43"
    """
    # Pattern: "Book Chapter:Verse" or "Book Chapter"
    # Supports both English and Hebrew book names
    pattern = r'(Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Samuel|Kings|Isaiah|Jeremiah|Ezekiel|Psalms|Proverbs|Yeshayahu|Yirmiyahu|Yechezkel|Bereshit|Shemot|Vayikra|Bamidbar|Devarim|Yehoshua|Shoftim|Shmuel|Melachim|Tehillim|Mishlei)\s+(\d+)(?::(\d+(?:-\d+)?))?'
    
    match = re.search(pattern, topic, re.IGNORECASE)
    if match:
        book, chapter, verse = match.groups()
        ref = f"{book} {chapter}"
        if verse:
            ref += f":{verse}"
        return normalize_reference(ref)
    
    return None


def format_sefaria_content(sefaria_data: Dict, grade_level: str = "8") -> str:
    """
    Format Sefaria text in Adeline's voice for Discipleship.
    
    Args:
        sefaria_data: Result from fetch_biblical_text()
        grade_level: Student grade level for appropriate formatting
    
    Returns:
        Formatted content string ready for NARRATIVE block
    """
    hebrew = sefaria_data['hebrew']
    english = sefaria_data['english']
    ref = sefaria_data['ref']
    
    content = f"**{ref}**\n\n"
    
    if hebrew:
        content += f"*Hebrew:* {hebrew}\n\n"
    
    content += f"{english}\n\n"
    
    if sefaria_data['is_fox']:
        content += "*This is Everett Fox's translation — it preserves the rhythm and feel of the Hebrew original. "
        content += "Fox keeps Hebrew names (YHWH, Ya'akov, Yisrael) and the poetic structure intact.*\n\n"
    
    return content
