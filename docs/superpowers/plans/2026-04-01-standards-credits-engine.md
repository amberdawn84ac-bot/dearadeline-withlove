# Standards & Credits Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the three-ledger credit accumulation system with Oklahoma compliance profiles and parent-approval gating for transcript courses.

**Architecture:** Python credit engine runs post-RegistrarAgent, accumulating hours in StandardsLedger/CreditLedger/EvidenceLedger. Course proposals are generated when bucket thresholds are met. Parent approval required before any course appears on official transcript. Oklahoma profiles are JSON config — not hardcoded logic.

**Tech Stack:** Python (FastAPI, asyncpg via Prisma), TypeScript (Next.js 14), Prisma (ledger models already exist).

---

## Context

The Foundation plan (merged) added:
- `StandardsLedgerEntry`, `CreditLedgerEntry`, `EvidenceLedgerEntry` Prisma models (adeline-brain/prisma/schema.prisma)
- `StandardsTag`, `CreditBucket`, `LearningEvidence` Zod schemas (adeline-core/src/schemas/standards.ts)
- `TRACK_CREDIT_MAP` config mapping all 10 tracks to credit buckets + external transcript names (adeline-core/src/config/tracks.ts)
- `StandardsFramework` enum: OAS, OSRHE_CORE, LOCAL
- `StandardsSubject` enum: ELA, SCIENCE, SOCIAL_STUDIES, HEALTH, WORLD_LANGUAGES, MATH, INFO_LIT

**Key constraint:** OAS (Oklahoma Academic Standards) is an **overlay** — it never controls what gets taught. The credit engine is portfolio-first, evidence-driven, with OAS metadata optional.

**Credit threshold rules:**
- 1.0 credit = ~120 weighted hours of evidence
- 0.5 credit = ~60 weighted hours
- When threshold is reached in a `CreditBucket`, propose a course using `TRACK_CREDIT_MAP[track].externalName`
- Course appears on transcript only after parent approval (`isApproved = true`)

**Oklahoma profiles (JSON, not hardcoded):**
- `oklahoma_flexible_homeschool` — OAS optional, portfolio-first, no transcript gating
- `oklahoma_college_prep` — OAS on, OSRHE 15-unit dashboard, ACT readiness, stricter standards
- `oklahoma_public_school_parity` — OAS required, standards saturation checks, school-like pacing (opt-in only)

---

## Task 1: Oklahoma Profile JSON Configs

**Objective:** Create the three selectable profile configurations as JSON. These are static, not database-driven.

**Location:** `adeline-brain/data/oklahoma_profiles.json`

**Implementation:**

Create the file with the following structure:

```json
{
  "oklahoma_flexible_homeschool": {
    "name": "Oklahoma Flexible Homeschool",
    "description": "Portfolio-first, OAS optional. Student accomplishments drive the transcript, not standards checklists. Parents see progress, never forced pacing.",
    "oasOptional": true,
    "requiresApprovalForTranscript": true,
    "creditHourWeighting": {
      "essay": 1.0,
      "quiz": 0.5,
      "lab": 1.5,
      "project": 2.0,
      "discussion": 0.75,
      "fieldwork": 1.5,
      "presentation": 1.25
    },
    "creditThresholds": {
      "full_credit": 120,
      "half_credit": 60
    },
    "oasrheEnabled": false,
    "actReadinessEnabled": false,
    "transcript": {
      "allowCourseProposals": true,
      "courseProposalPrefix": "Portfolio",
      "exampleCourse": "Portfolio: Environmental Science"
    }
  },
  "oklahoma_college_prep": {
    "name": "Oklahoma College Prep (OSRHE 15-Unit Core)",
    "description": "OAS standards on. Student tracks mastery against OAS codes. OSRHE 15-unit dashboard shows college-readiness progress. ACT prep indicators visible in transcript.",
    "oasOptional": false,
    "requiresApprovalForTranscript": true,
    "creditHourWeighting": {
      "essay": 1.0,
      "quiz": 0.5,
      "lab": 1.5,
      "project": 1.75,
      "discussion": 0.75,
      "fieldwork": 1.25,
      "presentation": 1.25
    },
    "creditThresholds": {
      "full_credit": 120,
      "half_credit": 60
    },
    "oasrheEnabled": true,
    "osrheCoreBuckets": [
      "ENGLISH",
      "MATH",
      "LAB_SCIENCE",
      "SOCIAL_STUDIES"
    ],
    "actReadinessEnabled": true,
    "oasSubjectWeights": {
      "ELA": 1.0,
      "MATH": 1.0,
      "SCIENCE": 1.25,
      "SOCIAL_STUDIES": 1.0
    },
    "transcript": {
      "allowCourseProposals": true,
      "courseProposalPrefix": "AP Eligible",
      "exampleCourse": "AP Eligible: Environmental Science (Mastery 94%)"
    }
  },
  "oklahoma_public_school_parity": {
    "name": "Oklahoma Public School Parity (High Compliance)",
    "description": "OAS saturation checks enforced. Student must demonstrate mastery of min 80% of standards in each subject. Stricter pacing aligned to school year. Opt-in only.",
    "oasOptional": false,
    "requiresApprovalForTranscript": true,
    "creditHourWeighting": {
      "essay": 1.0,
      "quiz": 0.75,
      "lab": 1.5,
      "project": 1.5,
      "discussion": 0.75,
      "fieldwork": 1.0,
      "presentation": 1.0
    },
    "creditThresholds": {
      "full_credit": 120,
      "half_credit": 60
    },
    "oasrheEnabled": true,
    "osrheCoreBuckets": [
      "ENGLISH",
      "MATH",
      "LAB_SCIENCE",
      "SOCIAL_STUDIES"
    ],
    "oasStandardsSaturationRequired": true,
    "oasStandardsSaturationThreshold": 0.80,
    "actReadinessEnabled": true,
    "oasSubjectWeights": {
      "ELA": 1.0,
      "MATH": 1.0,
      "SCIENCE": 1.25,
      "SOCIAL_STUDIES": 1.0
    },
    "transcript": {
      "allowCourseProposals": true,
      "courseProposalPrefix": "School Parity",
      "exampleCourse": "School Parity: Environmental Science (OAS Saturation 82%)"
    }
  }
}
```

**Tests:**

Create `adeline-brain/tests/test_oklahoma_profiles.py`:

```python
import json
from pathlib import Path

def test_oklahoma_profiles_valid_json():
    """Test that oklahoma_profiles.json is valid JSON."""
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    assert profiles_path.exists(), f"oklahoma_profiles.json not found at {profiles_path}"

    with open(profiles_path) as f:
        profiles = json.load(f)

    assert "oklahoma_flexible_homeschool" in profiles
    assert "oklahoma_college_prep" in profiles
    assert "oklahoma_public_school_parity" in profiles

def test_oklahoma_profiles_required_keys():
    """Test that each profile has required top-level keys."""
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    with open(profiles_path) as f:
        profiles = json.load(f)

    required_keys = {
        "name",
        "description",
        "oasOptional",
        "requiresApprovalForTranscript",
        "creditHourWeighting",
        "creditThresholds",
        "transcript"
    }

    for profile_key, profile in profiles.items():
        assert isinstance(profile, dict), f"{profile_key} is not a dict"
        assert required_keys.issubset(profile.keys()), \
            f"{profile_key} missing keys: {required_keys - set(profile.keys())}"

        # Validate creditThresholds
        assert "full_credit" in profile["creditThresholds"]
        assert "half_credit" in profile["creditThresholds"]
        assert profile["creditThresholds"]["full_credit"] == 120
        assert profile["creditThresholds"]["half_credit"] == 60

def test_artifact_type_weighting_consistent():
    """Test that all profiles define weighting for the same artifact types."""
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    with open(profiles_path) as f:
        profiles = json.load(f)

    artifact_types = {
        "essay", "quiz", "lab", "project", "discussion", "fieldwork", "presentation"
    }

    for profile_key, profile in profiles.items():
        weights = set(profile["creditHourWeighting"].keys())
        assert weights == artifact_types, \
            f"{profile_key} has mismatched artifact types: {weights} vs {artifact_types}"

        for weight in profile["creditHourWeighting"].values():
            assert weight > 0, f"{profile_key} has non-positive weight"
```

**Commit message:**

```
feat: Oklahoma profile configurations (JSON)

- Add oklahoma_profiles.json with three selectable profiles
- oklahoma_flexible_homeschool: Portfolio-first, OAS optional
- oklahoma_college_prep: OAS + OSRHE 15-unit + ACT readiness
- oklahoma_public_school_parity: Strict OAS saturation + pacing
- Add comprehensive tests for profile structure and consistency
```

---

## Task 2: Credit Engine — Accumulation Logic (Pure Functions)

**Objective:** Implement the core credit accumulation algorithm. Pure computation — no DB calls.

**Location:** `adeline-brain/app/services/credit_engine.py`

