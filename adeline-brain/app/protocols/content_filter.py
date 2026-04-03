"""Content filtering protocol for age-appropriate document access."""
from typing import Dict, Optional

# Sensitive keywords mapped to minimum age gate
# Students below this age will not see documents containing these keywords
SENSITIVE_KEYWORDS = {
    # Justice track (power capture, surveillance, human rights violations)
    "cointelpro": 14,  # FBI surveillance of civil rights groups → ages 14+
    "assassination": 15,  # Political/state assassination plots → ages 15+
    "torture": 15,  # Enhanced interrogation / torture → ages 15+
    "surveillance": 13,  # Government surveillance (lower threshold for awareness) → ages 13+

    # Health track (sensitive medical content)
    "abortion": 14,  # Reproductive health decisions → ages 14+
    "euthanasia": 15,  # End-of-life decisions → ages 15+
    "substance_abuse": 13,  # Drug/alcohol addiction → ages 13+

    # Other sensitive topics
    "sexual_abuse": 15,  # Child exploitation, sexual assault → ages 15+
    "genocide": 14,  # Mass atrocities → ages 14+
    "war_crimes": 14,  # International humanitarian law violations → ages 14+
}


def should_return_document(
    document: Dict,
    student_age: Optional[int] = None,
) -> bool:
    """
    Determine if a document should be returned to a student based on age.

    Implements age-gating for sensitive topics. If student_age is None,
    no filtering is applied (assumes no age restriction needed).

    Args:
        document: Dictionary with 'source_title' and 'chunk' fields
        student_age: Student's age in years (None = no filtering)

    Returns:
        True if document should be returned, False if filtered

    Example:
        doc = {"source_title": "COINTELPRO", "chunk": "..."}
        should_return_document(doc, student_age=10)  # False
        should_return_document(doc, student_age=16)  # True
        should_return_document(doc, student_age=None) # True (no filtering)
    """
    # If no age specified, don't filter (assume adult access)
    if student_age is None:
        return True

    # Combine title and chunk for keyword matching
    text_to_search = (
        (document.get("source_title", "") or "") + " " +
        (document.get("chunk", "") or "")
    ).lower()

    # Check for sensitive keywords
    for keyword, min_age in SENSITIVE_KEYWORDS.items():
        if keyword in text_to_search:
            # If student is below minimum age for this keyword, filter it
            if student_age < min_age:
                return False

    # No sensitive keywords found, or student is old enough
    return True
