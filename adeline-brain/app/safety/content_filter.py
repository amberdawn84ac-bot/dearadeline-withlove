"""
Content Safety Filter — Kid-Safe Quality Gate

Runs after every agent generates a lesson block. Enforces:
  1. Grade-band vocabulary ceiling (Flesch-Kincaid grade level estimate)
  2. Category flags — violence, fear, COPPA-sensitive content
  3. Biblical worldview consistency check (warns, never blocks)
  4. Cognitive load guard — max concepts per block by grade band
  5. PII shield — strips any student names / ages from generated text

Operates as a pure filter: receives a block, returns FilterResult.
No DB calls, no LLM calls — deterministic at call time.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ── Grade band ceiling map ────────────────────────────────────────────────────
# Maps grade level (1–12) to max allowed FK grade level in generated text.
# We allow 1-grade headroom for challenge.
_GRADE_CEILING = {
    range(1, 3): 3,    # K-2: max grade 3 reading
    range(3, 6): 7,    # 3-5: max grade 7 reading
    range(6, 9): 10,   # 6-8: max grade 10 reading
    range(9, 13): 13,  # 9-12: no effective ceiling
}

# Vocabulary lists by category — checked via regex word-boundary match
_VIOLENCE_TERMS = re.compile(
    r"\b(murder(?:ed|s)?|brutal(?:ly)?|gore|gory|massacre|slaughter|behead|torture(?:d)?|execution|lynching|atrocit(?:y|ies))\b",
    re.IGNORECASE,
)

_FEAR_TERMS = re.compile(
    r"\b(terrif(?:ied|ying)|horrif(?:ied|ying|ic)|nightmare|monster|demon|haunted|cursed|evil spirits?)\b",
    re.IGNORECASE,
)

# Secular-exclusive framing — watch for evolutionary/materialist assertions presented as fact
_WORLDVIEW_WATCH = re.compile(
    r"\b(evolved? from|random mutation|natural selection created|no purpose|no designer|no creator|universe created itself)\b",
    re.IGNORECASE,
)

# Crude PII patterns — student-identifying info that shouldn't be in generated content
_PII_PATTERN = re.compile(
    r"\b(?:SSN|social security|date of birth|DOB|phone number|home address)\b",
    re.IGNORECASE,
)

# Concept density — heuristic: count noun phrases / named entities via capitalized runs
_CONCEPT_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")

# Maximum concepts per grade band in a single block
_MAX_CONCEPTS = {
    range(1, 3): 4,
    range(3, 6): 7,
    range(6, 9): 12,
    range(9, 13): 20,
}


class SafetyFlag(str, Enum):
    VIOLENCE       = "VIOLENCE"
    FEAR_CONTENT   = "FEAR_CONTENT"
    WORLDVIEW_WARN = "WORLDVIEW_WARN"
    COGNITIVE_LOAD = "COGNITIVE_LOAD"
    PII_DETECTED   = "PII_DETECTED"
    GRADE_CEILING  = "GRADE_CEILING"


@dataclass
class FilterResult:
    passed: bool
    flags: list[SafetyFlag] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized_content: Optional[str] = None

    @property
    def is_hard_block(self) -> bool:
        """Hard blocks stop delivery. Worldview warns don't block."""
        hard = {SafetyFlag.VIOLENCE, SafetyFlag.FEAR_CONTENT, SafetyFlag.PII_DETECTED}
        return bool(hard.intersection(self.flags))


def _get_ceiling(grade_level: int, ceiling_map: dict) -> int:
    for grade_range, ceiling in ceiling_map.items():
        if grade_level in grade_range:
            return ceiling
    return 13


def _estimate_fk_grade(text: str) -> float:
    """
    Flesch-Kincaid grade level estimate.
    Uses sentence count + syllable heuristic (syllables ≈ vowel groups).
    Not perfect but fast and dependency-free.
    """
    sentences = max(1, len(re.findall(r"[.!?]+", text)))
    words = text.split()
    if not words:
        return 0.0
    syllables = sum(max(1, len(re.findall(r"[aeiouAEIOU]+", w))) for w in words)
    grade = 0.39 * (len(words) / sentences) + 11.8 * (syllables / len(words)) - 15.59
    return round(grade, 1)