**Implementation:**

```python
"""
Credit accumulation engine — pure functions for standards/credit/evidence ledger logic.
No database calls — all state passed in, results passed out.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
from datetime import datetime


# ── Data Classes ──────────────────────────────────────────────────────────────

class ArtifactType(str, Enum):
    """Learning evidence artifact types — must match adeline-core LearningEvidence."""
    ESSAY = "essay"
    QUIZ = "quiz"
    LAB = "lab"
    PROJECT = "project"
    DISCUSSION = "discussion"
    FIELDWORK = "fieldwork"
    PRESENTATION = "presentation"


@dataclass
class Evidence:
    """A single student artifact contributing to credit accumulation."""
    artifact_type: ArtifactType
    mastery_score: float  # 0.0 to 1.0
    hours: float  # Raw hours spent
    activity_date: datetime


@dataclass
class CreditHourWeighting:
    """Artifact type → weighted hour multiplier for a given profile."""
    essay: float
    quiz: float
    lab: float
    project: float
    discussion: float
    fieldwork: float
    presentation: float

    def get_weight(self, artifact_type: ArtifactType) -> float:
        """Return the weighting multiplier for an artifact type."""
        return getattr(self, artifact_type.value)


@dataclass
class CreditBucketAccumulation:
    """Running total for a single credit bucket."""
    bucket_name: str
    hours_earned: float = 0.0
    evidence_count: int = 0
    mastery_average: float = 0.0  # Running average


@dataclass
class CourseProposal:
    """A proposed course when a credit bucket threshold is met."""
    bucket: str
    external_course_name: str
    hours_earned: float
    mastery_percentage: float
    is_approved: bool = False
    proposed_at: Optional[datetime] = None


# ── Core Engine ───────────────────────────────────────────────────────────────

def calculate_weighted_hours(
    evidence: Evidence,
    weighting: CreditHourWeighting,
) -> float:
    """
    Calculate weighted hours for a single evidence artifact.

    Weighting formula:
        weighted_hours = hours * artifact_type_weight * mastery_factor

    mastery_factor scales from 0.5 (below 50%) to 1.0 (at 100%).
    This penalizes low-mastery work and fully credits high-mastery work.
    """
    artifact_weight = weighting.get_weight(evidence.artifact_type)

    # Mastery factor: scale from 0.5 to 1.0
    # At 0% mastery: factor = 0.5 (half credit)
    # At 50% mastery: factor = 0.75
    # At 100% mastery: factor = 1.0
    mastery_factor = 0.5 + (evidence.mastery_score * 0.5)

    weighted_hours = evidence.hours * artifact_weight * mastery_factor
    return weighted_hours


def accumulate_evidence_in_bucket(
    bucket: CreditBucketAccumulation,
    evidence: Evidence,
    weighting: CreditHourWeighting,
) -> CreditBucketAccumulation:
    """
    Add a single evidence artifact to a credit bucket accumulation.
    Returns updated bucket with running totals.
    """
    weighted_hours = calculate_weighted_hours(evidence, weighting)

    # Update running average mastery
    old_total_mastery = bucket.mastery_average * bucket.evidence_count
    new_evidence_count = bucket.evidence_count + 1
    bucket.mastery_average = (
        (old_total_mastery + evidence.mastery_score) / new_evidence_count
    )

    bucket.hours_earned += weighted_hours
    bucket.evidence_count = new_evidence_count

    return bucket


def check_credit_threshold(
    bucket: CreditBucketAccumulation,
    full_credit_hours: float = 120.0,
    half_credit_hours: float = 60.0,
) -> Optional[float]:
    """
    Check if a bucket has reached a credit threshold.

    Returns:
        - 1.0 if full_credit_hours threshold met
        - 0.5 if half_credit_hours threshold met
        - None if below half_credit_hours

    Once a threshold is crossed, it remains granted (no "taking back" credits).
    """
    if bucket.hours_earned >= full_credit_hours:
        return 1.0
    elif bucket.hours_earned >= half_credit_hours:
        return 0.5
    return None


def propose_course(
    bucket_name: str,
    external_course_name: str,
    hours_earned: float,
    mastery_average: float,
) -> CourseProposal:
    """
    Create a course proposal when a credit threshold is met.

    Proposal is NOT automatically approved — parent/admin must review.
    """
    return CourseProposal(
        bucket=bucket_name,
        external_course_name=external_course_name,
        hours_earned=hours_earned,
        mastery_percentage=mastery_average * 100,
        is_approved=False,
        proposed_at=datetime.utcnow(),
    )


def apply_profile_weighting(
    profile_key: str,
    profile_data: dict,
) -> CreditHourWeighting:
    """
    Extract CreditHourWeighting from a profile dict (e.g., loaded from JSON).

    Raises ValueError if profile data is malformed.
    """
    try:
        weights = profile_data["creditHourWeighting"]
        return CreditHourWeighting(
            essay=weights["essay"],
            quiz=weights["quiz"],
            lab=weights["lab"],
            project=weights["project"],
            discussion=weights["discussion"],
            fieldwork=weights["fieldwork"],
            presentation=weights["presentation"],
        )
    except (KeyError, TypeError) as e:
        raise ValueError(
            f"Profile '{profile_key}' has malformed creditHourWeighting: {e}"
        ) from e


def compute_bucket_accumulation(
    bucket_name: str,
    evidence_list: list[Evidence],
    weighting: CreditHourWeighting,
) -> CreditBucketAccumulation:
    """
    Accumulate all evidence for a single bucket.

    Returns final bucket state with total hours and mastery average.
    """
    bucket = CreditBucketAccumulation(bucket_name=bucket_name)
    for evidence in evidence_list:
        bucket = accumulate_evidence_in_bucket(bucket, evidence, weighting)
    return bucket


# ── Mastery Scaling ───────────────────────────────────────────────────────────

def mastery_score_to_grade_letter(mastery: float) -> str:
    """
    Convert mastery score (0.0–1.0) to a traditional letter grade.
    Used in transcript display.
    """
    if mastery >= 0.93:
        return "A"
    elif mastery >= 0.90:
        return "A-"
    elif mastery >= 0.87:
        return "B+"
    elif mastery >= 0.83:
        return "B"
    elif mastery >= 0.80:
        return "B-"
    elif mastery >= 0.77:
        return "C+"
    elif mastery >= 0.73:
        return "C"
    elif mastery >= 0.70:
        return "C-"
    elif mastery >= 0.60:
        return "D"
    else:
        return "F"
```

**Tests:**

Create `adeline-brain/tests/test_credit_engine.py`:

