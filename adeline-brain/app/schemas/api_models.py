"""
Pydantic models for adeline-brain.
These mirror adeline-core/src/types.ts — the source of truth.
Re-generate core_schema.json from TypeScript to validate sync.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid


# ── Tracks (mirrors Track enum in types.ts) ───────────────────────────────────

class Track(str, Enum):
    CREATION_SCIENCE     = "CREATION_SCIENCE"
    HEALTH_NATUROPATHY   = "HEALTH_NATUROPATHY"
    HOMESTEADING         = "HOMESTEADING"
    GOVERNMENT_ECONOMICS = "GOVERNMENT_ECONOMICS"
    JUSTICE_CHANGEMAKING = "JUSTICE_CHANGEMAKING"
    DISCIPLESHIP         = "DISCIPLESHIP"
    TRUTH_HISTORY        = "TRUTH_HISTORY"
    ENGLISH_LITERATURE   = "ENGLISH_LITERATURE"


# ── Witness Protocol (mirrors TRUTH_THRESHOLD + EvidenceVerdict in types.ts) ──

TRUTH_THRESHOLD = 0.82  # text-embedding-3-small peaks ~0.84 for high-confidence matches

class EvidenceVerdict(str, Enum):
    VERIFIED         = "VERIFIED"
    ARCHIVE_SILENT   = "ARCHIVE_SILENT"
    RESEARCH_MISSION = "RESEARCH_MISSION"


# ── Block Types (mirrors BlockType in types.ts) ───────────────────────────────

class BlockType(str, Enum):
    TEXT             = "TEXT"
    NARRATIVE        = "NARRATIVE"
    PRIMARY_SOURCE   = "PRIMARY_SOURCE"
    LAB_MISSION      = "LAB_MISSION"
    RESEARCH_MISSION = "RESEARCH_MISSION"
    QUIZ             = "QUIZ"


# ── User Roles (mirrors UserRole in types.ts) ─────────────────────────────────

class UserRole(str, Enum):
    STUDENT = "STUDENT"
    PARENT  = "PARENT"
    ADMIN   = "ADMIN"


# ── Evidence (mirrors EvidenceSchema in types.ts) ─────────────────────────────

class WitnessCitation(BaseModel):
    author:       str = ""
    year:         Optional[int] = None
    archive_name: str = ""

class Evidence(BaseModel):
    source_id:        str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_title:     str
    source_url:       str = ""
    witness_citation: WitnessCitation = Field(default_factory=WitnessCitation)
    similarity_score: float = Field(ge=0.0, le=1.0)
    verdict:          EvidenceVerdict
    chunk:            str

    @field_validator("similarity_score")
    @classmethod
    def score_must_be_valid(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("similarity_score must be between 0 and 1")
        return v


# ── User (mirrors UserSchema in types.ts) ─────────────────────────────────────

class User(BaseModel):
    id:          str = Field(default_factory=lambda: str(uuid.uuid4()))
    name:        str
    email:       str
    role:        UserRole
    is_homestead: bool = False
    grade_level: Optional[str] = None

    @field_validator("grade_level")
    @classmethod
    def grade_required_for_students(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("role") == UserRole.STUDENT and v is None:
            raise ValueError("grade_level is required for STUDENT role")
        return v


# ── Lesson Request / Response ─────────────────────────────────────────────────

class LessonRequest(BaseModel):
    student_id:  str
    track:       Track
    topic:       str
    is_homestead: bool = False
    grade_level: str

class LessonBlockResponse(BaseModel):
    block_id:         str = Field(default_factory=lambda: str(uuid.uuid4()))
    block_type:       BlockType
    content:          str
    evidence:         list[Evidence] = []
    is_silenced:      bool = False
    homestead_content: Optional[str] = None

class LessonResponse(BaseModel):
    lesson_id:            str = Field(default_factory=lambda: str(uuid.uuid4()))
    title:                str
    track:                Track
    blocks:               list[LessonBlockResponse]
    has_research_missions: bool = False
    oas_standards:        list[dict] = Field(default_factory=list)
    researcher_activated: bool = False   # True when auto-search ran during generation
    agent_name:           str = ""       # Which specialist agent handled this lesson
    xapi_statements:      list[dict] = Field(default_factory=list)  # xAPI records (Phase 6 persists these)
    credits_awarded:      list[dict] = Field(default_factory=list)  # CASE credit entries