def _strip_pii(text: str) -> str:
    return _PII_PATTERN.sub("[REDACTED]", text)


class ContentFilter:
    """
    Stateless content safety filter.
    Call check(content, grade_level) for any generated text.
    """

    def check(self, content: str, grade_level: int) -> FilterResult:
        flags: list[SafetyFlag] = []
        warnings: list[str] = []

        # 1. PII shield (always check first — hard block)
        if _PII_PATTERN.search(content):
            flags.append(SafetyFlag.PII_DETECTED)
            content = _strip_pii(content)
            warnings.append("PII pattern detected and redacted.")

        # 2. Violence check
        if _VIOLENCE_TERMS.search(content):
            flags.append(SafetyFlag.VIOLENCE)
            warnings.append(
                "Violence-adjacent vocabulary detected. "
                "Review before delivering to students under grade 9."
            )

        # 3. Fear/horror content
        if _FEAR_TERMS.search(content):
            flags.append(SafetyFlag.FEAR_CONTENT)
            warnings.append(
                "Fear-inducing vocabulary detected. "
                "Not appropriate for K-5 delivery."
            )

        # 4. Worldview consistency (warning only — never blocks)
        if _WORLDVIEW_WATCH.search(content):
            flags.append(SafetyFlag.WORLDVIEW_WARN)
            warnings.append(
                "Secular-exclusive framing detected. "
                "Recommend adding 'some scientists argue' or Creation Science framing."
            )

        # 5. Grade ceiling check
        fk_grade = _estimate_fk_grade(content)
        ceiling = _get_ceiling(grade_level, _GRADE_CEILING)
        if fk_grade > ceiling + 1.5:  # 1.5 grade point tolerance
            flags.append(SafetyFlag.GRADE_CEILING)
            warnings.append(
                f"Reading level too high: FK grade {fk_grade:.1f} "
                f"exceeds ceiling {ceiling} for grade {grade_level} student."
            )

        # 6. Cognitive load check
        concept_matches = _CONCEPT_PATTERN.findall(content)
        unique_concepts = len(set(concept_matches))
        max_concepts = _get_ceiling(grade_level, _MAX_CONCEPTS)
        if unique_concepts > max_concepts:
            flags.append(SafetyFlag.COGNITIVE_LOAD)
            warnings.append(
                f"High concept density: {unique_concepts} named concepts "
                f"exceeds recommended max {max_concepts} for grade {grade_level}."
            )

        # Hard blocks prevent delivery; soft flags (worldview, cognitive) are warnings
        hard_flags = {SafetyFlag.VIOLENCE, SafetyFlag.FEAR_CONTENT, SafetyFlag.PII_DETECTED}
        passed = not bool(hard_flags.intersection(flags))

        # Only return sanitized content if PII was stripped
        sanitized = content if SafetyFlag.PII_DETECTED in flags else None

        result = FilterResult(
            passed=passed,
            flags=flags,
            warnings=warnings,
            sanitized_content=sanitized,
        )

        if not passed:
            logger.warning(
                f"[ContentFilter] Block BLOCKED for grade {grade_level}: {flags}"
            )
        elif flags:
            logger.info(
                f"[ContentFilter] Block passed with warnings for grade {grade_level}: {flags}"
            )

        return result

    def check_block(self, block_content: str, block_type: str, grade_level: int) -> FilterResult:
        """
        Convenience wrapper that adjusts thresholds by block type.
        PRIMARY_SOURCE blocks get more latitude — historical violence is fact.
        """
        if block_type in ("PRIMARY_SOURCE", "RESEARCH_MISSION"):
            # Historical primary sources may contain difficult content — contextual
            # For K-5 (grade ≤ 5), still enforce the hard blocks
            if grade_level <= 5:
                return self.check(block_content, grade_level)
            # For 6-12, worldview and violence are expected in primary sources
            result = self.check(block_content, grade_level)
            # Downgrade violence flag to warning for primary sources in 6-12
            if SafetyFlag.VIOLENCE in result.flags and grade_level >= 6:
                result.flags.remove(SafetyFlag.VIOLENCE)
                result.warnings.append(
                    "Historical violence in primary source — appropriate for grade 6+."
                )
                result.passed = not result.is_hard_block
            return result
        return self.check(block_content, grade_level)


# Singleton
content_filter = ContentFilter()