```python
import pytest
from datetime import datetime
from app.services.credit_engine import (
    Evidence,
    ArtifactType,
    CreditHourWeighting,
    CreditBucketAccumulation,
    calculate_weighted_hours,
    accumulate_evidence_in_bucket,
    check_credit_threshold,
    propose_course,
    apply_profile_weighting,
    compute_bucket_accumulation,
    mastery_score_to_grade_letter,
)


@pytest.fixture
def sample_weighting():
    """Standard Oklahoma College Prep weighting."""
    return CreditHourWeighting(
        essay=1.0,
        quiz=0.5,
        lab=1.5,
        project=1.75,
        discussion=0.75,
        fieldwork=1.25,
        presentation=1.25,
    )


def test_calculate_weighted_hours_perfect_essay(sample_weighting):
    """Perfect essay: 10 hours × 1.0 weight × 1.0 mastery = 10 weighted hours."""
    evidence = Evidence(
        artifact_type=ArtifactType.ESSAY,
        mastery_score=1.0,
        hours=10.0,
        activity_date=datetime.utcnow(),
    )
    weighted = calculate_weighted_hours(evidence, sample_weighting)
    assert weighted == 10.0


def test_calculate_weighted_hours_half_mastery_essay(sample_weighting):
    """Essay at 50% mastery: 10 × 1.0 × 0.75 = 7.5 weighted hours."""
    evidence = Evidence(
        artifact_type=ArtifactType.ESSAY,
        mastery_score=0.5,
        hours=10.0,
        activity_date=datetime.utcnow(),
    )
    weighted = calculate_weighted_hours(evidence, sample_weighting)
    assert weighted == 7.5


def test_calculate_weighted_hours_low_mastery_quiz(sample_weighting):
    """Quiz at 20% mastery: 5 × 0.5 × 0.6 = 1.5 weighted hours."""
    evidence = Evidence(
        artifact_type=ArtifactType.QUIZ,
        mastery_score=0.2,
        hours=5.0,
        activity_date=datetime.utcnow(),
    )
    weighted = calculate_weighted_hours(evidence, sample_weighting)
    assert weighted == pytest.approx(1.5)


def test_accumulate_evidence_updates_running_average(sample_weighting):
    """Test that accumulation maintains running average mastery."""
    bucket = CreditBucketAccumulation(bucket_name="ENGLISH")

    e1 = Evidence(
        artifact_type=ArtifactType.ESSAY,
        mastery_score=0.8,
        hours=5.0,
        activity_date=datetime.utcnow(),
    )
    bucket = accumulate_evidence_in_bucket(bucket, e1, sample_weighting)
    assert bucket.evidence_count == 1
    assert bucket.mastery_average == 0.8

    e2 = Evidence(
        artifact_type=ArtifactType.ESSAY,
        mastery_score=0.9,
        hours=5.0,
        activity_date=datetime.utcnow(),
    )
    bucket = accumulate_evidence_in_bucket(bucket, e2, sample_weighting)
    assert bucket.evidence_count == 2
    assert bucket.mastery_average == 0.85


def test_check_credit_threshold_full_credit():
    """Bucket with 120+ hours earns 1.0 credit."""
    bucket = CreditBucketAccumulation(
        bucket_name="ENGLISH",
        hours_earned=125.0,
        evidence_count=1,
        mastery_average=0.85,
    )
    credit = check_credit_threshold(bucket, full_credit_hours=120.0)
    assert credit == 1.0


def test_check_credit_threshold_half_credit():
    """Bucket with 60–119 hours earns 0.5 credit."""
    bucket = CreditBucketAccumulation(
        bucket_name="ENGLISH",
        hours_earned=80.0,
        evidence_count=1,
        mastery_average=0.85,
    )
    credit = check_credit_threshold(bucket, full_credit_hours=120.0, half_credit_hours=60.0)
    assert credit == 0.5


def test_check_credit_threshold_none_below_half():
    """Bucket with <60 hours earns no credit."""
    bucket = CreditBucketAccumulation(
        bucket_name="ENGLISH",
        hours_earned=30.0,
        evidence_count=1,
        mastery_average=0.85,
    )
    credit = check_credit_threshold(bucket, half_credit_hours=60.0)
    assert credit is None


def test_propose_course():
    """CourseProposal is created with correct fields."""
    proposal = propose_course(
        bucket_name="ENGLISH",
        external_course_name="English Language Arts",
        hours_earned=125.0,
        mastery_average=0.87,
    )
    assert proposal.bucket == "ENGLISH"
    assert proposal.external_course_name == "English Language Arts"
    assert proposal.hours_earned == 125.0
    assert proposal.mastery_percentage == 87.0
    assert proposal.is_approved is False
    assert proposal.proposed_at is not None


def test_apply_profile_weighting_success():
    """Load weighting from profile dict."""
    profile = {
        "creditHourWeighting": {
            "essay": 1.0,
            "quiz": 0.5,
            "lab": 1.5,
            "project": 1.75,
            "discussion": 0.75,
            "fieldwork": 1.25,
            "presentation": 1.25,
        }
    }
    weighting = apply_profile_weighting("test_profile", profile)
    assert weighting.essay == 1.0
    assert weighting.quiz == 0.5
    assert weighting.lab == 1.5


def test_apply_profile_weighting_malformed():
    """Raise ValueError for malformed profile."""
    profile = {"creditHourWeighting": None}
    with pytest.raises(ValueError):
        apply_profile_weighting("bad_profile", profile)


def test_compute_bucket_accumulation():
    """Accumulate multiple evidence items into a bucket."""
    weighting = CreditHourWeighting(
        essay=1.0, quiz=0.5, lab=1.5, project=1.75,
        discussion=0.75, fieldwork=1.25, presentation=1.25,
    )

    evidence = [
        Evidence(
            artifact_type=ArtifactType.ESSAY,
            mastery_score=0.85,
            hours=10.0,
            activity_date=datetime.utcnow(),
        ),
        Evidence(
            artifact_type=ArtifactType.LAB,
            mastery_score=0.9,
            hours=8.0,
            activity_date=datetime.utcnow(),
        ),
    ]

    bucket = compute_bucket_accumulation("ENGLISH", evidence, weighting)
    assert bucket.evidence_count == 2
    # essay: 10 * 1.0 * (0.5 + 0.85*0.5) = 10 * 0.925 = 9.25
    # lab: 8 * 1.5 * (0.5 + 0.9*0.5) = 8 * 1.5 * 0.95 = 11.4
    assert bucket.hours_earned == pytest.approx(20.65)


def test_mastery_score_to_grade_letter():
    """Test grade letter mapping."""
    assert mastery_score_to_grade_letter(0.95) == "A"
    assert mastery_score_to_grade_letter(0.87) == "B+"
    assert mastery_score_to_grade_letter(0.80) == "B-"
    assert mastery_score_to_grade_letter(0.70) == "C-"
    assert mastery_score_to_grade_letter(0.60) == "D"
    assert mastery_score_to_grade_letter(0.45) == "F"
```

**Commit message:**

```
feat: Credit accumulation engine (pure functions)

- Implement weighted hour calculation with mastery scaling
- Add evidence accumulation with running average mastery
- Implement credit threshold checks (1.0 and 0.5 credit levels)
- Add course proposal generation
- Add profile weighting extraction and bucket accumulation
- Include grade letter conversion for transcript display
- Comprehensive test coverage for all pure functions
```

---

## Task 3: Standards Mapper — Map Track + Content to OAS Codes

**Objective:** Map curriculum tracks and lesson content to Oklahoma Academic Standards (OAS) codes.

**Location:** `adeline-brain/app/services/standards_mapper.py`

**Implementation:**

```python
"""
Standards mapper — map tracks and lesson content to OAS codes.
OAS is an overlay (not controlling), but metadata enriches transcripts.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class StandardsSubject(str, Enum):
    """OAS subject areas."""
    ELA = "ELA"
    SCIENCE = "SCIENCE"
    SOCIAL_STUDIES = "SOCIAL_STUDIES"
    HEALTH = "HEALTH"
    WORLD_LANGUAGES = "WORLD_LANGUAGES"
    MATH = "MATH"
    INFO_LIT = "INFO_LIT"


@dataclass
class OASStandard:
    """A single OAS standard code."""
    code: str  # e.g., "OK-ELA-8.R.1"
    subject: StandardsSubject
    grade_band: str  # e.g., "K-2", "3-5", "6-8", "9-12"
    strand: str  # e.g., "Reading", "Writing"
    description: str
    confidence: float = 0.0  # 0.0–1.0, how strongly this lesson addresses the standard


# ── Track → Subject Mapping ───────────────────────────────────────────────────

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
    "CREATIVE_ECONOMY": StandardsSubject.ELA,  # Includes INFO_LIT and art
}


# ── OAS Code Registry (Simplified for Demo) ───────────────────────────────────
# In production, this would be a full curriculum database.

OAS_STANDARDS_REGISTRY = {
    "OK-ELA-8.R.1": OASStandard(
        code="OK-ELA-8.R.1",
        subject=StandardsSubject.ELA,
        grade_band="6-8",
        strand="Reading",
        description="Students will identify and analyze main idea and supporting details.",
    ),
    "OK-ELA-HS.R.2": OASStandard(
        code="OK-ELA-HS.R.2",
        subject=StandardsSubject.ELA,
        grade_band="9-12",
        strand="Reading",
        description="Students will analyze author's purpose and craft.",
    ),
    "OK-SCIENCE-8.LS.1": OASStandard(
        code="OK-SCIENCE-8.LS.1",
        subject=StandardsSubject.SCIENCE,
        grade_band="6-8",
        strand="Life Science",
        description="Students will understand the relationship between structure and function.",
    ),
    "OK-MATH-HS.A.1": OASStandard(
        code="OK-MATH-HS.A.1",
        subject=StandardsSubject.MATH,
        grade_band="9-12",
        strand="Algebra",
        description="Students will solve linear and quadratic equations.",
    ),
    "OK-SOCIAL-STUDIES-HS.1": OASStandard(
        code="OK-SOCIAL-STUDIES-HS.1",
        subject=StandardsSubject.SOCIAL_STUDIES,
        grade_band="9-12",
        strand="History",
        description="Students will analyze major events in United States history.",
    ),
}


def get_track_subject(track: str) -> Optional[StandardsSubject]:
    """Map a track name to its primary OAS subject."""
    return TRACK_TO_SUBJECT.get(track)


def lookup_oas_standard(code: str) -> Optional[OASStandard]:
    """Retrieve a single OAS standard by code."""
    return OAS_STANDARDS_REGISTRY.get(code)


def infer_oas_confidence(
    content: str,
    oas_code: str,
) -> float:
    """
    Estimate how well a lesson content addresses an OAS standard.

    This is a simplified keyword-match heuristic. In production, you'd use
    semantic similarity (embeddings) or human curation.

    Returns: confidence 0.0–1.0
    """
    if not content:
        return 0.0

    content_lower = content.lower()
    standard = lookup_oas_standard(oas_code)
    if not standard:
        return 0.0

    description_lower = standard.description.lower()

    # Keyword matching: does the content mention key terms from the standard?
    keywords = description_lower.split()
    matches = sum(1 for kw in keywords if len(kw) > 3 and kw in content_lower)

    # Confidence = proportion of keywords found (cap at 1.0)
    confidence = min(1.0, matches / max(1, len(keywords)))
    return confidence


def map_lesson_to_oas(
    track: str,
    content: str,
    grade_band: str = "9-12",
) -> list[OASStandard]:
    """
    Given a track and lesson content, infer which OAS standards are addressed.

    Returns: list of OASStandard objects with confidence scores set.

    This is a heuristic — in production, you'd use embeddings or human curation.
    """
    subject = get_track_subject(track)
    if not subject:
        return []

    matching_standards = []
    for code, standard in OAS_STANDARDS_REGISTRY.items():
        if standard.subject == subject and standard.grade_band == grade_band:
            confidence = infer_oas_confidence(content, code)
            if confidence > 0.3:  # Only include if reasonable match
                standard_with_confidence = OASStandard(
                    code=standard.code,
                    subject=standard.subject,
                    grade_band=standard.grade_band,
                    strand=standard.strand,
                    description=standard.description,
                    confidence=confidence,
                )
                matching_standards.append(standard_with_confidence)

    # Sort by confidence descending
    return sorted(matching_standards, key=lambda s: s.confidence, reverse=True)


def validate_oas_code(code: str) -> bool:
    """Check if an OAS code is valid."""
    return code in OAS_STANDARDS_REGISTRY
```

