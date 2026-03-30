"""Grade-adaptive content configuration for the 8-Track curriculum.

Ported from cascade-adeline/src/lib/adaptive-content.ts
Pure computation — no DB calls.
"""
from __future__ import annotations
from typing import Literal

GradeBand = Literal["k2", "35", "68", "912"]

GRADE_CONFIGS: dict = {
    "k2":  {"difficulty": "EMERGING",   "attention_span_min": 15, "reading_level": "picture-books",      "interactive": "drag-drop"},
    "35":  {"difficulty": "DEVELOPING", "attention_span_min": 25, "reading_level": "early-reader",       "interactive": "typing"},
    "68":  {"difficulty": "EXPANDING",  "attention_span_min": 35, "reading_level": "independent-reader", "interactive": "coding"},
    "912": {"difficulty": "MASTERING",  "attention_span_min": 45, "reading_level": "young-adult",        "interactive": "research"},
}

TRACK_VOCABULARY: dict = {
    "TRUTH_HISTORY": {
        "k2":  ["past", "old", "story", "family", "time"],
        "35":  ["timeline", "evidence", "source", "community", "decade"],
        "68":  ["primary-source", "bias", "perspective", "chronology", "historical-analysis"],
        "912": ["historiography", "revisionism", "propaganda", "contextual-analysis", "source-criticism"],
    },
    "CREATION_SCIENCE": {
        "k2":  ["plants", "animals", "weather", "seasons", "God"],
        "35":  ["ecosystems", "matter", "energy", "life-cycles", "creation"],
        "68":  ["cells", "chemistry", "genetics", "designed-universe"],
        "912": ["biochemistry", "intelligent-design", "genetics", "research-methods"],
    },
    "HOMESTEADING": {
        "k2":  ["seeds", "soil", "grow", "water", "animals"],
        "35":  ["compost", "harvest", "seasons", "stewardship", "tools"],
        "68":  ["permaculture", "soil-biology", "fermentation", "preservation"],
        "912": ["regenerative-agriculture", "food-systems", "self-sufficiency", "land-management"],
    },
    "JUSTICE_CHANGEMAKING": {
        "k2":  ["fair", "share", "help", "kind", "community"],
        "35":  ["rights", "community", "change", "leaders", "history"],
        "68":  ["systemic", "advocacy", "power", "reform", "equity"],
        "912": ["structural-injustice", "policy", "regulatory-capture", "grassroots"],
    },
    "GOVERNMENT_ECONOMICS": {
        "k2":  ["rules", "money", "leaders", "vote", "share"],
        "35":  ["taxes", "budget", "government", "trade", "community"],
        "68":  ["economics", "legislation", "capitalism", "markets", "debt"],
        "912": ["monetary-policy", "constitutional-law", "regulatory-capture", "macroeconomics"],
    },
    "DISCIPLESHIP": {
        "k2":  ["God", "pray", "love", "truth", "kindness"],
        "35":  ["scripture", "faith", "discernment", "character", "worldview"],
        "68":  ["theology", "apologetics", "cultural-discernment", "biblical-worldview"],
        "912": ["philosophy", "epistemology", "apologetics", "systematic-theology"],
    },
    "HEALTH_NATUROPATHY": {
        "k2":  ["food", "sleep", "exercise", "clean", "body"],
        "35":  ["nutrition", "herbs", "exercise", "sleep", "natural-remedies"],
        "68":  ["naturopathy", "anatomy", "biochemistry", "holistic-health"],
        "912": ["naturopathic-medicine", "pharmacognosy", "systems-biology", "functional-medicine"],
    },
    "ENGLISH_LITERATURE": {
        "k2":  ["story", "character", "read", "write", "words"],
        "35":  ["plot", "setting", "dialogue", "narrator", "conflict"],
        "68":  ["protagonist", "metaphor", "theme", "foreshadowing", "literary-devices"],
        "912": ["archetype", "allegory", "rhetoric", "narrative-structure", "criticism"],
    },
}


def get_grade_band(grade_level: str) -> GradeBand:
    s = (grade_level or "").strip().upper()
    if s == "K":
        return "k2"
    try:
        g = int(s)
    except ValueError:
        return "35"
    if g <= 2: return "k2"
    if g <= 5: return "35"
    if g <= 8: return "68"
    return "912"


def get_difficulty_for_grade(grade_level: str) -> str:
    return GRADE_CONFIGS[get_grade_band(grade_level)]["difficulty"]


def get_attention_span_minutes(grade_level: str) -> int:
    return GRADE_CONFIGS[get_grade_band(grade_level)]["attention_span_min"]


def get_track_vocabulary(track: str, grade_level: str) -> list:
    return TRACK_VOCABULARY.get(track, {}).get(get_grade_band(grade_level), [])


def build_lesson_prompt_context(
    track: str,
    grade_level: str,
    topic: str,
    is_homestead: bool = False,
) -> dict:
    """Build grade-adaptive context dict for injection into agent prompts."""
    band = get_grade_band(grade_level)
    cfg  = GRADE_CONFIGS[band]
    return {
        "track":          track,
        "topic":          topic,
        "grade_level":    grade_level,
        "grade_band":     band,
        "difficulty":     cfg["difficulty"],
        "attention_span": cfg["attention_span_min"],
        "reading_level":  cfg["reading_level"],
        "vocabulary":     get_track_vocabulary(track, grade_level),
        "is_homestead":   is_homestead,
        "homestead_note": (
            "Default to homestead/farm-based applications. "
            "Use real activities on the working homestead, not hypothetical scenarios."
            if is_homestead else ""
        ),
    }
