"""
Justice Document Parser — Extract and chunk documents for JUSTICE_CHANGEMAKING track.

Handles:
- Lobbying disclosure forms
- Civil rights testimonies
- Legislative history
- Court opinions
- Investigative reports
"""
import re
from typing import List, Dict, Optional
from datetime import datetime


def parse_lobbying_disclosure(text: str, metadata: Dict) -> List[Dict]:
    """
    Parse lobbying disclosure forms.
    Extracts registrant, client, issues, and expenditures.
    """
    chunks = []
    
    # Split by sections if present
    sections = re.split(r'\n(?=SECTION \d+|PART [A-Z])', text)
    
    for i, section in enumerate(sections):
        if len(section.strip()) < 100:
            continue
            
        # Extract key information
        registrant = _extract_field(section, r'Registrant[:\s]+([^\n]+)')
        client = _extract_field(section, r'Client[:\s]+([^\n]+)')
        issues = _extract_field(section, r'Issues?[:\s]+([^\n]+)')
        
        chunk_text = section.strip()
        
        # Add context header
        header = f"Lobbying Disclosure"
        if registrant:
            header += f" - Registrant: {registrant}"
        if client:
            header += f", Client: {client}"
        if issues:
            header += f", Issues: {issues}"
        
        chunks.append({
            "text": f"{header}\n\n{chunk_text}",
            "metadata": {
                **metadata,
                "chunk_index": i,
                "registrant": registrant,
                "client": client,
                "issues": issues,
            }
        })
    
    return chunks if chunks else [{"text": text, "metadata": metadata}]


def parse_civil_rights_testimony(text: str, metadata: Dict) -> List[Dict]:
    """
    Parse civil rights testimonies and oral histories.
    Preserves speaker context and historical significance.
    """
    chunks = []
    
    # Try to split by speaker if interview format
    speaker_pattern = r'\n([A-Z\s]+):\s+'
    parts = re.split(speaker_pattern, text)
    
    if len(parts) > 3:  # Likely interview format
        current_speaker = None
        current_text = []
        
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Speaker name
                if current_speaker and current_text:
                    chunks.append({
                        "text": f"{current_speaker}: {' '.join(current_text)}",
                        "metadata": {**metadata, "speaker": current_speaker}
                    })
                current_speaker = part.strip()
                current_text = []
            else:  # Speaker text
                current_text.append(part.strip())
        
        # Add final chunk
        if current_speaker and current_text:
            chunks.append({
                "text": f"{current_speaker}: {' '.join(current_text)}",
                "metadata": {**metadata, "speaker": current_speaker}
            })
    else:
        # Not interview format - chunk by paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        for i, para in enumerate(paragraphs):
            chunks.append({
                "text": para,
                "metadata": {**metadata, "chunk_index": i}
            })
    
    return chunks if chunks else [{"text": text, "metadata": metadata}]


def parse_court_opinion(text: str, metadata: Dict) -> List[Dict]:
    """
    Parse court opinions and legal decisions.
    Preserves case citations and legal reasoning.
    """
    chunks = []
    
    # Extract case name and citation
    case_name = _extract_field(text, r'([A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+)')
    citation = _extract_field(text, r'(\d+\s+[A-Z\.]+\s+\d+)')
    
    # Split by major sections (Opinion, Dissent, Concurrence)
    section_pattern = r'\n(?=(?:OPINION|DISSENT|CONCURRENCE|MAJORITY|PLURALITY))'
    sections = re.split(section_pattern, text)
    
    for i, section in enumerate(sections):
        if len(section.strip()) < 200:
            continue
        
        # Determine section type
        section_type = "Opinion"
        if re.match(r'DISSENT', section, re.IGNORECASE):
            section_type = "Dissent"
        elif re.match(r'CONCURRENCE', section, re.IGNORECASE):
            section_type = "Concurrence"
        
        header = f"{case_name or 'Court Opinion'}"
        if citation:
            header += f" ({citation})"
        header += f" - {section_type}"
        
        chunks.append({
            "text": f"{header}\n\n{section.strip()}",
            "metadata": {
                **metadata,
                "case_name": case_name,
                "citation": citation,
                "section_type": section_type,
                "chunk_index": i,
            }
        })
    
    return chunks if chunks else [{"text": text, "metadata": metadata}]


