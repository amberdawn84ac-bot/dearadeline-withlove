"""
GenUI Schema — Structured output schemas for generative UI blocks.

These Pydantic models enforce strict JSON structure from LLM outputs,
ensuring Adeline generates valid interactive UI components.

Usage with OpenAI:
    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_schema", "json_schema": GenerativeLesson.model_json_schema()},
        messages=[...]
    )

Usage with Anthropic (tool use):
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        tools=[{"name": "generate_lesson", "input_schema": GenerativeLesson.model_json_schema()}],
        messages=[...]
    )
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field


# ── Block Type Enum ──────────────────────────────────────────────────────────

class GenUIBlockType(str, Enum):
    """All interactive block types Adeline can generate."""
    PRIMARY_SOURCE   = "PRIMARY_SOURCE"
    LAB_MISSION      = "LAB_MISSION"
    EXPERIMENT       = "EXPERIMENT"
    NARRATIVE        = "NARRATIVE"
    RESEARCH_MISSION = "RESEARCH_MISSION"
    QUIZ             = "QUIZ"
    FLASHCARD        = "FLASHCARD"
    MIND_MAP         = "MIND_MAP"
    TIMELINE         = "TIMELINE"
    MNEMONIC         = "MNEMONIC"
    NARRATED_SLIDE   = "NARRATED_SLIDE"
    BOOK_SUGGESTION  = "BOOK_SUGGESTION"
    TEXT             = "TEXT"
    INTERACTIVE_SIM  = "INTERACTIVE_SIM"
    HIGHLIGHT_ASK    = "HIGHLIGHT_ASK"


# ── Individual Block Data Schemas ────────────────────────────────────────────

class QuizOption(BaseModel):
    """A single quiz option."""
    text: str = Field(..., description="The option text")
    is_correct: bool = Field(False, description="Whether this is the correct answer")


class QuizData(BaseModel):
    """Data for a QUIZ block — interactive multiple choice."""
    question: str = Field(..., description="The quiz question")
    options: List[QuizOption] = Field(..., min_length=2, max_length=5, description="Answer options")
    explanation: str = Field(..., description="Explanation shown after answering")
    difficulty: Literal["easy", "medium", "hard"] = Field("medium", description="Question difficulty")


class FlashcardData(BaseModel):
    """Data for a FLASHCARD block — flippable card."""
    front: str = Field(..., description="Front of card (term/question)")
    back: str = Field(..., description="Back of card (definition/answer)")
    category: Optional[str] = Field(None, description="Optional category label")


class TimelineEvent(BaseModel):
    """A single event on a timeline."""
    date: str = Field(..., description="Date or time period (e.g., '1863', 'March 1865')")
    label: str = Field(..., description="Short event title")
    description: str = Field(..., description="1-2 sentence description")
    source_title: Optional[str] = Field(None, description="Primary source reference")


class TimelineData(BaseModel):
    """Data for a TIMELINE block — chronological events."""
    span: str = Field(..., description="Time range (e.g., '1860-1870')")
    events: List[TimelineEvent] = Field(..., min_length=2, description="Timeline events")


class MindMapNode(BaseModel):
    """A node in a mind map."""
    id: str = Field(..., description="Unique node ID")
    label: str = Field(..., description="Node label text")
    children: List[MindMapNode] = Field(default_factory=list, description="Child nodes")


class MindMapData(BaseModel):
    """Data for a MIND_MAP block — concept hierarchy."""
    concept: str = Field(..., description="Central concept being mapped")
    root: MindMapNode = Field(..., description="Root node of the mind map")


class MnemonicData(BaseModel):
    """Data for a MNEMONIC block — memory aid."""
    phrase: str = Field(..., description="The mnemonic phrase")
    breakdown: List[str] = Field(..., description="What each letter/word represents")
    concept: str = Field(..., description="What this helps remember")


class NarratedSlide(BaseModel):
    """A single slide in a narrated presentation."""
    slide_number: int = Field(..., ge=1, description="Slide number")
    title: str = Field(..., description="Slide title")
    bullets: List[str] = Field(..., max_length=5, description="Bullet points")
    narration: str = Field(..., description="30-60 second spoken script")


class NarratedSlideData(BaseModel):
    """Data for a NARRATED_SLIDE block — presentation deck."""
    total_duration_minutes: float = Field(..., description="Estimated total duration")
    slides: List[NarratedSlide] = Field(..., min_length=1, description="Slide deck")


class ExperimentData(BaseModel):
    """Data for an EXPERIMENT block — hands-on science."""
    title: str = Field(..., description="Experiment title")
    tagline: str = Field(..., description="Catchy one-liner")
    materials: List[str] = Field(..., description="Required materials")
    steps: List[str] = Field(..., description="Step-by-step instructions")
    scientific_concepts: List[str] = Field(..., description="Concepts being demonstrated")
    creation_connection: Optional[str] = Field(None, description="Biblical/creation worldview tie-in")
    safety_notes: Optional[str] = Field(None, description="Safety warnings if any")


class BookSuggestionData(BaseModel):
    """Data for a BOOK_SUGGESTION block — reading recommendation."""
    title: str = Field(..., description="Book title")
    author: str = Field(..., description="Author name")
    why_read: str = Field(..., description="Why this book connects to the lesson")
    reading_level: Optional[str] = Field(None, description="Lexile or grade level")


class InteractiveSimData(BaseModel):
    """Data for an INTERACTIVE_SIM block — simulation/visualization."""
    sim_type: str = Field(..., description="Type of simulation (e.g., 'physics', 'timeline', 'map')")
    title: str = Field(..., description="Simulation title")
    instructions: str = Field(..., description="How to interact with the simulation")
    parameters: dict = Field(default_factory=dict, description="Simulation parameters")


# ── Generic UI Block ─────────────────────────────────────────────────────────

class UIBlock(BaseModel):
    """A single UI block that Adeline generates."""
    block_id: str = Field(..., description="Unique block identifier")
    block_type: GenUIBlockType = Field(..., description="Type of interactive block")
    content: str = Field(..., description="Main text content (Markdown supported)")
    
    # Optional structured data for interactive blocks
    quiz_data: Optional[QuizData] = Field(None, description="Data for QUIZ blocks")
    flashcard_data: Optional[FlashcardData] = Field(None, description="Data for FLASHCARD blocks")
    timeline_data: Optional[TimelineData] = Field(None, description="Data for TIMELINE blocks")
    mind_map_data: Optional[MindMapData] = Field(None, description="Data for MIND_MAP blocks")
    mnemonic_data: Optional[MnemonicData] = Field(None, description="Data for MNEMONIC blocks")
    narrated_slide_data: Optional[NarratedSlideData] = Field(None, description="Data for NARRATED_SLIDE blocks")
    experiment_data: Optional[ExperimentData] = Field(None, description="Data for EXPERIMENT blocks")
    book_suggestion_data: Optional[BookSuggestionData] = Field(None, description="Data for BOOK_SUGGESTION blocks")
    interactive_sim_data: Optional[InteractiveSimData] = Field(None, description="Data for INTERACTIVE_SIM blocks")
    
    # Evidence and metadata
    is_silenced: bool = Field(False, description="Whether this block should be hidden")
    homestead_content: Optional[str] = Field(None, description="Homestead-adapted version")


# ── Complete Lesson Schema ───────────────────────────────────────────────────

class GenerativeLesson(BaseModel):
    """
    Complete lesson payload that Adeline generates.
    
    This is the top-level schema for structured LLM output.
    The frontend's GenUIRenderer consumes this directly.
    """
    lesson_id: str = Field(..., description="Unique lesson identifier")
    title: str = Field(..., description="Lesson title")
    track: str = Field(..., description="Learning track (e.g., TRUTH_HISTORY)")
    topic: str = Field(..., description="Lesson topic")
    
    # The interactive blocks
    ui_blocks: List[UIBlock] = Field(..., description="Ordered list of UI blocks")
    
    # Curriculum alignment
    oas_standards: List[str] = Field(default_factory=list, description="Oklahoma Academic Standards covered")
    
    # Metadata
    agent_name: str = Field("AdelineAgent", description="Which agent generated this lesson")
    credit_hours: float = Field(0.5, description="Credit hours for completion")
    researcher_activated: bool = Field(False, description="Whether external research was used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lesson_id": "lesson-abc123",
                "title": "The Underground Railroad",
                "track": "TRUTH_HISTORY",
                "topic": "How enslaved people escaped to freedom",
                "ui_blocks": [
                    {
                        "block_id": "block-1",
                        "block_type": "PRIMARY_SOURCE",
                        "content": "Frederick Douglass wrote in his autobiography...",
                        "is_silenced": False,
                    },
                    {
                        "block_id": "block-2",
                        "block_type": "QUIZ",
                        "content": "Test your understanding:",
                        "quiz_data": {
                            "question": "Who was Harriet Tubman?",
                            "options": [
                                {"text": "A conductor on the Underground Railroad", "is_correct": True},
                                {"text": "A plantation owner", "is_correct": False},
                            ],
                            "explanation": "Harriet Tubman made 13 missions to rescue enslaved people.",
                            "difficulty": "medium",
                        },
                        "is_silenced": False,
                    },
                ],
                "oas_standards": ["USH.5.1", "USH.5.2"],
                "agent_name": "HistorianAgent",
                "credit_hours": 0.5,
                "researcher_activated": False,
            }
        }


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_openai_json_schema() -> dict:
    """Get the JSON schema for OpenAI's response_format parameter."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "generative_lesson",
            "strict": True,
            "schema": GenerativeLesson.model_json_schema(),
        }
    }


def get_anthropic_tool_schema() -> dict:
    """Get the tool schema for Anthropic's tool use."""
    return {
        "name": "generate_lesson",
        "description": "Generate an interactive lesson with UI blocks",
        "input_schema": GenerativeLesson.model_json_schema(),
    }