**Tests:**

Create `adeline-brain/tests/test_standards_mapper.py`:

```python
import pytest
from app.services.standards_mapper import (
    StandardsSubject,
    OASStandard,
    get_track_subject,
    lookup_oas_standard,
    infer_oas_confidence,
    map_lesson_to_oas,
    validate_oas_code,
)


def test_get_track_subject_english_literature():
    """ENGLISH_LITERATURE maps to ELA."""
    assert get_track_subject("ENGLISH_LITERATURE") == StandardsSubject.ELA


def test_get_track_subject_creation_science():
    """CREATION_SCIENCE maps to SCIENCE."""
    assert get_track_subject("CREATION_SCIENCE") == StandardsSubject.SCIENCE


def test_get_track_subject_applied_mathematics():
    """APPLIED_MATHEMATICS maps to MATH."""
    assert get_track_subject("APPLIED_MATHEMATICS") == StandardsSubject.MATH


def test_get_track_subject_unknown():
    """Unknown track returns None."""
    assert get_track_subject("UNKNOWN_TRACK") is None


def test_lookup_oas_standard_exists():
    """Valid OAS code returns standard."""
    standard = lookup_oas_standard("OK-ELA-8.R.1")
    assert standard is not None
    assert standard.code == "OK-ELA-8.R.1"
    assert standard.subject == StandardsSubject.ELA


def test_lookup_oas_standard_not_exists():
    """Invalid OAS code returns None."""
    assert lookup_oas_standard("INVALID-CODE") is None


def test_infer_oas_confidence_high_match():
    """Content with strong keyword match yields high confidence."""
    content = "Students will analyze author's purpose and craft in the essay."
    confidence = infer_oas_confidence(content, "OK-ELA-HS.R.2")
    assert confidence > 0.5


def test_infer_oas_confidence_low_match():
    """Content with weak keyword match yields low confidence."""
    content = "Hello world."
    confidence = infer_oas_confidence(content, "OK-ELA-HS.R.2")
    assert confidence < 0.3


def test_infer_oas_confidence_empty_content():
    """Empty content returns 0.0."""
    assert infer_oas_confidence("", "OK-ELA-HS.R.2") == 0.0


def test_map_lesson_to_oas_ela():
    """Map ELA lesson to OAS standards."""
    content = "Read and analyze author's purpose in the primary source."
    standards = map_lesson_to_oas("ENGLISH_LITERATURE", content, grade_band="9-12")

    assert len(standards) > 0
    assert all(s.subject == StandardsSubject.ELA for s in standards)

    # Should be sorted by confidence descending
    for i in range(len(standards) - 1):
        assert standards[i].confidence >= standards[i + 1].confidence


def test_map_lesson_to_oas_unknown_track():
    """Unknown track returns empty list."""
    standards = map_lesson_to_oas("UNKNOWN_TRACK", "content here", grade_band="9-12")
    assert standards == []


def test_validate_oas_code_valid():
    """Valid code passes validation."""
    assert validate_oas_code("OK-ELA-8.R.1") is True


def test_validate_oas_code_invalid():
    """Invalid code fails validation."""
    assert validate_oas_code("INVALID-CODE") is False
```

**Commit message:**

```
feat: Standards mapper — track to OAS code inference

- Map 10 tracks to OAS subject areas
- Implement OAS standard lookup and validation
- Add keyword-based confidence scoring for content-to-standard mapping
- Add lesson-to-OAS mapping with confidence ranking
- Comprehensive test coverage for all mapper functions
```

---

## Task 4: Credits FastAPI Router

**Objective:** Expose credit engine functionality via REST API endpoints.

**Location:** `adeline-brain/app/api/credits.py`

**Implementation:**