def parse_legislative_history(text: str, metadata: Dict) -> List[Dict]:
    """
    Parse legislative history documents (committee reports, floor debates).
    Preserves bill numbers and legislative context.
    """
    chunks = []
    
    # Extract bill number
    bill_number = _extract_field(text, r'((?:H\.R\.|S\.) \d+)')
    
    # Split by speaker in floor debates
    speaker_pattern = r'\n((?:Mr\.|Mrs\.|Ms\.|Senator|Representative)\s+[A-Z]+):\s+'
    parts = re.split(speaker_pattern, text)
    
    if len(parts) > 3:  # Floor debate format
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                speaker = parts[i].strip()
                statement = parts[i + 1].strip()
                
                if len(statement) > 100:
                    header = f"Legislative Debate"
                    if bill_number:
                        header += f" on {bill_number}"
                    header += f" - {speaker}"
                    
                    chunks.append({
                        "text": f"{header}\n\n{statement}",
                        "metadata": {
                            **metadata,
                            "bill_number": bill_number,
                            "speaker": speaker,
                        }
                    })
    else:
        # Committee report format - chunk by sections
        section_pattern = r'\n(?=[A-Z][A-Z\s]+\n)'
        sections = re.split(section_pattern, text)
        
        for i, section in enumerate(sections):
            if len(section.strip()) > 200:
                chunks.append({
                    "text": section.strip(),
                    "metadata": {**metadata, "bill_number": bill_number, "chunk_index": i}
                })
    
    return chunks if chunks else [{"text": text, "metadata": metadata}]


def parse_investigative_report(text: str, metadata: Dict) -> List[Dict]:
    """
    Parse investigative journalism and research reports.
    Preserves findings and evidence structure.
    """
    chunks = []
    
    # Split by major sections
    section_pattern = r'\n(?=[A-Z][A-Z\s]{3,}\n|CHAPTER \d+|SECTION \d+)'
    sections = re.split(section_pattern, text)
    
    for i, section in enumerate(sections):
        if len(section.strip()) < 200:
            continue
        
        # Extract section title
        title_match = re.match(r'^([A-Z][A-Z\s]{3,})', section)
        section_title = title_match.group(1).strip() if title_match else None
        
        header = "Investigative Report"
        if section_title:
            header += f" - {section_title}"
        
        chunks.append({
            "text": f"{header}\n\n{section.strip()}",
            "metadata": {
                **metadata,
                "section_title": section_title,
                "chunk_index": i,
            }
        })
    
    return chunks if chunks else [{"text": text, "metadata": metadata}]


def chunk_justice_document(
    text: str,
    source_type: str,
    metadata: Optional[Dict] = None
) -> List[Dict]:
    """
    Main entry point for chunking justice documents.
    Routes to appropriate parser based on source type.
    """
    metadata = metadata or {}
    metadata["source_type"] = source_type
    metadata["parsed_at"] = datetime.utcnow().isoformat()
    
    # Route to appropriate parser
    if source_type == "lobbying_disclosure":
        return parse_lobbying_disclosure(text, metadata)
    elif source_type == "civil_rights_testimony":
        return parse_civil_rights_testimony(text, metadata)
    elif source_type == "court_opinion":
        return parse_court_opinion(text, metadata)
    elif source_type == "legislative_history":
        return parse_legislative_history(text, metadata)
    elif source_type == "investigative_report":
        return parse_investigative_report(text, metadata)
    else:
        # Generic chunking - split by paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        return [
            {"text": para, "metadata": {**metadata, "chunk_index": i}}
            for i, para in enumerate(paragraphs)
        ]


# ── Helper Functions ──────────────────────────────────────────────────────────

def _extract_field(text: str, pattern: str) -> Optional[str]:
    """Extract a field using regex pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove page numbers
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    # Remove headers/footers
    text = re.sub(r'\n\s*Page \d+ of \d+\s*\n', '\n', text)
    return text.strip()
