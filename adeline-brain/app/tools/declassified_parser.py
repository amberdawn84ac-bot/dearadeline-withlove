"""
Parser for declassified government documents from various archives.

Converts raw documents from government archives (NARA, CIA FOIA, FBI Vault,
Congressional Record, Federal Register, DNSA) into standardized chunks
suitable for embedding and storage in Hippocampus.

Input: Raw document text from various archives (HTML, PDF text, plain text)
Processing:
  - Remove boilerplate (headers, footers, page breaks, classification marks)
  - Chunk text into segments (500-1000 chars, respecting sentence boundaries)
  - Extract metadata (title, date, author, classification status)
  - Normalize whitespace and formatting

Output: List of ParsedChunk objects with chunk_text + metadata
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ParsedChunk:
    """A chunk of parsed document text with metadata."""
    chunk_text: str          # Cleaned, 500-1000 char segment
    metadata: dict = field(default_factory=dict)  # {archive_name, title, date, author, classification, source_url}


# ── Text cleaning ──────────────────────────────────────────────────────────

def clean_document_text(raw_text: str) -> str:
    """
    Remove boilerplate from government documents:
    - Classification marks (CLASSIFIED, SECRET, DECLASSIFIED)
    - Page breaks and formatting lines
    - Headers/footers
    - Multiple blank lines
    """
    text = raw_text

    # Remove classification marks and related boilerplate
    text = re.sub(r'(CLASSIFIED|SECRET|TOP SECRET|CONFIDENTIAL|UNCLASSIFIED|DECLASSIFIED)[^\n]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(NOFORN|FOUO|FOR OFFICIAL USE ONLY)[^\n]*', '', text)

    # Remove page break patterns (ASCII and Unicode box-drawing)
    text = re.sub(r'[=\-═╔╗╚╝║╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬]{5,}', '', text)
    text = re.sub(r'Page \d+', '', text, flags=re.IGNORECASE)

    # Remove release/authority lines
    text = re.sub(r'(Released|Authority|RIF Request)[^\n]*', '', text, flags=re.IGNORECASE)

    # Normalize whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple blank lines → double newline
    text = re.sub(r'[ \t]+', ' ', text)       # Multiple spaces → single space

    return text.strip()


# ── Text chunking ──────────────────────────────────────────────────────────

def chunk_text_preserving_sentences(
    text: str,
    min_chunk_size: int = 500,
    max_chunk_size: int = 1000,
) -> list[str]:
    """
    Split text into chunks that respect sentence boundaries.
    Sentences are separated by . ! ?

    Args:
        text: The text to chunk
        min_chunk_size: Minimum characters per chunk (unless single sentence < 100 chars)
        max_chunk_size: Maximum characters per chunk

    Returns:
        List of text chunks, each ending with sentence terminator
    """
    # Split by sentence
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Add sentence to current chunk
        if current_chunk:
            test_chunk = current_chunk + " " + sentence
        else:
            test_chunk = sentence

        if len(test_chunk) <= max_chunk_size:
            current_chunk = test_chunk
        else:
            # Current chunk is full, save it
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence

    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)

    # Filter by minimum size (unless very short document)
    result = [c.strip() for c in chunks if len(c.strip()) >= min_chunk_size or len(chunks) == 1]
    return result if result else []


# ── Metadata extraction ────────────────────────────────────────────────────

def extract_date(text: str) -> Optional[str]:
    """
    Extract date from document text. Returns YYYY-MM-DD format.

    Supports patterns like:
    - DATE: January 15, 1963
    - 15 January 1963
    - January 15, 1963
    """
    # Try common patterns
    patterns = [
        r'DATE:\s*([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
        r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                # Parse and normalize to ISO format
                date_str = ' '.join(match.groups())
                parsed = datetime.strptime(date_str, '%B %d %Y')
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                try:
                    # Try abbreviated month
                    parsed = datetime.strptime(date_str, '%b %d %Y')
                    return parsed.strftime('%Y-%m-%d')
                except ValueError:
                    continue

    return None


def extract_metadata(text: str, archive_name: str, source_url: str) -> dict:
    """
    Extract metadata from document text.

    Returns dict with:
    - archive_name: The archive this document came from
    - source_url: URL to the source document
    - title: Document title/subject
    - date: Publication/classification date (YYYY-MM-DD)
    - author: Author or originating official
    - classification: Classification status
    - subject: Document subject line
    """
    metadata = {
        'archive_name': archive_name,
        'source_url': source_url,
        'title': '',
        'date': None,
        'author': '',
        'classification': '',
        'subject': '',
    }

    # Extract date
    date = extract_date(text)
    if date:
        metadata['date'] = date

    # Extract author (FROM: or by pattern)
    author_match = re.search(r'FROM:\s*([^\n,]+)', text, flags=re.IGNORECASE)
    if not author_match:
        # Try pattern: Name, Title
        author_match = re.search(r'^([A-Z][a-z]+\s+[A-Z][a-z]+),\s*([A-Za-z\s]+(?:Director|Secretary|Chairman))', text, flags=re.MULTILINE)

    if author_match:
        metadata['author'] = author_match.group(1).strip()

    # Extract subject
    subject_match = re.search(r'SUBJECT:\s*([^\n]+)', text, flags=re.IGNORECASE)
    if subject_match:
        metadata['subject'] = subject_match.group(1).strip()

    # Extract title (SUBJECT if available, else first substantial line)
    if metadata['subject']:
        metadata['title'] = metadata['subject'][:100]
    else:
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 10]
        if lines:
            metadata['title'] = lines[0][:100]

    return metadata


# ── Main parser ────────────────────────────────────────────────────────────

def parse_declassified_document(
    raw_text: str,
    archive_name: str,
    source_url: str,
) -> list[ParsedChunk]:
    """
    Parse a declassified government document into chunks.

    Flow:
    1. Clean boilerplate
    2. Extract metadata
    3. Chunk text respecting sentence boundaries
    4. Create ParsedChunk objects

    Args:
        raw_text: Raw document text from archive
        archive_name: One of: NARA, CIA_FOIA, FBI_VAULT, CONGRESSIONAL_RECORD, FEDERAL_REGISTER, DNSA
        source_url: URL to the source document

    Returns:
        List of ParsedChunk objects ready for embedding + storage.
    """
    # Step 1: Clean
    cleaned = clean_document_text(raw_text)

    # Step 2: Extract metadata
    metadata = extract_metadata(cleaned, archive_name, source_url)

    # Step 3: Chunk text
    chunks = chunk_text_preserving_sentences(cleaned, min_chunk_size=500, max_chunk_size=1000)

    # Handle empty document
    if not chunks:
        logger.warning(f"[Parser] {archive_name}: No chunks produced from {metadata['title']}")
        return []

    # Step 4: Create ParsedChunk objects
    parsed_chunks = [
        ParsedChunk(chunk_text=chunk, metadata=metadata.copy())
        for chunk in chunks
    ]

    logger.info(f"[Parser] {archive_name}: {len(parsed_chunks)} chunks from {metadata['title']}")
    return parsed_chunks