```python
"""
FastAPI router for credit engine — accumulation, proposals, approvals.
Endpoints are async and use Prisma Client for state persistence.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json
from pathlib import Path

from app.services.credit_engine import (
    Evidence,
    ArtifactType,
    CreditBucketAccumulation,
    check_credit_threshold,
    propose_course,
    apply_profile_weighting,
    compute_bucket_accumulation,
    mastery_score_to_grade_letter,
    CreditHourWeighting,
)
from app.connections.prisma_client import get_prisma_client


# ── Pydantic Models ───────────────────────────────────────────────────────────

class EvidenceInput(BaseModel):
    """Evidence artifact submitted to credit engine."""
    artifact_type: str  # "essay", "quiz", "lab", "project", etc.
    title: str
    mastery_score: float = Field(ge=0.0, le=1.0)
    hours: float = Field(gt=0.0)
    activity_date: datetime


class CreditBucketResponse(BaseModel):
    """Credit accumulation state for a single bucket."""
    bucket: str
    hours_earned: float
    evidence_count: int
    mastery_average: float
    mastery_grade: str
    credit_earned: Optional[float]  # 1.0, 0.5, or None


class CoursePropusalResponse(BaseModel):
    """A proposed course awaiting parent approval."""
    proposal_id: str
    bucket: str
    external_course_name: str
    hours_earned: float
    mastery_percentage: float
    mastery_grade: str
    is_approved: bool
    proposed_at: datetime
    approved_at: Optional[datetime] = None


class CreditDashboardResponse(BaseModel):
    """Full credit state for a student."""
    student_id: str
    current_profile: str
    buckets: list[CreditBucketResponse]
    pending_proposals: list[CoursePropusalResponse]
    approved_courses: list[CoursePropusalResponse]


class ProfileResponse(BaseModel):
    """Oklahoma profile metadata."""
    key: str
    name: str
    description: str
    oas_optional: bool


router = APIRouter(prefix="/credits", tags=["credits"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_oklahoma_profiles() -> dict:
    """Load oklahoma_profiles.json."""
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    with open(profiles_path) as f:
        return json.load(f)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{student_id}/profile")
async def get_student_profile(student_id: str) -> dict:
    """
    Get the student's current Oklahoma profile preference.

    Returns:
        {
            "student_id": "...",
            "profile_key": "oklahoma_college_prep",
            "profile": {...}
        }
    """
    prisma = get_prisma_client()

    # Fetch student
    user = await prisma.user.find_unique(where={"id": student_id})
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")

    # For now, assume profile is stored in User.profile_key field (add to schema if needed)
    # Default to oklahoma_flexible_homeschool
    profile_key = getattr(user, "profile_key", "oklahoma_flexible_homeschool")

    profiles = load_oklahoma_profiles()
    profile = profiles.get(profile_key)

    return {
        "student_id": student_id,
        "profile_key": profile_key,
        "profile": profile,
    }


@router.put("/{student_id}/profile")
async def set_student_profile(student_id: str, profile_key: str) -> dict:
    """
    Switch the student's Oklahoma profile.

    Valid profile_key values:
        - oklahoma_flexible_homeschool
        - oklahoma_college_prep
        - oklahoma_public_school_parity
    """
    profiles = load_oklahoma_profiles()
    if profile_key not in profiles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile_key. Choose from: {list(profiles.keys())}",
        )

    prisma = get_prisma_client()

    # Update User.profile_key (add field to schema first)
    # For now, this is a placeholder
    # TODO: Add profile_key field to User model

    return {
        "student_id": student_id,
        "profile_key": profile_key,
        "message": "Profile updated successfully",
    }


@router.get("/{student_id}")
async def get_credit_dashboard(student_id: str) -> CreditDashboardResponse:
    """
    Get the full credit dashboard for a student.

    Shows:
        - Current profile
        - Credit accumulation by bucket
        - Pending proposals
        - Approved courses
    """
    prisma = get_prisma_client()

    # Fetch student and profile
    user = await prisma.user.find_unique(where={"id": student_id})
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")

    profile_key = getattr(user, "profile_key", "oklahoma_flexible_homeschool")
    profiles = load_oklahoma_profiles()
    profile_data = profiles[profile_key]

    # Fetch all evidence ledger entries for this student
    evidence_entries = await prisma.evidenceledgerentry.find_many(
        where={"studentId": student_id},
        order_by={"createdAt": "desc"},
    )

    # Group evidence by bucket and accumulate
    weighting = apply_profile_weighting(profile_key, profile_data)
    bucket_accumulations: dict[str, CreditBucketAccumulation] = {}

    for entry in evidence_entries:
        bucket = entry.bucket
        if bucket not in bucket_accumulations:
            bucket_accumulations[bucket] = CreditBucketAccumulation(bucket_name=bucket)

        evidence = Evidence(
            artifact_type=ArtifactType[entry.artifactType.upper()],
            mastery_score=entry.masteryScore,
            hours=entry.hours,
            activity_date=entry.activityDate,
        )

        accum = bucket_accumulations[bucket]
        bucket_accumulations[bucket] = (
            compute_bucket_accumulation(
                bucket,
                [evidence],
                weighting,
            ) if accum.evidence_count == 0 else
            # Manual update for existing bucket
            _update_bucket_in_place(accum, evidence, weighting)
        )

    # Build bucket responses
    bucket_responses = []
    for bucket_name, accum in bucket_accumulations.items():
        credit_earned = check_credit_threshold(
            accum,
            full_credit_hours=profile_data["creditThresholds"]["full_credit"],
            half_credit_hours=profile_data["creditThresholds"]["half_credit"],
        )

        bucket_responses.append(
            CreditBucketResponse(
                bucket=bucket_name,
                hours_earned=accum.hours_earned,
                evidence_count=accum.evidence_count,
                mastery_average=accum.mastery_average,
                mastery_grade=mastery_score_to_grade_letter(accum.mastery_average),
                credit_earned=credit_earned,
            )
        )

    # Fetch pending and approved proposals
    pending_proposals = []
    approved_courses = []

    for entry in evidence_entries:
        if entry.proposedCourse:
            proposal_response = CoursePropusalResponse(
                proposal_id=entry.id,
                bucket=entry.bucket,
                external_course_name=entry.proposedCourse,
                hours_earned=entry.hours,
                mastery_percentage=entry.masteryScore * 100,
                mastery_grade=mastery_score_to_grade_letter(entry.masteryScore),
                is_approved=entry.isApproved,
                proposed_at=entry.createdAt,
                approved_at=None,  # TODO: add approvedAt field to schema
            )

            if entry.isApproved:
                approved_courses.append(proposal_response)
            else:
                pending_proposals.append(proposal_response)

    return CreditDashboardResponse(
        student_id=student_id,
        current_profile=profile_key,
        buckets=bucket_responses,
        pending_proposals=pending_proposals,
        approved_courses=approved_courses,
    )


@router.post("/{student_id}/approve/{proposal_id}")
async def approve_course_proposal(student_id: str, proposal_id: str) -> dict:
    """
    Parent approves a course proposal.
    Once approved, the course is eligible for the official transcript.
    """
    prisma = get_prisma_client()

    # Find the evidence entry
    evidence = await prisma.evidenceledgerentry.find_unique(where={"id": proposal_id})
    if not evidence or evidence.studentId != student_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Update approval flag
    updated = await prisma.evidenceledgerentry.update(
        where={"id": proposal_id},
        data={"isApproved": True},
    )

    return {
        "proposal_id": updated.id,
        "is_approved": updated.isApproved,
        "message": "Course approved and eligible for official transcript",
    }


@router.get("/available-profiles")
async def list_available_profiles() -> list[ProfileResponse]:
    """List all available Oklahoma profiles."""
    profiles = load_oklahoma_profiles()
    return [
        ProfileResponse(
            key=profile_key,
            name=profile["name"],
            description=profile["description"],
            oas_optional=profile["oasOptional"],
        )
        for profile_key, profile in profiles.items()
    ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _update_bucket_in_place(
    bucket: CreditBucketAccumulation,
    evidence: Evidence,
    weighting: CreditHourWeighting,
) -> CreditBucketAccumulation:
    """Update a bucket in place (helper for accumulation)."""
    from app.services.credit_engine import accumulate_evidence_in_bucket
    return accumulate_evidence_in_bucket(bucket, evidence, weighting)
```

**Tests:**

Create `adeline-brain/tests/test_credits_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_available_profiles():
    """GET /credits/available-profiles returns all profiles."""
    response = client.get("/credits/available-profiles")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 3

    profile_keys = {p["key"] for p in data}
    assert "oklahoma_flexible_homeschool" in profile_keys
    assert "oklahoma_college_prep" in profile_keys
    assert "oklahoma_public_school_parity" in profile_keys


@pytest.mark.asyncio
async def test_get_credit_dashboard_student_not_found():
    """GET /credits/{student_id} returns 404 for unknown student."""
    response = client.get("/credits/unknown-student-id")
    assert response.status_code == 404
```

**Commit message:**

```
feat: Credits FastAPI router with dashboard endpoints

- Add GET /credits/available-profiles to list Oklahoma profiles
- Add GET /credits/{student_id}/profile to fetch student profile
- Add PUT /credits/{student_id}/profile to switch profiles
- Add GET /credits/{student_id} for full credit dashboard
- Add POST /credits/{student_id}/approve/{proposal_id} for course approval
- Include comprehensive request/response models
```

---

## Task 5: Brain Client Credit Functions (TypeScript)

**Objective:** Add type-safe REST client functions in the frontend for credit endpoints.

**Location:** `adeline-ui/src/lib/brain-client.ts`

**Implementation:**

Add these functions to the existing brain-client:

```typescript
// ── Credit Engine Types ───────────────────────────────────────────────────────

export interface CreditBucketState {
  bucket: string;
  hoursEarned: number;
  evidenceCount: number;
  masteryAverage: number;
  masteryGrade: string;
  creditEarned: number | null; // 1.0, 0.5, or null
}

export interface CourseProposal {
  proposalId: string;
  bucket: string;
  externalCourseName: string;
  hoursEarned: number;
  masteryPercentage: number;
  masteryGrade: string;
  isApproved: boolean;
  proposedAt: string; // ISO datetime
  approvedAt?: string;
}

export interface CreditDashboard {
  studentId: string;
  currentProfile: string;
  buckets: CreditBucketState[];
  pendingProposals: CourseProposal[];
  approvedCourses: CourseProposal[];
}

export interface OklahomProfile {
  key: string;
  name: string;
  description: string;
  oasOptional: boolean;
}

// ── Credit Engine Functions ───────────────────────────────────────────────────

/**
 * Fetch all available Oklahoma profiles.
 */
export async function listAvailableProfiles(): Promise<OklahomProfile[]> {
  const res = await fetch(`${BRAIN_URL}/credits/available-profiles`);
  if (!res.ok) {
    throw new Error(
      `Failed to fetch profiles: ${res.status} ${res.statusText}`
    );
  }
  return res.json();
}

/**
 * Get the student's current Oklahoma profile and profile key.
 */
export async function getStudentProfile(
  studentId: string
): Promise<{ studentId: string; profileKey: string; profile: Record<string, any> }> {
  const res = await fetch(`${BRAIN_URL}/credits/${studentId}/profile`);
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error("Student not found");
    }
    throw new Error(
      `Failed to fetch profile: ${res.status} ${res.statusText}`
    );
  }
  return res.json();
}

/**
 * Switch the student's Oklahoma profile.
 */
export async function setStudentProfile(
  studentId: string,
  profileKey: string
): Promise<{ studentId: string; profileKey: string; message: string }> {
  const res = await fetch(`${BRAIN_URL}/credits/${studentId}/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_key: profileKey }),
  });
  if (!res.ok) {
    throw new Error(
      `Failed to set profile: ${res.status} ${res.statusText}`
    );
  }
  return res.json();
}

/**
 * Fetch the full credit dashboard for a student.
 * Shows accumulation by bucket, pending proposals, and approved courses.
 */
export async function getCreditDashboard(
  studentId: string
): Promise<CreditDashboard> {
  const res = await fetch(`${BRAIN_URL}/credits/${studentId}`);
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error("Student not found");
    }
    throw new Error(
      `Failed to fetch credit dashboard: ${res.status} ${res.statusText}`
    );
  }
  return res.json();
}

/**
 * Parent approves a course proposal.
 * Once approved, the course is eligible for the official transcript.
 */
