"""
Standards mapper — map tracks and lesson content to OAS codes.
OAS is an overlay (not controlling), but metadata enriches transcripts.
"""
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class StandardsSubject(str, Enum):
    ELA = "ELA"
    SCIENCE = "SCIENCE"
    SOCIAL_STUDIES = "SOCIAL_STUDIES"
    HEALTH = "HEALTH"
    WORLD_LANGUAGES = "WORLD_LANGUAGES"
    MATH = "MATH"
    INFO_LIT = "INFO_LIT"


@dataclass
class OASStandard:
    code: str
    subject: StandardsSubject
    grade_band: str
    strand: str
    description: str
    confidence: float = 0.0


TRACK_TO_SUBJECT: dict[str, StandardsSubject] = {
    "CREATION_SCIENCE": StandardsSubject.SCIENCE,
    "HEALTH_NATUROPATHY": StandardsSubject.HEALTH,
    "HOMESTEADING": StandardsSubject.SCIENCE,
    "GOVERNMENT_ECONOMICS": StandardsSubject.SOCIAL_STUDIES,
    "JUSTICE_CHANGEMAKING": StandardsSubject.SOCIAL_STUDIES,
    "DISCIPLESHIP": StandardsSubject.SOCIAL_STUDIES,
    "TRUTH_HISTORY": StandardsSubject.SOCIAL_STUDIES,
    "ENGLISH_LITERATURE": StandardsSubject.ELA,
    "APPLIED_MATHEMATICS": StandardsSubject.MATH,
    "CREATIVE_ECONOMY": StandardsSubject.ELA,
}

OAS_STANDARDS_REGISTRY = {
    "OK-ELA-8.R.1": OASStandard(code="OK-ELA-8.R.1", subject=StandardsSubject.ELA, grade_band="6-8", strand="Reading", description="Students will identify and analyze main idea and supporting details."),
    "OK-ELA-HS.R.2": OASStandard(code="OK-ELA-HS.R.2", subject=StandardsSubject.ELA, grade_band="9-12", strand="Reading", description="Students will analyze author's purpose and craft."),
    "OK-SCIENCE-8.LS.1": OASStandard(code="OK-SCIENCE-8.LS.1", subject=StandardsSubject.SCIENCE, grade_band="6-8", strand="Life Science", description="Students will understand the relationship between structure and function."),
    "OK-MATH-HS.A.1": OASStandard(code="OK-MATH-HS.A.1", subject=StandardsSubject.MATH, grade_band="9-12", strand="Algebra", description="Students will solve linear and quadratic equations."),
    "OK-SOCIAL-STUDIES-HS.1": OASStandard(code="OK-SOCIAL-STUDIES-HS.1", subject=StandardsSubject.SOCIAL_STUDIES, grade_band="9-12", strand="History", description="Students will analyze major events in United States history."),
}


def get_track_subject(track: str) -> Optional[StandardsSubject]:
    return TRACK_TO_SUBJECT.get(track)


def lookup_oas_standard(code: str) -> Optional[OASStandard]:
    return OAS_STANDARDS_REGISTRY.get(code)


def infer_oas_confidence(content: str, oas_code: str) -> float:
    if not content:
        return 0.0
    content_lower = content.lower()
    standard = lookup_oas_standard(oas_code)
    if not standard:
        return 0.0
    description_lower = standard.description.lower()
    keywords = description_lower.split()
    matches = sum(1 for kw in keywords if len(kw) > 3 and kw in content_lower)
    confidence = min(1.0, matches / max(1, len(keywords)))
    return confidence


def map_lesson_to_oas(track: str, content: str, grade_band: str = "9-12") -> list[OASStandard]:
    subject = get_track_subject(track)
    if not subject:
        return []
    matching_standards = []
    for code, standard in OAS_STANDARDS_REGISTRY.items():
        if standard.subject == subject and standard.grade_band == grade_band:
            confidence = infer_oas_confidence(content, code)
            if confidence > 0.3:
                matching_standards.append(OASStandard(
                    code=standard.code, subject=standard.subject,
                    grade_band=standard.grade_band, strand=standard.strand,
                    description=standard.description, confidence=confidence,
                ))
    return sorted(matching_standards, key=lambda s: s.confidence, reverse=True)


def validate_oas_code(code: str) -> bool:
    return code in OAS_STANDARDS_REGISTRY
