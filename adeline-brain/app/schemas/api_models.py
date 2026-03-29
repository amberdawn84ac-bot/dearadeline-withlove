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
    APPLIED_MATHEMATICS  = "APPLIED_MATHEMATICS"


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
    EXPERIMENT       = "EXPERIMENT"
    RESEARCH_MISSION = "RESEARCH_MISSION"
    QUIZ             = "QUIZ"


# ── Chaos Levels (Science Experiment difficulty/safety) ──────────────────────

class ChaosLevel(int, Enum):
    SPROUT    = 1   # 🌱 Kitchen table; paper towels only
    SCOUT     = 2   # 🔭 Driveway/backyard; wear old clothes
    SOVEREIGN = 3   # 🔥 Open field; fire extinguisher & Dad required


class ScienceCredit(str, Enum):
    LABORATORY_SCIENCE = "LABORATORY_SCIENCE"
    PHYSICS            = "PHYSICS"
    CHEMISTRY          = "CHEMISTRY"
    BIOLOGY            = "BIOLOGY"
    EARTH_SCIENCE      = "EARTH_SCIENCE"


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


# ── Experiment (Sovereign Lab — CREATION_SCIENCE experiments) ────────────────

class ExperimentStep(BaseModel):
    step_number: int
    instruction: str
    tip:         str = ""  # optional safety/technique tip

class SocialMediaKit(BaseModel):
    caption_template: str = ""               # e.g. "Adeline taught us THIS today 🧪🔥"
    filming_tips:     list[str] = Field(default_factory=list)  # "Use slow-mo", "Get the reaction shot"
    hashtags:         list[str] = Field(default_factory=list)

class CreationConnection(BaseModel):
    """The 'God's Creation' bridge — why this experiment points to design."""
    title:      str             # e.g. "Catalysts in the Human Body"
    scripture:  str = ""        # e.g. "Psalm 139:14 — fearfully and wonderfully made"
    explanation: str            # 2-3 sentences connecting the science to God's design

class Experiment(BaseModel):
    id:                   str = Field(default_factory=lambda: str(uuid.uuid4()))
    title:                str                                 # "Elephant Toothpaste"
    tagline:              str = ""                             # "The loudest way to learn decomposition"
    chaos_level:          ChaosLevel                          # SPROUT / SCOUT / SOVEREIGN
    wow_factor:           int = Field(ge=1, le=10, default=8) # 1-10 spectacle rating
    scientific_concepts:  list[str]                            # ["exothermic reactions", "decomposition", "catalysts"]
    science_credits:      list[ScienceCredit]                  # what the Registrar grants
    grade_band:           str = "3-12"                         # applicable grade range
    materials:            list[str]                            # shopping/pantry list
    safety_requirements:  list[str] = Field(default_factory=list)
    steps:                list[ExperimentStep]
    creation_connection:  CreationConnection
    social_media_kit:     SocialMediaKit = Field(default_factory=SocialMediaKit)
    estimated_minutes:    int = 30
    track:                Track = Track.CREATION_SCIENCE

class ExperimentResponse(BaseModel):
    """Returned from GET /experiments and POST /experiments/start."""
    experiment:           Experiment
    student_materials_ready: bool = False
    video_upload_url:     str = ""
