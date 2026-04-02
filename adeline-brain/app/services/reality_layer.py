"""
Reality Layer Service — truth weights, importance filters, distortion flags.
"""
import uuid
import json
import logging
from typing import Optional
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class WeightTier(IntEnum):
    CORE_TRUTH = 1
    WORKING_KNOWLEDGE = 2
    EXPOSURE = 3


@dataclass
class DistortionFlag:
    id: str
    commonClaim: str
    whatsHidden: str
    whatActuallyHappens: str
    whyItMatters: str


@dataclass
class KeystoneConcept:
    id: str
    concept: str
    firstIntroduced: bool = False
    context: Optional[str] = None
    repetitionNumber: int = 1


@dataclass
class ImportanceFilterResult:
    survivalFunction: bool
    powerSystems: bool
    permanence: bool

    @property
    def passes(self) -> bool:
        return self.survivalFunction or self.powerSystems or self.permanence


@dataclass
class RealityLayerMetadata:
    weightTier: int
    distortionFlags: list
    keystoneConcept: Optional[KeystoneConcept]
    distractionBoxes: list
    importanceFilter: dict


# ── Pure helper functions (testable without API) ─────────────────────────────

def parse_weight_tier(raw: str) -> int:
    """Parse Claude's weight tier response (1, 2, or 3). Default to 2."""
    try:
        tier = int(raw.strip())
        return tier if tier in (1, 2, 3) else 2
    except (ValueError, TypeError):
        return 2


def extract_json_from_response(text: str) -> str:
    """Extract JSON from a Claude response that may have markdown code fences."""
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()


def parse_distortion_flags(raw_json: str) -> list[DistortionFlag]:
    """Parse distortion flags from JSON string."""
    try:
        text = extract_json_from_response(raw_json)
        flags_raw = json.loads(text)
        return [
            DistortionFlag(
                id=str(uuid.uuid4()),
                commonClaim=f.get("commonClaim", ""),
                whatsHidden=f.get("whatsHidden", ""),
                whatActuallyHappens=f.get("whatActuallyHappens", ""),
                whyItMatters=f.get("whyItMatters", ""),
            )
            for f in flags_raw
        ]
    except (json.JSONDecodeError, TypeError):
        return []


def parse_importance_filter(raw_json: str) -> Optional[ImportanceFilterResult]:
    """Parse importance filter from JSON string. Returns None if fails."""
    try:
        text = extract_json_from_response(raw_json)
        data = json.loads(text)
        result = ImportanceFilterResult(
            survivalFunction=data.get("survivalFunction", False),
            powerSystems=data.get("powerSystems", False),
            permanence=data.get("permanence", False),
        )
        return result if result.passes else None
    except (json.JSONDecodeError, TypeError):
        return None
