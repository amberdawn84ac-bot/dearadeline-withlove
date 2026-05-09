"""
Pydantic models for adeline-brain.
These mirror adeline-core/src/types.ts — the source of truth.
Re-generate core_schema.json from TypeScript to validate sync.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
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
    CREATIVE_ECONOMY     = "CREATIVE_ECONOMY"


# ── Witness Protocol (mirrors TRUTH_THRESHOLD + EvidenceVerdict in types.ts) ──

TRUTH_THRESHOLD = 0.82  # text-embedding-3-small peaks ~0.84 for high-confidence matches

class EvidenceVerdict(str, Enum):
    VERIFIED         = "VERIFIED"
    ARCHIVE_SILENT   = "ARCHIVE_SILENT"
    RESEARCH_MISSION = "RESEARCH_MISSION"


class SourceType(str, Enum):
    """What kind of archive this evidence came from."""
    PRIMARY_SOURCE        = "PRIMARY_SOURCE"        # Historical primary sources (TRUTH_HISTORY)
    DECLASSIFIED_GOV      = "DECLASSIFIED_GOV"      # Declassified government documents
    ARCHIVE_ORG           = "ARCHIVE_ORG"           # Archive.org materials
    ACADEMIC_JOURNAL      = "ACADEMIC_JOURNAL"      # Academic research
    PERSONAL_COLLECTION   = "PERSONAL_COLLECTION"   # Personal archives
    INVESTIGATIVE_REPORT  = "INVESTIGATIVE_REPORT"  # Investigative journalism (Justice)
    LEGAL_DOCUMENT        = "LEGAL_DOCUMENT"        # Court opinions, legal filings (Justice)
    LEGISLATIVE_RECORD    = "LEGISLATIVE_RECORD"    # Congressional records (Justice)
    DISCLOSURE_FORM       = "DISCLOSURE_FORM"       # Lobbying disclosures (Justice)
    TESTIMONY             = "TESTIMONY"             # Testimonies and oral histories (Justice)
    DOCUMENT              = "DOCUMENT"              # Generic document

SOURCE_TYPE_LABELS = {
    "PRIMARY_SOURCE":        "Primary Source",
    "DECLASSIFIED_GOV":      "Declassified Document",
    "ARCHIVE_ORG":           "Archive.org",
    "ACADEMIC_JOURNAL":      "Academic Journal",
    "PERSONAL_COLLECTION":   "Personal Collection",
    "INVESTIGATIVE_REPORT":  "Investigative Report",
    "LEGAL_DOCUMENT":        "Legal Document",
    "LEGISLATIVE_RECORD":    "Legislative Record",
    "DISCLOSURE_FORM":       "Disclosure Form",
    "TESTIMONY":             "Testimony",
    "DOCUMENT":              "Document",
}

DECLASSIFIED_COLLECTIONS = {
    "NARA":                 "https://catalog.archives.gov/search",
    "CIA_FOIA":             "https://www.cia.gov/information-freedom/records-available-online/",
    "FBI_VAULT":            "https://vault.fbi.gov/",
    "CONGRESSIONAL_RECORD": "https://www.congress.gov/congressional-record/",
    "FEDERAL_REGISTER":     "https://www.federalregister.gov/",
    "DNSA":                 "https://nsarchive.gwu.edu/",
}


# ── Block Types (mirrors BlockType in types.ts) ───────────────────────────────

class BlockType(str, Enum):
    TEXT             = "TEXT"
    NARRATIVE        = "NARRATIVE"
    PRIMARY_SOURCE   = "PRIMARY_SOURCE"
    LAB_MISSION      = "LAB_MISSION"
    EXPERIMENT       = "EXPERIMENT"
    RESEARCH_MISSION = "RESEARCH_MISSION"
    QUIZ             = "QUIZ"
    MIND_MAP         = "MIND_MAP"
    TIMELINE         = "TIMELINE"
    MNEMONIC         = "MNEMONIC"
    NARRATED_SLIDE   = "NARRATED_SLIDE"
    BOOK_SUGGESTION  = "BOOK_SUGGESTION"
    ANIMATED_SKETCHNOTE_LESSON = "ANIMATED_SKETCHNOTE_LESSON"


# ── Multimodal Data Models ────────────────────────────────────────────────────

class MindMapNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    children: list["MindMapNode"] = []

MindMapNode.model_rebuild()

class MindMapData(BaseModel):
    concept: str
    root: MindMapNode

class TimelineEvent(BaseModel):
    date: str = Field(description="Year or date string, e.g. '1865', 'March 3, 1865'. Use consistent format within a timeline.")
    label: str
    description: str
    source_title: str = ""

class TimelineData(BaseModel):
    span: str
    events: list[TimelineEvent]

class MnemonicData(BaseModel):
    concept: str
    acronym: str
    words: list[str]
    tip: str

    @model_validator(mode="after")
    def words_match_acronym(self) -> "MnemonicData":
        if len(self.words) != len(self.acronym):
            raise ValueError(
                f"MnemonicData: words length ({len(self.words)}) must equal "
                f"acronym length ({len(self.acronym)})"
            )
        return self

class NarratedSlide(BaseModel):
    slide_number: int = Field(ge=1)
    title: str
    bullets: list[str]
    narration: str

class NarratedSlideData(BaseModel):
    total_duration_minutes: float
    slides: list[NarratedSlide]


# ── Animated Sketchnote Lesson Data Models ────────────────────────────────────

class StyledTextModel(BaseModel):
    text: str
    style: str  # bold_marker | block_caps | script_hand | sketch_print | tiny_notes | label | caption
    layout: str  # title_banner | section_header | callout_bubble | flow_step | side_note | diagram_label | closing_quote
    decoration: list[str] = []
    emphasis: Optional[str] = None  # low | medium | high

class VisualElementModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # handwritten_text | doodle | diagram | arrow | bubble | label | icon | character | background | timeline | split_screen
    content: str
    position: dict  # {x: 0-100, y: 0-100}
    size: Optional[dict] = None  # {width: 0-100, height: 0-100}
    style: Optional[str] = None
    color: Optional[str] = None

class AnimationInstructionModel(BaseModel):
    elementId: str
    animation: str  # draw_in | write_on | fade_in | pop_in | slide_in | zoom_in | pulse | wiggle | pan | morph | highlight
    startTime: float
    duration: float
    easing: Optional[str] = None  # linear | ease_in | ease_out | ease_in_out

class AnimatedSceneModel(BaseModel):
    sceneNumber: int
    sceneTitle: StyledTextModel
    durationSeconds: float
    narration: str
    visualBuild: list[VisualElementModel] = []
    animationPlan: list[AnimationInstructionModel] = []
    teachingLayer: dict  # {visualSummary, deepExplanation, whyItMatters, activity?}
    soundDesign: Optional[dict] = None
    narrationAudioUrl: Optional[str] = None  # filled after pyttsx3 TTS

class AnimatedSketchnoteLessonData(BaseModel):
    lessonType: str = "animated_sketchnote_lesson"
    title: StyledTextModel
    subtitle: StyledTextModel
    targetAges: str
    totalDurationSeconds: float
    learningGoals: list[str] = []
    colorPalette: list[str] = []
    visualStyle: dict  # {format, artDirection, typography, illustrationRules, layoutRules}
    scenes: list[AnimatedSceneModel] = []
    fullNarrationScript: str = ""
    vocabulary: list[dict] = []   # [{word, definition, visualCue}]
    assessment: list[dict] = []   # [{question, answer, type}]
    extensionActivities: list[dict] = []  # [{title, instructions, materials?}]

class AnimatedLessonRequest(BaseModel):
    topic: str
    focus: str = ""
    duration_seconds: int = 180
    target_ages: str = "10-15"
    track: Optional[Track] = None
    student_id: Optional[str] = None

class NarrateRequest(BaseModel):
    text: str
    voice_rate: int = 160  # words per minute


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
    source_type:      str = "PRIMARY_SOURCE"
    witness_citation: WitnessCitation = Field(default_factory=WitnessCitation)
    similarity_score: float = Field(ge=0.0, le=1.0)
    verdict:          Optional[EvidenceVerdict] = None
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
    render_mode: Optional[str] = None  # "animated_sketchnote_lesson" triggers sketchnote synthesis
    force_regenerate: bool = False  # Bypass canonical cache and regenerate fresh lesson content

class LessonBlockResponse(BaseModel):
    block_id:         str = Field(default_factory=lambda: str(uuid.uuid4()))
    block_type:       str   # BlockType or GenUIBlockType — adapter may produce any of 15 types
    content:          str
    evidence:         list[Evidence] = []
    is_silenced:      bool = False
    homestead_content: Optional[str] = None
    mind_map_data:        Optional[MindMapData] = None
    timeline_data:        Optional[TimelineData] = None
    mnemonic_data:        Optional[MnemonicData] = None
    narrated_slide_data:  Optional[NarratedSlideData] = None
    # Interface-generative fields — populated by adapter when transforming block type
    quiz_data:            Optional[dict] = None   # QuizData: {question, options, explanation, difficulty}
    flashcard_data:       Optional[dict] = None   # FlashcardData: {front, back, category}
    experiment_data:      Optional[dict] = None   # ExperimentData: {title, materials, steps, ...}
    book_id:              Optional[str] = None
    book_title:           Optional[str] = None
    book_author:          Optional[str] = None
    epub_url:             Optional[str] = None
    cover_url:            Optional[str] = None
    lexile_level:         Optional[int] = None
    animated_sketchnote_data: Optional[AnimatedSketchnoteLessonData] = None

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


class CanonicalLessonRecord(BaseModel):
    """Persistent master lesson for a topic+track. Adapted per student at serve time."""
    id:                  str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic_slug:          str                        # sha256(topic.lower()+":"+track)
    topic:               str
    track:               Track
    title:               str
    blocks:              list[LessonBlockResponse]  # full-depth, adult/HS level
    oas_standards:       list[dict] = Field(default_factory=list)
    researcher_activated: bool = False
    agent_name:          str = ""


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


# ── Projects (CREATIVE_ECONOMY + HOMESTEADING project library) ───────────────

class ProjectDifficulty(int, Enum):
    SEEDLING = 1   # beginner — a few hours, basic materials
    GROWER   = 2   # intermediate — half day, some tools
    BUILDER  = 3   # advanced — full weekend+, real construction

class ProjectCategory(str, Enum):
    CRAFT     = "CRAFT"      # making/crafting (CREATIVE_ECONOMY)
    MARKET    = "MARKET"     # branding and selling (CREATIVE_ECONOMY)
    GARDEN    = "GARDEN"     # growing food (HOMESTEADING)
    LIVESTOCK = "LIVESTOCK"  # animals (HOMESTEADING)
    BUILD     = "BUILD"      # construction (HOMESTEADING)
    PRESERVE  = "PRESERVE"   # food preservation (HOMESTEADING)

class ProjectStep(BaseModel):
    step_number: int
    instruction: str
    tip: Optional[str] = None

class PriceRange(BaseModel):
    low: float
    high: float
    unit: str = "per item"

class Project(BaseModel):
    id:               str
    title:            str
    track:            Track
    category:         ProjectCategory
    difficulty:       ProjectDifficulty
    tagline:          str
    skills:           list[str]
    business_skills:  list[str] = []
    materials:        list[str]
    steps:            list[ProjectStep]
    estimated_hours:  float
    price_range:      Optional[PriceRange] = None
    where_to_sell:    list[str] = []
    portfolio_prompts: list[str]
    safety_notes:     list[str] = []
    income_description: str = ""
    grade_band:       str = "5-12"

class ProjectSealRequest(BaseModel):
    student_id: str
    project_id: str
    reflection: str = ""

class ProjectSealResponse(BaseModel):
    project_id:   str
    credit_type:  str
    credit_hours: float
    message:      str

class ProjectStartRequest(BaseModel):
    student_id: str
    project_id: str

class ProjectStartResponse(BaseModel):
    project_id: str
    message:    str