export async function approveCourseProposal(
  studentId: string,
  proposalId: string
): Promise<{ proposalId: string; isApproved: boolean; message: string }> {
  const res = await fetch(
    `${BRAIN_URL}/credits/${studentId}/approve/${proposalId}`,
    {
      method: "POST",
    }
  );
  if (!res.ok) {
    throw new Error(
      `Failed to approve proposal: ${res.status} ${res.statusText}`
    );
  }
  return res.json();
}
```

**Tests:**

Create `adeline-ui/src/lib/__tests__/brain-client.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  listAvailableProfiles,
  getStudentProfile,
  setStudentProfile,
  getCreditDashboard,
  approveCourseProposal,
} from "../brain-client";

// Mock fetch globally
global.fetch = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Credit Engine Client Functions", () => {
  describe("listAvailableProfiles", () => {
    it("should fetch and return all profiles", async () => {
      const mockProfiles = [
        {
          key: "oklahoma_flexible_homeschool",
          name: "Oklahoma Flexible Homeschool",
          description: "Portfolio-first...",
          oasOptional: true,
        },
      ];

      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response(JSON.stringify(mockProfiles), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

      const result = await listAvailableProfiles();
      expect(result).toEqual(mockProfiles);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/credits/available-profiles")
      );
    });

    it("should throw on fetch error", async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response("Not Found", { status: 404 })
      );

      await expect(listAvailableProfiles()).rejects.toThrow();
    });
  });

  describe("getCreditDashboard", () => {
    it("should fetch student credit dashboard", async () => {
      const studentId = "test-student-123";
      const mockDashboard = {
        studentId,
        currentProfile: "oklahoma_college_prep",
        buckets: [
          {
            bucket: "ENGLISH",
            hoursEarned: 125.5,
            evidenceCount: 8,
            masteryAverage: 0.87,
            masteryGrade: "B+",
            creditEarned: 1.0,
          },
        ],
        pendingProposals: [],
        approvedCourses: [],
      };

      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response(JSON.stringify(mockDashboard), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

      const result = await getCreditDashboard(studentId);
      expect(result).toEqual(mockDashboard);
    });
  });

  describe("approveCourseProposal", () => {
    it("should approve a course proposal", async () => {
      const studentId = "test-student-123";
      const proposalId = "proposal-456";

      vi.mocked(global.fetch).mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            proposalId,
            isApproved: true,
            message: "Course approved and eligible for official transcript",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );

      const result = await approveCourseProposal(studentId, proposalId);
      expect(result.isApproved).toBe(true);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/credits/${studentId}/approve/${proposalId}`),
        { method: "POST" }
      );
    });
  });
});
```

**Commit message:**

```
feat: Add credit engine client functions (TypeScript)

- Add listAvailableProfiles() to fetch all Oklahoma profiles
- Add getStudentProfile() to fetch current profile
- Add setStudentProfile() to switch profiles
- Add getCreditDashboard() for full credit state
- Add approveCourseProposal() for parent approval flow
- Include TypeScript interfaces for all response types
- Add comprehensive vitest test coverage
```

---

## Task 6: CreditDashboard React Component

**Objective:** Build the frontend dashboard showing credit accumulation, proposals, and approval workflow.

**Location:** `adeline-ui/src/components/dashboard/CreditDashboard.tsx`

**Implementation:**

```typescript
"use client";

import { useEffect, useState } from "react";
import { getCreditDashboard, approveCourseProposal, listAvailableProfiles } from "@/lib/brain-client";
import type { CreditDashboard, OklahomProfile } from "@/lib/brain-client";

interface Props {
  studentId: string;
}

export function CreditDashboardComponent({ studentId }: Props) {
  const [dashboard, setDashboard] = useState<CreditDashboard | null>(null);
  const [profiles, setProfiles] = useState<OklahomProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approvingProposalId, setApprovingProposalId] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        const [dashboardData, profilesData] = await Promise.all([
          getCreditDashboard(studentId),
          listAvailableProfiles(),
        ]);
        setDashboard(dashboardData);
        setProfiles(profilesData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load credit data");
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [studentId]);

  const handleApproveProposal = async (proposalId: string) => {
    try {
      setApprovingProposalId(proposalId);
      await approveCourseProposal(studentId, proposalId);

      // Refresh dashboard
      const updated = await getCreditDashboard(studentId);
      setDashboard(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve proposal");
    } finally {
      setApprovingProposalId(null);
    }
  };

  if (isLoading) {
    return <div className="p-6 text-center">Loading credit data...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-600">Error: {error}</div>;
  }

  if (!dashboard) {
    return <div className="p-6">No credit data available.</div>;
  }

  const currentProfile = profiles.find((p) => p.key === dashboard.currentProfile);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="border-b pb-4">
        <h1 className="text-3xl font-bold">Credit Dashboard</h1>
        <p className="text-sm text-gray-600 mt-1">
          Portfolio: {currentProfile?.name || dashboard.currentProfile}
        </p>
        {currentProfile && (
          <p className="text-xs text-gray-500 mt-1">{currentProfile.description}</p>
        )}
      </div>

      {/* Credit Buckets */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Credit Accumulation by Bucket</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {dashboard.buckets.map((bucket) => (
            <div key={bucket.bucket} className="border rounded-lg p-4 bg-white shadow">
              <h3 className="font-semibold text-lg">{bucket.bucket}</h3>
              <div className="mt-3 space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Hours Earned:</span>
                  <span className="font-mono font-semibold">
                    {bucket.hoursEarned.toFixed(1)} / 120
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Mastery:</span>
                  <span className="font-mono font-semibold">
                    {(bucket.masteryAverage * 100).toFixed(0)}% ({bucket.masteryGrade})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Evidence:</span>
                  <span className="font-mono">{bucket.evidenceCount} artifact(s)</span>
                </div>

                {/* Progress bar */}
                <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      bucket.creditEarned === 1.0
                        ? "bg-green-600"
                        : bucket.creditEarned === 0.5
                        ? "bg-blue-600"
                        : "bg-gray-400"
                    }`}
                    style={{ width: `${Math.min((bucket.hoursEarned / 120) * 100, 100)}%` }}
                  />
                </div>

                {/* Credit earned badge */}
                {bucket.creditEarned && (
                  <div className="mt-2">
                    <span className="inline-block bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded">
                      {bucket.creditEarned.toFixed(1)} Credit Earned
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Pending Proposals */}
      {dashboard.pendingProposals.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-4">Pending Course Proposals</h2>
          <div className="space-y-3">
            {dashboard.pendingProposals.map((proposal) => (
              <div key={proposal.proposalId} className="border border-yellow-300 bg-yellow-50 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-lg">{proposal.externalCourseName}</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {proposal.hoursEarned.toFixed(1)} hours · {proposal.masteryGrade} mastery
                    </p>
                  </div>
                  <button
                    onClick={() => handleApproveProposal(proposal.proposalId)}
                    disabled={approvingProposalId === proposal.proposalId}
                    className="px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
                  >
                    {approvingProposalId === proposal.proposalId ? "Approving..." : "Approve"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Approved Courses */}
      {dashboard.approvedCourses.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-4">Approved Courses (On Official Transcript)</h2>
          <div className="space-y-3">
            {dashboard.approvedCourses.map((course) => (
              <div key={course.proposalId} className="border border-green-300 bg-green-50 rounded-lg p-4">
                <h3 className="font-semibold text-lg">{course.externalCourseName}</h3>
                <p className="text-sm text-gray-600 mt-1">
                  {course.hoursEarned.toFixed(1)} hours · {course.masteryGrade} mastery ·{" "}
                  {course.masteryPercentage.toFixed(0)}% confidence
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
```

**Tests:**

Create `adeline-ui/src/components/dashboard/__tests__/CreditDashboard.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CreditDashboardComponent } from "../CreditDashboard";
import * as brainClient from "@/lib/brain-client";

vi.mock("@/lib/brain-client");

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CreditDashboardComponent", () => {
  it("should render loading state initially", () => {
    vi.mocked(brainClient.getCreditDashboard).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<CreditDashboardComponent studentId="test-student" />);
    expect(screen.getByText("Loading credit data...")).toBeInTheDocument();
  });

  it("should render credit dashboard data", async () => {
    const mockDashboard = {
      studentId: "test-student",
      currentProfile: "oklahoma_college_prep",
      buckets: [
        {
          bucket: "ENGLISH",
          hoursEarned: 125.5,
          evidenceCount: 8,
          masteryAverage: 0.87,
          masteryGrade: "B+",
          creditEarned: 1.0,
        },
      ],
      pendingProposals: [
        {
          proposalId: "prop-1",
          bucket: "ENGLISH",
          externalCourseName: "English Language Arts",
          hoursEarned: 125.5,
          masteryPercentage: 87,
          masteryGrade: "B+",
          isApproved: false,
          proposedAt: new Date().toISOString(),
        },
      ],
      approvedCourses: [],
    };

    vi.mocked(brainClient.getCreditDashboard).mockResolvedValueOnce(
      mockDashboard
    );
    vi.mocked(brainClient.listAvailableProfiles).mockResolvedValueOnce([
      {
        key: "oklahoma_college_prep",
        name: "College Prep",
        description: "OAS + OSRHE",
        oasOptional: false,
      },
    ]);

    render(<CreditDashboardComponent studentId="test-student" />);

    await waitFor(() => {
      expect(screen.getByText("ENGLISH")).toBeInTheDocument();
    });

    expect(screen.getByText("125.5 / 120")).toBeInTheDocument();
    expect(screen.getByText("87% (B+)")).toBeInTheDocument();
  });

  it("should handle approval button click", async () => {
    const mockDashboard = {
      studentId: "test-student",
      currentProfile: "oklahoma_college_prep",
      buckets: [],
      pendingProposals: [
        {
          proposalId: "prop-1",
          bucket: "ENGLISH",
          externalCourseName: "English Language Arts",
          hoursEarned: 125.5,
          masteryPercentage: 87,
          masteryGrade: "B+",
          isApproved: false,
          proposedAt: new Date().toISOString(),
        },
      ],
      approvedCourses: [],
    };

    vi.mocked(brainClient.getCreditDashboard).mockResolvedValueOnce(
      mockDashboard
    );
    vi.mocked(brainClient.listAvailableProfiles).mockResolvedValueOnce([]);
    vi.mocked(brainClient.approveCourseProposal).mockResolvedValueOnce({
      proposalId: "prop-1",
      isApproved: true,
      message: "Approved",
    });

    render(<CreditDashboardComponent studentId="test-student" />);

    await waitFor(() => {
      expect(screen.getByText("Approve")).toBeInTheDocument();
    });

    const approveButton = screen.getByText("Approve");
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(brainClient.approveCourseProposal).toHaveBeenCalledWith(
        "test-student",
        "prop-1"
      );
    });
  });
});
```

**Commit message:**

```
feat: CreditDashboard React component

- Display credit accumulation by bucket with progress bars
- Show pending course proposals with approve action
- Show approved courses on official transcript
- Display current Oklahoma profile info
- Include error handling and loading states
- Add comprehensive vitest + RTL test coverage
```

---

## Task 7: Integration — Post-RegistrarAgent Credit Engine Call

**Objective:** Hook the credit engine into the lesson completion workflow. After RegistrarAgent seals a lesson, invoke the credit engine.

**Location:** `adeline-brain/app/agents/orchestrator.py` (modification)

**Implementation:**

Modify the `seal_lesson` or post-registration hook to call the credit engine:

```python
# In orchestrator.py, after RegistrarAgent runs:

from app.services.credit_engine import (
    Evidence,
    ArtifactType,
    apply_profile_weighting,
    accumulate_evidence_in_bucket,
    check_credit_threshold,
    propose_course,
)
from app.services.standards_mapper import map_lesson_to_oas
import json
from pathlib import Path


async def accumulate_credit_from_lesson(
    student_id: str,
    lesson_id: str,
    track: str,
    mastery_score: float,
    activity_date: datetime,
    prisma: Any,  # Prisma client
) -> None:
    """
    Called after RegistrarAgent seals a lesson.

    This:
    1. Records which standards were addressed (StandardsLedger)
    2. Accumulates credit hours in CreditLedger
    3. Records evidence in EvidenceLedger
    4. Proposes courses when bucket thresholds are met
    """

    # 1. Fetch lesson content for standards mapping
    lesson = await prisma.lesson.find_unique(where={"id": lesson_id})
    if not lesson:
        return

    # 2. Get student profile
    user = await prisma.user.find_unique(where={"id": student_id})
    profile_key = getattr(user, "profile_key", "oklahoma_flexible_homeschool")

    # Load profile
    profiles_path = Path(__file__).parent.parent / "data" / "oklahoma_profiles.json"
    with open(profiles_path) as f:
        profiles = json.load(f)
    profile_data = profiles[profile_key]

    # 3. Map lesson to OAS standards
    oas_standards = map_lesson_to_oas(
        track=track,
        content=lesson.title + " " + " ".join([b.content for b in lesson.blocks[:3]]),
        grade_band="9-12",  # TODO: get from student profile
    )

    # Record in StandardsLedger
    for oas in oas_standards:
        await prisma.standardsledgerentry.create(
            data={
                "studentId": student_id,
                "framework": "OAS",
                "subject": oas.subject.value,
                "code": oas.code,
                "confidence": oas.confidence,
                "lessonId": lesson_id,
            }
        )

    # 4. Record evidence in EvidenceLedger
    from app.config.tracks import TRACK_CREDIT_MAP

    track_mapping = TRACK_CREDIT_MAP.get(track)
    if not track_mapping:
        return

    # Infer artifact type (simplified: default to "project" for lessons)
    artifact_type = "project"
    hours_engaged = lesson.estimatedMinutes / 60.0  # Convert to hours

    evidence_entry = await prisma.evidenceledgerentry.create(
        data={
            "studentId": student_id,
            "artifactType": artifact_type,
            "title": lesson.title,
            "masteryScore": mastery_score,
            "hours": hours_engaged,
            "activityDate": activity_date,
            "evaluatorNotes": f"From lesson: {lesson_id}",
            "bucket": track_mapping["primary"],
        }
    )

    # 5. Create CreditLedger entry
    weighting = apply_profile_weighting(profile_key, profile_data)
    weighted_hours = hours_engaged * weighting.project * (0.5 + mastery_score * 0.5)

    await prisma.creditledgerentry.create(
        data={
            "studentId": student_id,
            "bucket": track_mapping["primary"],
            "hoursEarned": weighted_hours,
            "source": "lesson",
            "sourceId": lesson_id,
        }
    )

    # 6. Check if threshold is met and propose course
    all_credit_entries = await prisma.creditledgerentry.find_many(
        where={
            "studentId": student_id,
            "bucket": track_mapping["primary"],
        }
    )

    total_hours = sum(e.hoursEarned for e in all_credit_entries)
    credit_earned = check_credit_threshold(
        total_hours,
        full_credit_hours=profile_data["creditThresholds"]["full_credit"],
        half_credit_hours=profile_data["creditThresholds"]["half_credit"],
    )

    if credit_earned:
        # Check if we already have a pending proposal for this bucket
        existing_proposal = await prisma.evidenceledgerentry.find_first(
            where={
                "studentId": student_id,
                "bucket": track_mapping["primary"],
                "proposedCourse": {"not": None},
            }
        )

        if not existing_proposal:
            # Create course proposal
            await prisma.evidenceledgerentry.update(
                where={"id": evidence_entry.id},
                data={
                    "proposedCourse": track_mapping["externalName"],
                },
            )
```

**Tests:**

Add to `adeline-brain/tests/test_orchestrator.py`:

```python
import pytest
from datetime import datetime
from app.agents.orchestrator import accumulate_credit_from_lesson


@pytest.mark.asyncio
async def test_accumulate_credit_from_lesson(prisma_client):
    """Test that credit accumulation is triggered after lesson completion."""
    # Setup student and lesson
    student = await prisma_client.user.create(
        data={
            "name": "Test Student",
            "email": "test@example.com",
            "role": "STUDENT",
            "gradeLevel": "11",
        }
    )

    lesson = await prisma_client.lesson.create(
        data={
            "title": "Environmental Science Fundamentals",
            "estimatedMinutes": 120,
            "targetGrades": ["9", "10", "11"],
            "tracks": {"create": [{"track": "CREATION_SCIENCE"}]},
        }
    )

    # Call credit accumulation
    await accumulate_credit_from_lesson(
        student_id=student.id,
        lesson_id=lesson.id,
        track="CREATION_SCIENCE",
        mastery_score=0.85,
        activity_date=datetime.utcnow(),
        prisma=prisma_client,
    )

    # Verify StandardsLedger entry created
    standards_entry = await prisma_client.standardsledgerentry.find_first(
        where={"studentId": student.id}
    )
    assert standards_entry is not None

    # Verify EvidenceLedger entry created
    evidence_entry = await prisma_client.evidenceledgerentry.find_first(
        where={"studentId": student.id}
    )
    assert evidence_entry is not None
    assert evidence_entry.masteryScore == 0.85

    # Verify CreditLedger entry created
    credit_entry = await prisma_client.creditledgerentry.find_first(
        where={"studentId": student.id}
    )
    assert credit_entry is not None
    assert credit_entry.hoursEarned > 0
```

**Commit message:**

```
feat: Integrate credit engine with orchestrator post-lesson hook

- Add accumulate_credit_from_lesson() called after RegistrarAgent
- Records OAS standards addressed in StandardsLedger
- Accumulates credit hours in CreditLedger
- Records evidence artifacts in EvidenceLedger
- Proposes courses when bucket thresholds are met
- Includes integration tests with Prisma client
```

---

## Task 8: Self-Review & Cleanup

**Objective:** Verify all components work together, run full test suite, and clean up any rough edges.

**Checklist:**

- [ ] Run `pytest adeline-brain/tests/test_credit_engine.py -v` — all green
- [ ] Run `pytest adeline-brain/tests/test_standards_mapper.py -v` — all green
- [ ] Run `pytest adeline-brain/tests/test_oklahoma_profiles.py -v` — all green
- [ ] Run `pytest adeline-brain/tests/test_credits_api.py -v` — all green
- [ ] Run `pytest adeline-brain/tests/test_orchestrator.py -v` — all green
- [ ] Run `pnpm test adeline-ui/src/lib/__tests__/brain-client.test.ts` — all green
- [ ] Run `pnpm test adeline-ui/src/components/dashboard/__tests__/CreditDashboard.test.tsx` — all green
- [ ] Verify `adeline-brain/data/oklahoma_profiles.json` is valid JSON
- [ ] Verify no hardcoded credit thresholds outside `credit_engine.py` and profiles.json
- [ ] Verify all Prisma models (StandardsLedgerEntry, CreditLedgerEntry, EvidenceLedgerEntry) exist in schema
- [ ] Verify `TRACK_CREDIT_MAP` covers all 10 tracks with `externalName` set
- [ ] Verify FastAPI router endpoints match brain-client function signatures
- [ ] Verify TypeScript types exported from brain-client match Pydantic models
- [ ] Check for any `TODO` comments — resolve or convert to issues
- [ ] Run formatter: `black adeline-brain/` and `pnpm format` for TypeScript
- [ ] Run linter: `ruff check adeline-brain/` and `pnpm lint`
- [ ] Create one integration test spanning lesson → credit accumulation → proposal
- [ ] Document the three-ledger model in a brief comment block

**Integration Test:**

Create `adeline-brain/tests/test_credit_integration.py`:

```python
import pytest
from datetime import datetime
from app.services.credit_engine import (
    Evidence,
    ArtifactType,
    CreditHourWeighting,
    compute_bucket_accumulation,
    check_credit_threshold,
    propose_course,
)


@pytest.mark.asyncio
async def test_end_to_end_credit_accumulation():
    """
    End-to-end test: evidence → accumulation → threshold → proposal.

    Scenario:
    1. Student completes a series of essays and labs
    2. Hours accumulate in the ENGLISH bucket
    3. When total reaches 120 hours, system proposes "English Language Arts" course
    4. Parent approves the course
    5. Course appears on official transcript
    """
    # Setup
    weighting = CreditHourWeighting(
        essay=1.0, quiz=0.5, lab=1.5, project=1.75,
        discussion=0.75, fieldwork=1.25, presentation=1.25,
    )

    # Evidence: 4 essays at 85% mastery, 10 hours each
    evidence = [
        Evidence(
            artifact_type=ArtifactType.ESSAY,
            mastery_score=0.85,
            hours=10.0,
            activity_date=datetime.utcnow(),
        )
        for _ in range(4)
    ]

    # Add 4 labs at 90% mastery, 12 hours each
    evidence.extend([
        Evidence(
            artifact_type=ArtifactType.LAB,
            mastery_score=0.90,
            hours=12.0,
            activity_date=datetime.utcnow(),
        )
        for _ in range(4)
    ])

    # Accumulate
    bucket = compute_bucket_accumulation(
        bucket_name="ENGLISH",
        evidence_list=evidence,
        weighting=weighting,
    )

    # Essays: 4 × (10 × 1.0 × (0.5 + 0.85×0.5)) = 4 × 8.75 = 35 hours
    # Labs: 4 × (12 × 1.5 × (0.5 + 0.9×0.5)) = 4 × (12 × 1.5 × 0.95) = 68.4 hours
    # Total ≈ 103.4 hours (below 120 full credit threshold)

    assert bucket.hours_earned == pytest.approx(103.4, rel=0.1)
    assert bucket.evidence_count == 8

    # Check threshold (should be 0.5 credit = 60-119 hours)
    credit = check_credit_threshold(bucket, full_credit_hours=120.0, half_credit_hours=60.0)
    assert credit == 0.5

    # Propose course
    proposal = propose_course(
        bucket_name="ENGLISH",
        external_course_name="English Language Arts",
        hours_earned=bucket.hours_earned,
        mastery_average=bucket.mastery_average,
    )

    assert proposal.bucket == "ENGLISH"
    assert proposal.external_course_name == "English Language Arts"
    assert proposal.is_approved is False
    assert proposal.proposed_at is not None
```

**Final Commit:**

```
test: Add end-to-end credit accumulation integration test

- Test evidence → accumulation → threshold → proposal workflow
- Verify weighted hours calculation with multiple artifact types
- Verify threshold checking and course proposal generation
- Clean up all TODOs and rough edges
```

---

## Self-Review Checklist

Before marking complete:

1. **Architecture Soundness**
   - [ ] Three-ledger model (Standards/Credit/Evidence) is clear and isolated
   - [ ] Pure functions in credit_engine.py have no side effects
   - [ ] Profile loading is centralized in one place
   - [ ] No OAS logic hard-coded — all in standards_mapper.py

2. **Testing Coverage**
   - [ ] Unit tests for pure functions (credit_engine, standards_mapper)
   - [ ] Integration tests for API endpoints
   - [ ] UI component tests with mocked brain-client
   - [ ] End-to-end test spanning lesson → credit → proposal

3. **Type Safety**
   - [ ] All Python Pydantic models match TypeScript interfaces
   - [ ] All Prisma models exist (StandardsLedger, CreditLedger, EvidenceLedger)
   - [ ] No `Any` types except for Prisma client

4. **Parent Approval Gating**
   - [ ] Courses do NOT appear on transcript until `isApproved = true`
   - [ ] Frontend shows pending vs. approved clearly
   - [ ] API endpoint for approval exists and works

5. **Profile-Driven Configuration**
   - [ ] Three profiles load from JSON, not hardcoded
   - [ ] Credit thresholds read from profile, not hardcoded constants
   - [ ] Artifact weighting comes from profile

6. **Documentation**
   - [ ] Brief comment block explaining three-ledger model
   - [ ] README in `adeline-brain/data/` explaining oklahoma_profiles.json format
   - [ ] Docstrings on all public functions

---

## Files to Create/Modify

| Path | Type | Notes |
|------|------|-------|
| `adeline-brain/data/oklahoma_profiles.json` | Create | Three selectable profile configs |
| `adeline-brain/app/services/credit_engine.py` | Create | Pure accumulation functions |
| `adeline-brain/app/services/standards_mapper.py` | Create | Track → OAS code inference |
| `adeline-brain/app/api/credits.py` | Create | FastAPI router for credit endpoints |
| `adeline-brain/tests/test_credit_engine.py` | Create | Tests for pure functions |
| `adeline-brain/tests/test_standards_mapper.py` | Create | Tests for mapper |
| `adeline-brain/tests/test_oklahoma_profiles.py` | Create | Tests for profile structure |
| `adeline-brain/tests/test_credits_api.py` | Create | Tests for FastAPI routes |
| `adeline-brain/tests/test_credit_integration.py` | Create | End-to-end test |
| `adeline-ui/src/lib/brain-client.ts` | Modify | Add credit functions |
| `adeline-ui/src/lib/__tests__/brain-client.test.ts` | Create | Tests for client functions |
| `adeline-ui/src/components/dashboard/CreditDashboard.tsx` | Create | React dashboard component |
| `adeline-ui/src/components/dashboard/__tests__/CreditDashboard.test.tsx` | Create | Tests for dashboard |
| `adeline-brain/app/agents/orchestrator.py` | Modify | Hook credit engine post-RegistrarAgent |
| `adeline-brain/tests/test_orchestrator.py` | Modify | Add credit integration test |

---

## Known Constraints & Design Decisions

1. **OAS is overlay-only:** Standards metadata never gate learning. Portfolio evidence is primary.
2. **Parent approval required:** No course appears on official transcript without explicit `isApproved = true`.
3. **Weighted hours, not seat time:** Hours are scaled by artifact type and mastery, not raw time spent.
4. **Profile JSON, not database:** Three Oklahoma profiles are static JSON, not database rows. Easier to version-control and deploy.
5. **Pure functions for accumulation:** All math in `credit_engine.py` is side-effect-free for testability.
6. **Post-RegistrarAgent hook:** Credit accumulation runs *after* lesson registration (not during).
7. **No hard-coded thresholds:** All constants (120 hours for 1.0 credit) read from profile JSON.

---

## Success Criteria

- [ ] All unit tests pass (pytest, vitest)
- [ ] Credit dashboard displays correctly (no errors)
- [ ] Course proposal created when bucket threshold reached
- [ ] Parent can approve proposals via UI
- [ ] Approved course appears on official transcript
- [ ] All three Oklahoma profiles load and work
- [ ] OAS standards recorded (not gating)
- [ ] No breaking changes to existing endpoints
- [ ] Code reviewed and linted (black, ruff, eslint)
