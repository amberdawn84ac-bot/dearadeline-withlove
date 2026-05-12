"""
Learning Plan API — Dynamic personalized lesson suggestions.

Endpoints:
  GET /learning-plan/{student_id}  — Return personalized lesson suggestions based on:
    - Student profile (grade, interests, learning style, pacing)
    - ZPD candidates from Neo4j knowledge graph (concepts ready to learn)
    - Track progress and mastery levels (balance weak tracks)
    - Recent lessons completed (avoid repetition)
    - Cross-track connections (multi-disciplinary learning)
    - OAS Standards alignment (curriculum requirements)
    - Available projects from the portfolio catalog
    - Hippocampus corpus availability (what sources exist)
    - Credit requirements (what the student still needs)

The learning plan powers the dashboard's dynamic lesson cards.
This is the heart of Adeline's adaptive curriculum — connecting:
  - HistorianAgent (TRUTH_HISTORY, JUSTICE_CHANGEMAKING)
  - ScienceAgent (CREATION_SCIENCE, HOMESTEADING)
  - DiscipleshipAgent (all other tracks)
  - RegistrarAgent (credits, xAPI, transcript)
"""
import json
import logging
import random
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Header
from pydantic import BaseModel

from app.schemas.api_models import Track
from app.api.middleware import verify_student_access
from app.models.student import load_student_state, MasteryBand
from app.connections.journal_store import journal_store
from app.connections.neo4j_client import neo4j_client
from app.connections.pgvector_client import hippocampus
from app.connections.redis_client import redis_client
from app.tools.graph_query import tool_get_zpd_candidates, ZPDCandidate

# Graduation requirements (Oklahoma public school standards - 23 credits)
GRADUATION_REQUIREMENTS = {
    "ENGLISH_CORE": 4.0,      # Language Arts (English Literature)
    "MATH_CORE": 3.0,         # Math (Applied Mathematics, Algebra 1+)
    "SCIENCE_CORE": 3.0,      # Lab Science (Creation Science + Health Naturopathy + Physical Science + Biology)
    "SOCIAL_STUDIES": 3.0,    # Social Studies (Truth History + Oklahoma History + Government)
    "WORLD_LANGUAGE": 2.0,     # Technology or World Language (2 units same language)
    "PERSONAL_FINANCE": 0.5,   # Personal Financial Literacy (Creative Economics - business, pricing)
    "FINE_ARTS": 1.0,          # Art or Speech (Creative Economics - art projects, creative work)
    "ELECTIVES": 6.5,        # Additional electives (Homesteading + Discipleship + Justice Changemaking)
}
TOTAL_REQUIRED = sum(GRADUATION_REQUIREMENTS.values())  # 23.0 credits

# Map tracks to credit buckets
TRACK_TO_BUCKET = {
    "ENGLISH_LITERATURE": "ENGLISH_CORE",
    "APPLIED_MATHEMATICS": ["MATH_CORE", "PERSONAL_FINANCE"],  # Math + financial literacy
    "CREATION_SCIENCE": "SCIENCE_CORE",
    "HEALTH_NATUROPATHY": "SCIENCE_CORE",  # Health science + naturopathy
    "TRUTH_HISTORY": "SOCIAL_STUDIES",
    "GOVERNMENT_ECONOMICS": "SOCIAL_STUDIES",
    "CREATIVE_ECONOMY": "FINE_ARTS",  # Art projects, creative work, business
    "HOMESTEADING": "ELECTIVES",
    "DISCIPLESHIP": "ELECTIVES",
    "JUSTICE_CHANGEMAKING": "ELECTIVES",
    # Note: WORLD_LANGUAGE requirement can be met with Technology track or 2 units of same language
    # We'll map Technology requirements to existing tracks where applicable
}

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/learning-plan", tags=["learning-plan"])


# ── Response Models ──────────────────────────────────────────────────────────────────────────────

class LessonSuggestion(BaseModel):
    id: str
    title: str
    track: str
    description: str
    emoji: str
    priority: float
    source: str  # "zpd", "cross_track", "continue", "explore", "interest"
    concept_id: Optional[str] = None
    standard_code: Optional[str] = None
    grade_band: Optional[str] = None
    agent: Optional[str] = None  # Which agent will handle this: Historian, Science, Discipleship


class ProjectSuggestion(BaseModel):
    id: str
    title: str
    track: str
    tagline: str
    emoji: str
    difficulty: str
    estimated_hours: float
    portfolio_credit: bool = True  # Projects always earn portfolio credit


class BookRecommendation(BaseModel):
    id: str
    title: str
    author: str
    track: str
    lexile_level: int
    grade_band: Optional[str] = None
    cover_url: Optional[str] = None
    relevance_score: float = 0.0


class CreditGap(BaseModel):
    bucket: str
    required: float
    earned: float
    remaining: float
    priority: int  # 1=highest priority, 7=lowest

class GradeLevelStandard(BaseModel):
    standard_id: str
    subject: str
    grade: int
    description: str
    mastered: bool
    priority: int

class GraduationProgress(BaseModel):
    total_required: float
    total_earned: float
    percentage_complete: float
    credits_remaining: float
    on_track: bool  # Based on grade level and expected progress
    is_high_school: bool  # True for 9-12, False for K-8

class LearningPlanResponse(BaseModel):
    student_id: str
    suggestions: list[LessonSuggestion]
    projects: list[ProjectSuggestion]  # Portfolio projects ready to start
    recommended_books: list[BookRecommendation] = []
    total_tracks_active: int
    strongest_track: Optional[str] = None
    weakest_track: Optional[str] = None
    total_credits_earned: float = 0.0
    credits_this_week: float = 0.0
    graduation_progress: GraduationProgress
    credit_gaps: list[CreditGap]  # What's still needed for graduation (9-12 only)
    grade_standards: list[GradeLevelStandard]  # K-8 grade-level standards progress
    generated_at: str


# ── Track metadata ──────────────────────────────────────────────────────────────────────────────

# Which agent handles each track (from CLAUDE.md architecture)
TRACK_AGENT_MAP = {
    "TRUTH_HISTORY": "HistorianAgent",
    "JUSTICE_CHANGEMAKING": "HistorianAgent",
    "CREATION_SCIENCE": "ScienceAgent",
    "HOMESTEADING": "ScienceAgent",
    "DISCIPLESHIP": "DiscipleshipAgent",
    "HEALTH_NATUROPATHY": "DiscipleshipAgent",
    "GOVERNMENT_ECONOMICS": "DiscipleshipAgent",
    "ENGLISH_LITERATURE": "DiscipleshipAgent",
    "APPLIED_MATHEMATICS": "DiscipleshipAgent",
    "CREATIVE_ECONOMY": "DiscipleshipAgent",
}

TRACK_EMOJI = {
    "TRUTH_HISTORY": "🏗️",
    "CREATION_SCIENCE": "🔬",
    "HOMESTEADING": "🌾",
    "DISCIPLESHIP": "📖",
    "JUSTICE_CHANGEMAKING": "⚖️",
    "HEALTH_NATUROPATHY": "🌿",
    "GOVERNMENT_ECONOMICS": "🏦",
    "ENGLISH_LITERATURE": "📚",
    "APPLIED_MATHEMATICS": "📐",
    "CREATIVE_ECONOMY": "🎨",
}

TRACK_DESCRIPTIONS = {
    "TRUTH_HISTORY": "Primary sources from real history",
    "CREATION_SCIENCE": "Hands-on discovery and experiments",
    "HOMESTEADING": "Self-sufficiency and land skills",
    "DISCIPLESHIP": "Scripture study and spiritual growth",
    "JUSTICE_CHANGEMAKING": "Investigating injustice and taking action",
    "HEALTH_NATUROPATHY": "Natural health and body wisdom",
    "GOVERNMENT_ECONOMICS": "How power and money really work",
    "ENGLISH_LITERATURE": "Reading critically and writing boldly",
    "APPLIED_MATHEMATICS": "Math you'll actually use",
    "CREATIVE_ECONOMY": "Making and selling real things",
}

# Map student interests to tracks and topics (from onboarding)
INTEREST_TRACK_MAP = {
    "Gardening": ("HOMESTEADING", [
        ("Starting a Garden", "Planning and planting your first beds"),
        ("Companion Planting", "Which plants help each other grow"),
        ("Soil Health", "Building living soil for better harvests"),
    ]),
    "Chickens": ("HOMESTEADING", [
        ("Raising Chickens", "From chicks to eggs — the basics"),
        ("Chicken Health", "Keeping your flock healthy naturally"),
        ("Egg Production", "Maximizing eggs through the seasons"),
    ]),
    "Coding": ("APPLIED_MATHEMATICS", [
        ("Logic and Algorithms", "Thinking like a programmer"),
        ("Variables and Functions", "Building blocks of code"),
        ("Problem Solving", "Breaking big problems into small steps"),
    ]),
    "Science": ("CREATION_SCIENCE", [
        ("The Scientific Method", "How we discover truth through observation"),
        ("Ecosystems", "How living things depend on each other"),
        ("Weather Patterns", "Understanding the sky above us"),
    ]),
    "History": ("TRUTH_HISTORY", [
        ("Primary Sources", "Reading what people actually wrote"),
        ("Historical Context", "Understanding the world they lived in"),
        ("Cause and Effect", "How events connect across time"),
    ]),
    "Reading": ("ENGLISH_LITERATURE", [
        ("Close Reading", "Finding meaning in every word"),
        ("Author's Purpose", "Why did they write this?"),
        ("Literary Analysis", "Patterns and themes in stories"),
    ]),
    "Art": ("CREATIVE_ECONOMY", [
        ("Finding Your Style", "What makes your art yours?"),
        ("Art as Business", "Turning creativity into income"),
        ("Visual Storytelling", "Communicating through images"),
    ]),
    "Music": ("CREATIVE_ECONOMY", [
        ("Music Theory Basics", "The language of sound"),
        ("Songwriting", "Turning feelings into songs"),
        ("Performance", "Sharing your music with others"),
    ]),
    "Animals": ("CREATION_SCIENCE", [
        ("Animal Behavior", "Why animals do what they do"),
        ("Habitats", "Where creatures live and why"),
        ("Conservation", "Protecting wildlife for the future"),
    ]),
    "Cooking": ("HOMESTEADING", [
        ("Kitchen Chemistry", "The science of cooking"),
        ("Meal Planning", "Feeding a family on a budget"),
        ("Food Preservation", "Making food last longer"),
    ]),
    "Building": ("APPLIED_MATHEMATICS", [
        ("Measurement", "Precision in construction"),
        ("Geometry in Practice", "Angles, shapes, and structures"),
        ("Project Planning", "From blueprint to finished product"),
    ]),
    "Nature": ("CREATION_SCIENCE", [
        ("Field Observation", "Learning to see what's really there"),
        ("Plant Identification", "Knowing what grows around you"),
        ("Seasonal Cycles", "How nature changes through the year"),
    ]),
    "Writing": ("ENGLISH_LITERATURE", [
        ("Finding Your Voice", "Writing that sounds like you"),
        ("Persuasive Writing", "Making your case with words"),
        ("Storytelling", "Crafting narratives that captivate"),
    ]),
    "Business": ("CREATIVE_ECONOMY", [
        ("Entrepreneurship", "Starting something from nothing"),
        ("Marketing Basics", "Getting people to notice"),
        ("Financial Literacy", "Understanding money and value"),
    ]),
    "Faith": ("DISCIPLESHIP", [
        ("Scripture Study", "Going deeper into the Word"),
        ("Prayer Life", "Developing conversation with God"),
        ("Apologetics", "Knowing what you believe and why"),
    ]),
}

# Starter topics differentiated by grade band so every student sees age-appropriate content.
# Used as a fallback when the ZPD knowledge graph has no candidates yet (new students).
STARTER_TOPICS_BY_GRADE: dict[str, dict[str, list[tuple[str, str]]]] = {
    "K-2": {
        "TRUTH_HISTORY": [
            ("My Family's Story", "Interviewing grandparents to record your family's history"),
            ("Community Helpers Then and Now", "How towns and neighborhoods have changed"),
            ("Holidays and Their Meaning", "Why we celebrate and what history is behind each one"),
        ],
        "CREATION_SCIENCE": [
            ("Butterfly Life Cycles", "Watching caterpillars turn into butterflies — step by step"),
            ("Seeds and Growing Things", "Planting seeds and recording what you observe"),
            ("Weather Watch", "Keeping a daily weather journal for one month"),
        ],
        "HOMESTEADING": [
            ("Garden Helpers", "Learning which bugs help the garden and which don't"),
            ("Where Food Comes From", "Tracing your meals back to the farm"),
            ("Baby Animals on the Farm", "How animals are born, fed, and cared for"),
        ],
        "DISCIPLESHIP": [
            ("The Lord's Prayer", "Learning each line and what it means"),
            ("Creation Week", "What God made on each of the seven days"),
            ("Fruit of the Spirit", "What love, joy, peace, and patience look like in real life"),
        ],
        "JUSTICE_CHANGEMAKING": [
            ("Fair and Unfair", "Recognizing when rules help everyone — or only some people"),
            ("Community Problem Solvers", "People who helped make their neighborhood better"),
            ("My Voice Matters", "Learning to speak up kindly for what is right"),
        ],
        "HEALTH_NATUROPATHY": [
            ("How My Body Works", "Learning about bones, muscles, and the heart"),
            ("Foods That Help Us Grow", "Which foods give us energy, strength, and clear thinking"),
            ("Rest and Movement", "Why we need sleep and why we need to play outside"),
        ],
        "GOVERNMENT_ECONOMICS": [
            ("Needs vs. Wants", "Understanding why we cannot have everything at once"),
            ("Earning and Spending", "Setting up a simple lemonade stand and counting the money"),
            ("Leaders in Our Community", "Who makes decisions in our town — and how"),
        ],
        "ENGLISH_LITERATURE": [
            ("My Favorite Story", "Retelling a book in your own words"),
            ("Rhymes and Reasons", "Poetry is just talking with a beat"),
            ("Letter Writing", "Writing a real letter to someone you love"),
        ],
        "APPLIED_MATHEMATICS": [
            ("Counting Money", "Using real coins and dollars to buy and make change"),
            ("Measuring with Rulers", "Hands-on measurement in the kitchen and garden"),
            ("Patterns Everywhere", "Spotting patterns in nature, fabric, and buildings"),
        ],
        "CREATIVE_ECONOMY": [
            ("My First Art Show", "Making artwork and sharing it with the family"),
            ("Simple Crafts to Sell", "Making something by hand and deciding on a fair price"),
            ("Telling Stories with Pictures", "Drawing a comic strip about your day"),
        ],
    },
    "3-5": {
        "TRUTH_HISTORY": [
            ("The Declaration of Independence", "What the founders wrote — and what they meant"),
            ("The Trail of Tears", "Primary sources from those who survived forced removal"),
            ("The American Revolution", "Letters from colonists and loyalists — two different stories"),
        ],
        "CREATION_SCIENCE": [
            ("The Water Cycle", "Hands-on experiments with evaporation, clouds, and rain"),
            ("Ecosystems in Your Backyard", "What lives in the soil, air, and plants right outside"),
            ("Animal Adaptations", "How creatures are designed to thrive in their environment"),
        ],
        "HOMESTEADING": [
            ("Starting a Garden", "Planning beds, choosing varieties, and reading a seed packet"),
            ("Composting Basics", "Turning kitchen scraps into rich garden soil"),
            ("Raising Chickens", "From chicks to eggs — flock health and daily care"),
        ],
        "DISCIPLESHIP": [
            ("The Psalms", "Hebrew poetry and what the words meant in their original context"),
            ("The Sermon on the Mount", "What Jesus taught — and what the crowd would have heard"),
            ("God's Design in Creation", "Seeing the Creator's fingerprints in living things"),
        ],
        "JUSTICE_CHANGEMAKING": [
            ("Children Who Changed History", "Young activists and the lasting impact they made"),
            ("Media Literacy Basics", "Is everything you read online really true?"),
            ("Environmental Stewardship", "Taking care of the land and water God entrusted to us"),
        ],
        "HEALTH_NATUROPATHY": [
            ("Herbal Garden Basics", "Growing and using plants that support everyday health"),
            ("The Immune System", "How your body fights off sickness — without drugs"),
            ("Sleep, Stress, and Health", "Why rest is one of the most powerful medicines"),
        ],
        "GOVERNMENT_ECONOMICS": [
            ("How Local Government Works", "City council, mayors, and where your family has a voice"),
            ("Supply and Demand", "Why some things cost more than others — and who decides"),
            ("Making a Budget", "Dividing money into needs, wants, and savings"),
        ],
        "ENGLISH_LITERATURE": [
            ("Reading Critically", "What is the author asking you to believe?"),
            ("Narrative Voice", "Who is telling the story — and why does it matter?"),
            ("Persuasive Writing", "Making an argument and backing it up with evidence"),
        ],
        "APPLIED_MATHEMATICS": [
            ("Fractions in Real Life", "Cooking, building, and dividing things up fairly"),
            ("Measuring and Building", "Using math to plan and build a real project"),
            ("Budgeting a Project", "Adding up costs before you spend — and adjusting when needed"),
        ],
        "CREATIVE_ECONOMY": [
            ("Pricing Your Work", "What is your time, skill, and materials worth?"),
            ("Making and Selling", "From idea to finished product — and making a profit"),
            ("Design Thinking", "How to solve real problems with creativity"),
        ],
    },
    "6-8": {
        "TRUTH_HISTORY": [
            ("Primary Sources Workshop", "Evaluating documents for bias, context, and reliability"),
            ("The Civil War in Letters", "What soldiers and civilians actually wrote home about"),
            ("Constitutional Amendments", "How and why the founding document has changed over time"),
        ],
        "CREATION_SCIENCE": [
            ("Scientific Method in Action", "Designing and running your own controlled experiment"),
            ("Genetics and Heredity", "Why living things look like their parents — and sometimes don't"),
            ("Earth's Systems", "How geology, the water cycle, and the atmosphere interact"),
        ],
        "HOMESTEADING": [
            ("Soil Science", "Testing and amending your soil for a better harvest"),
            ("Food Preservation", "Canning, fermenting, and dehydrating the harvest"),
            ("Small-Scale Animal Husbandry", "Managing a flock or small herd sustainably"),
        ],
        "DISCIPLESHIP": [
            ("Apologetics Foundations", "Knowing what you believe — and being able to explain why"),
            ("Biblical Worldview", "How Scripture speaks to every area of modern life"),
            ("Church History", "How the faith was tested, preserved, and passed down"),
        ],
        "JUSTICE_CHANGEMAKING": [
            ("Regulatory Capture Explained", "How corporations influence the laws that govern them"),
            ("Civil Rights Documentation", "Reading primary sources from the movement — not the textbook"),
            ("Local Advocacy Project", "Identifying a real problem and taking documented action"),
        ],
        "HEALTH_NATUROPATHY": [
            ("Nutrition Science", "What the food industry funds — and what the research actually shows"),
            ("Herbal Medicine Research", "Evaluating traditional plant remedies with modern evidence"),
            ("Mental Health and Faith", "Anxiety, depression, and a biblical framework for care"),
        ],
        "GOVERNMENT_ECONOMICS": [
            ("How Laws Really Get Made", "Lobbying, campaign money, and the legislative process"),
            ("The Federal Reserve", "Who controls the money supply — and what that means for you"),
            ("Economics of the Household", "Running your family's finances like a business"),
        ],
        "ENGLISH_LITERATURE": [
            ("Literary Analysis", "Finding theme, symbolism, and authorial intent in a real text"),
            ("Research and Citation", "Building an argument from primary sources"),
            ("Rhetoric and Persuasion", "How language is used to shape what people believe"),
        ],
        "APPLIED_MATHEMATICS": [
            ("Algebra in Real Life", "Using equations to solve actual problems around the house"),
            ("Geometry and Design", "Angles, measurements, and building a real structure"),
            ("Statistics and Data", "Reading graphs, polls, and probability with a critical eye"),
        ],
        "CREATIVE_ECONOMY": [
            ("Building a Brand", "What makes a business stand out — and why people trust it"),
            ("Portfolio Development", "Documenting your creative work professionally"),
            ("Entrepreneurship Basics", "Starting something from nothing — the first steps"),
        ],
    },
    "9-12": {
        "TRUTH_HISTORY": [
            ("The Declaration — A Close Read", "Annotating the founding document line by line"),
            ("Reconstruction and Its Collapse", "What primary sources reveal about post-war America"),
            ("20th Century Foreign Policy", "Declassified documents and geopolitical strategy"),
        ],
        "CREATION_SCIENCE": [
            ("Origins Debate", "Evaluating evolutionary and creation science arguments from primary literature"),
            ("Advanced Biology", "Cell biology, genetics, and biochemistry for the serious student"),
            ("Environmental Chemistry", "How pollutants move through ecosystems — and who regulates them"),
        ],
        "HOMESTEADING": [
            ("Farm Business Planning", "From acreage to income — building a sustainable homestead"),
            ("Advanced Food Preservation", "Fermentation science, lacto-fermentation, and shelf-life chemistry"),
            ("Permaculture Design", "Designing land for maximum yield and long-term sustainability"),
        ],
        "DISCIPLESHIP": [
            ("Systematic Theology", "Core doctrines and their biblical foundations — in your own words"),
            ("Cultural Apologetics", "Engaging the secular world with grace, truth, and evidence"),
            ("Vocational Calling", "How faith shapes career, family, and life purpose"),
        ],
        "JUSTICE_CHANGEMAKING": [
            ("Power-Capture Tactics", "Regulatory, legislative, and narrative capture — and how changemakers respond"),
            ("Investigative Research Methods", "FOIA requests, lobbying records, and follow-the-money analysis"),
            ("Changemaker Portfolio", "Documenting actions taken, not essays written — for a real audience"),
        ],
        "HEALTH_NATUROPATHY": [
            ("Clinical Nutrition", "Evidence-based natural health — reading the actual studies"),
            ("Functional Medicine Overview", "Root causes vs. symptom management — a framework for health"),
            ("Community Health Advocacy", "Applying health knowledge to serve and educate others"),
        ],
        "GOVERNMENT_ECONOMICS": [
            ("Austrian Economics", "Sound money, free markets, and individual liberty — the theoretical foundation"),
            ("Constitutional Law", "How the courts have interpreted — and sometimes ignored — the founding document"),
            ("Entrepreneurship and the Market", "Building a business within a real economic framework"),
        ],
        "ENGLISH_LITERATURE": [
            ("Advanced Rhetoric", "The art of persuasion from Aristotle to modern political speech"),
            ("American Literature Survey", "Primary texts from the founding era to the 20th century"),
            ("Senior Thesis Writing", "Research, argument structure, and academic writing for publication"),
        ],
        "APPLIED_MATHEMATICS": [
            ("Pre-Calculus Concepts", "Functions, limits, and the language of higher mathematics"),
            ("Financial Mathematics", "Interest, compound growth, investment, and real-world money management"),
            ("Statistics for Research", "Using data to answer real questions — and spotting manipulation"),
        ],
        "CREATIVE_ECONOMY": [
            ("Business Plan Development", "Turning a creative idea into a viable enterprise — with numbers"),
            ("Visual Communication", "Design principles for marketing, branding, and public communication"),
            ("Creative Portfolio for College", "Documenting work for admissions, employment, or clients"),
        ],
    },
}


def _get_grade_band(grade_level: str) -> str:
    """Return the grade band string for a given grade level."""
    if grade_level == "K" or grade_level.upper().startswith("K"):
        grade_num = 0
    else:
        import re
        match = re.match(r"(\d+)", grade_level)
        grade_num = int(match.group(1)) if match else 5
    if grade_num <= 2:
        return "K-2"
    elif grade_num <= 5:
        return "3-5"
    elif grade_num <= 8:
        return "6-8"
    return "9-12"


def _get_grade_appropriate_starters(track: str, grade_level: str) -> list[tuple[str, str]]:
    """Return grade-band-filtered starter topics for a track."""
    band = _get_grade_band(grade_level)
    return STARTER_TOPICS_BY_GRADE.get(band, {}).get(track, [])


def _zpd_to_suggestion(candidate: ZPDCandidate, priority_boost: float = 0.0) -> LessonSuggestion:
    """
    Convert a ZPD candidate to a lesson suggestion.

    Uses the candidate's compute_priority() score (prereq_readiness × mastery_gap × leverage)
    when available (BKT-aware path). Falls back to 0.7 for graph-only candidates.
    Priority is clamped to [0, 1].
    """
    # BKT-aware path: candidate.priority is from compute_priority() in zpd_engine.py
    # Graph-only fallback: candidate.priority defaults to 0.5
    base_priority = candidate.priority if candidate.priority > 0 else 0.7
    final_priority = min(1.0, base_priority + priority_boost)

    return LessonSuggestion(
        id=f"zpd-{candidate.concept_id}",
        title=candidate.title,
        track=candidate.track,
        description=candidate.description or TRACK_DESCRIPTIONS.get(candidate.track, ""),
        emoji=TRACK_EMOJI.get(candidate.track, "📚"),
        priority=final_priority,
        source="zpd",
        concept_id=candidate.concept_id,
        standard_code=candidate.standard_code,
        grade_band=candidate.grade_band,
        agent=TRACK_AGENT_MAP.get(candidate.track),
    )


def _interest_suggestion(interest: str, topic: tuple[str, str], track: str, idx: int) -> LessonSuggestion:
    """Create a suggestion based on student interests from onboarding."""
    title, description = topic
    return LessonSuggestion(
        id=f"interest-{interest.lower()}-{idx}",
        title=title,
        track=track,
        description=description,
        emoji=TRACK_EMOJI.get(track, "📚"),
        priority=0.85 - (idx * 0.02),  # High priority for interest-based
        source="interest",
        agent=TRACK_AGENT_MAP.get(track),
    )


def _starter_suggestion(track: str, topic: tuple[str, str], idx: int) -> LessonSuggestion:
    """Create a starter suggestion for a track with no ZPD data."""
    title, description = topic
    return LessonSuggestion(
        id=f"starter-{track.lower()}-{idx}",
        title=title,
        track=track,
        description=description,
        emoji=TRACK_EMOJI.get(track, "📚"),
        priority=0.5 - (idx * 0.05),  # Decrease priority for later suggestions
        source="explore",
        agent=TRACK_AGENT_MAP.get(track),
    )


async def _get_student_profile(student_id: str) -> dict:
    """Fetch student profile including interests, grade level, learning style."""
    from app.config import get_db_conn
    try:
        conn = await get_db_conn()
        row = await conn.fetchrow(
            """
            SELECT "name", "gradeLevel", "interests", "learningStyle", "pacingMultiplier", "state"
            FROM "User"
            WHERE "id" = $1
            """,
            student_id,
        )
        await conn.close()
        if row:
            interests = list(row["interests"]) if row["interests"] else []
            return {
                "name": row["name"],
                "grade_level": row["gradeLevel"],
                "interests": interests,
                "learning_style": row["learningStyle"],
                "pacing_multiplier": row["pacingMultiplier"] or 1.0,
                "state": row["state"],
            }
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to fetch student profile: {e}")
    return {"interests": [], "grade_level": "8", "learning_style": "EXPEDITION"}


async def _get_credit_summary(student_id: str) -> tuple[float, float]:
    """Get total credits earned and credits this week."""
    from app.config import get_db_conn
    from datetime import timedelta
    try:
        conn = await get_db_conn()
        # Total credits
        total = await conn.fetchval(
            'SELECT COALESCE(SUM("creditHours"), 0) FROM "TranscriptEntry" WHERE "studentId" = $1',
            student_id,
        )
        # Credits this week
        from datetime import datetime as _dt
        week_ago = _dt.utcnow() - timedelta(days=7)  # naive UTC — matches DB TIMESTAMP
        weekly = await conn.fetchval(
            'SELECT COALESCE(SUM("creditHours"), 0) FROM "TranscriptEntry" WHERE "studentId" = $1 AND "completedAt" >= $2',
            student_id, week_ago,
        )
        await conn.close()
        return float(total or 0), float(weekly or 0)
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to fetch credit summary: {e}")
    return 0.0, 0.0


async def _get_credits_by_bucket(student_id: str) -> dict[str, float]:
    """Get earned credits grouped by graduation bucket."""
    from app.config import get_db_conn
    credits_by_bucket = {bucket: 0.0 for bucket in GRADUATION_REQUIREMENTS}
    
    try:
        conn = await get_db_conn()
        rows = await conn.fetch(
            """
            SELECT track, SUM("creditHours") as hours
            FROM "TranscriptEntry" 
            WHERE "studentId" = $1
            GROUP BY track
            """,
            student_id,
        )
        await conn.close()
        
        for row in rows:
            track = row["track"]
            hours = float(row["hours"] or 0)
            bucket = TRACK_TO_BUCKET.get(track)
            if bucket:
                if isinstance(bucket, list):
                    # Track maps to multiple buckets - count toward ALL of them
                    for b in bucket:
                        credits_by_bucket[b] += hours
                else:
                    credits_by_bucket[bucket] += hours
                
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get credits by bucket: {e}")
        
    return credits_by_bucket


def _calculate_credit_gaps(credits_by_bucket: dict[str, float], grade_level: str) -> list[CreditGap]:
    """Calculate what credits are still needed for graduation with grade-level priorities."""
    gaps = []
    
    # Parse grade level
    if grade_level == "K":
        grade_num = 0
    elif grade_level.startswith("K"):
        grade_num = 0
    else:
        import re
        match = re.match(r'(\d+)', grade_level)
        grade_num = int(match.group(1)) if match else 0
    
    # Different priority orders for K-8 vs 9-12
    if grade_num <= 8:  # K-8: Foundational skills first
        priority_order = [
            "ENGLISH_CORE",      # Reading/writing fundamentals
            "MATH_CORE",         # Math fundamentals
            "SCIENCE_CORE",      # Science exploration
            "SOCIAL_STUDIES",    # History/civics basics
            "PERSONAL_FINANCE",  # Health/financial literacy basics
            "FINE_ARTS",         # Creativity and arts
            "WORLD_LANGUAGE",    # Technology/second language exposure
            "ELECTIVES"          # Interest-based learning
        ]
    else:  # 9-12: Credit accumulation for graduation (Oklahoma standards)
        priority_order = [
            "ENGLISH_CORE",      # 4 credits required
            "MATH_CORE",         # 3 credits required (Algebra 1+)
            "SCIENCE_CORE",      # 3 credits required (Physical Science + Biology + above)
            "SOCIAL_STUDIES",    # 3 credits required (US History + OK History + Government)
            "WORLD_LANGUAGE",    # 2 credits required (Technology or language)
            "PERSONAL_FINANCE",  # 0.5 credits required
            "FINE_ARTS",         # 1 credit required
            "ELECTIVES"          # 6.5 credits required
        ]
    
    for i, bucket in enumerate(priority_order, 1):
        required = GRADUATION_REQUIREMENTS[bucket]
        earned = credits_by_bucket.get(bucket, 0.0)
        remaining = max(0.0, required - earned)
        
        gaps.append(CreditGap(
            bucket=bucket,
            required=required,
            earned=earned,
            remaining=remaining,
            priority=i,
        ))
    
    return gaps


def _calculate_graduation_progress(credits_by_bucket: dict[str, float], grade_level: str) -> GraduationProgress:
    """Calculate overall graduation progress with grade-level specific expectations."""
    total_earned = sum(credits_by_bucket.values())
    percentage = (total_earned / TOTAL_REQUIRED) * 100 if TOTAL_REQUIRED > 0 else 0
    remaining = max(0.0, TOTAL_REQUIRED - total_earned)
    
    # Parse grade level to numeric
    if grade_level == "K":
        grade_num = 0
    elif grade_level.startswith("K"):
        grade_num = 0
    else:
        # Extract number from grade (e.g., "1st" -> 1, "11th" -> 11)
        import re
        match = re.match(r'(\d+)', grade_level)
        grade_num = int(match.group(1)) if match else 0
    
    # Grade-level specific expectations
    on_track = False
    expected_credits = 0.0
    
    if grade_num <= 8:  # K-8: No credit accumulation, focus on foundational skills
        # K-8 doesn't accumulate credits toward graduation
        # They should be building foundational knowledge across all subjects
        on_track = True  # All K-8 students are "on track" by default
        expected_credits = 0.0
    else:  # 9-12: Credit accumulation toward graduation
        # High school students should earn ~6 credits per year
        years_completed = grade_num - 8  # 9th grade = 1 year of high school
        expected_credits = min(years_completed * 6.0, TOTAL_REQUIRED)
        on_track = total_earned >= expected_credits * 0.8  # 80% of expected progress
    
    return GraduationProgress(
        total_required=TOTAL_REQUIRED,
        total_earned=total_earned,
        percentage_complete=round(percentage, 1),
        credits_remaining=round(remaining, 1),
        on_track=on_track,
        is_high_school=grade_num >= 9,
    )


async def _get_grade_level_standards(student_id: str, grade_level: str) -> list[GradeLevelStandard]:
    """Fetch live OAS standards from Neo4j for this grade, with per-standard mastery status."""
    import re

    if grade_level == "K" or grade_level.startswith("K"):
        grade_num = 0
    else:
        m = re.match(r"(\d+)", grade_level)
        grade_num = int(m.group(1)) if m else 0

    # Standards only tracked for K-8
    if grade_num > 8:
        return []

    try:
        rows = await neo4j_client.run(
            """
            MATCH (s:OASStandard)
            WHERE s.grade = $grade
            OPTIONAL MATCH (st:Student {id: $student_id})-[:MASTERED]->(c:Concept)
                           -[:MAPS_TO_STANDARD]->(s)
            WITH s, count(c) > 0 AS mastered
            RETURN s.id            AS id,
                   s.standard_text AS description,
                   s.grade         AS grade,
                   coalesce(s.subject, 'General') AS subject,
                   mastered
            ORDER BY s.id
            LIMIT 10
            """,
            {"grade": grade_num, "student_id": student_id},
        )
        return [
            GradeLevelStandard(
                standard_id=r["id"],
                subject=r["subject"] or "General",
                grade=int(r["grade"] or grade_num),
                description=r["description"] or "",
                mastered=bool(r["mastered"]),
                priority=i + 1,
            )
            for i, r in enumerate(rows)
        ]
    except Exception as e:
        logger.warning(f"[LearningPlan] Neo4j grade standards query failed: {e}")
        return []


async def _get_available_projects(track: str = None, limit: int = 3) -> list[ProjectSuggestion]:
    """Get available projects from the catalog, optionally filtered by track."""
    from app.api.projects import PROJECTS
    
    projects = []
    for proj in PROJECTS.values():
        if track and proj.track.value != track:
            continue
        projects.append(ProjectSuggestion(
            id=proj.id,
            title=proj.title,
            track=proj.track.value,
            tagline=proj.tagline,
            emoji=TRACK_EMOJI.get(proj.track.value, "🎨"),
            difficulty=str(proj.difficulty.value) if hasattr(proj.difficulty, 'value') else str(proj.difficulty),
            estimated_hours=proj.estimated_hours,
            portfolio_credit=True,
        ))
        if len(projects) >= limit:
            break
    return projects


# ── Redis sliding-window helpers ───────────────────────────────────────────────────────────────────────

def _plan_cache_key(student_id: str) -> str:
    return f"learning_plan:{student_id}"


async def pop_completed_lesson(student_id: str, lesson_title: str) -> None:
    """
    Remove a completed lesson from the Redis queue by title.
    Called synchronously before the background replenishment fires.
    """
    cache_key = _plan_cache_key(student_id)
    try:
        raw = await redis_client.get(cache_key)
        if not raw:
            return
        plan = json.loads(raw)
        original_count = len(plan.get("suggestions", []))
        plan["suggestions"] = [
            s for s in plan.get("suggestions", [])
            if s.get("title") != lesson_title
        ]
        if len(plan["suggestions"]) < original_count:
            await redis_client.set(cache_key, json.dumps(plan), ex=3600)
            logger.info(
                f"[LearningPlan] Popped '{lesson_title}' from queue for student={student_id}. "
                f"Queue: {original_count} → {len(plan['suggestions'])}"
            )
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to pop completed lesson (non-fatal): {e}")


async def _replenish_learning_plan_queue(student_id: str) -> None:
    """
    Background task: read credit gaps, generate 1-2 targeted new suggestions,
    and append them to the Redis queue so the dashboard always has fresh cards.
    """
    cache_key = _plan_cache_key(student_id)
    try:
        # 1. Load current queue
        raw = await redis_client.get(cache_key)
        plan = json.loads(raw) if raw else {}
        current_suggestions: list[dict] = plan.get("suggestions", [])
        current_titles = {s.get("title") for s in current_suggestions}

        # 2. Load what's needed to generate a gap-targeted suggestion
        profile = {}
        try:
            profile = await _get_student_profile(student_id)
        except Exception:
            pass
        grade_level = profile.get("grade_level", "8")

        credits_by_bucket = await _get_credits_by_bucket(student_id)
        credit_gaps = _calculate_credit_gaps(credits_by_bucket, grade_level)

        student_state = None
        try:
            student_state = await load_student_state(student_id)
        except Exception:
            pass

        track_scores: dict[str, float] = {}
        if student_state and student_state.tracks:
            for track_name, mastery in student_state.tracks.items():
                track_scores[track_name] = mastery.mastery_score

        weakest_track = min(track_scores, key=track_scores.get) if track_scores else None

        # 3. Build up to 2 new suggestions, prioritised by graduation gaps
        new_suggestions: list[LessonSuggestion] = []

        # Priority 1: ZPD candidates in the highest-priority gap track
        for gap in sorted(credit_gaps, key=lambda g: g.priority):
            if gap.remaining <= 0:
                continue
            for track, bucket in TRACK_TO_BUCKET.items():
                effective_bucket = bucket[0] if isinstance(bucket, list) else bucket
                if effective_bucket != gap.bucket:
                    continue
                try:
                    candidates = await tool_get_zpd_candidates(student_id, track, limit=2)
                    for c in candidates:
                        s = _zpd_to_suggestion(c, priority_boost=0.3)
                        if s.title not in current_titles:
                            new_suggestions.append(s)
                            current_titles.add(s.title)
                        if len(new_suggestions) >= 2:
                            break
                except Exception:
                    pass
            if len(new_suggestions) >= 2:
                break

        # Priority 2: Grade-appropriate starter for the weakest track if still short
        if len(new_suggestions) < 2 and weakest_track:
            starters = _get_grade_appropriate_starters(weakest_track, grade_level)
            for idx, topic in enumerate(starters):
                s = _starter_suggestion(weakest_track, topic, idx)
                if s.title not in current_titles:
                    new_suggestions.append(s)
                    current_titles.add(s.title)
                if len(new_suggestions) >= 2:
                    break

        if not new_suggestions:
            logger.info(f"[LearningPlan/Replenish] No new suggestions generated for student={student_id}")
            return

        # 4. Append and write back to Redis (1-hour TTL keeps queue fresh)
        for s in new_suggestions:
            current_suggestions.append(s.model_dump())
        plan["suggestions"] = current_suggestions
        plan["generated_at"] = datetime.now(timezone.utc).isoformat()
        await redis_client.set(cache_key, json.dumps(plan), ex=3600)
        logger.info(
            f"[LearningPlan/Replenish] Appended {len(new_suggestions)} new suggestion(s) "
            f"for student={student_id}. Queue now has {len(current_suggestions)} items."
        )
    except Exception as e:
        logger.warning(f"[LearningPlan/Replenish] Background replenishment failed (non-fatal): {e}")


@router.get("/{student_id}", response_model=LearningPlanResponse)
async def get_learning_plan(
    student_id: str,
    limit: int = Query(6, ge=1, le=12),
    include_all_tracks: bool = Query(False),
    refresh: bool = Query(False, description="Force regeneration, bypassing cache"),
    _user_id: str = Depends(verify_student_access),
):
    """
    Generate a personalized learning plan with dynamic lesson suggestions.

    This is the heart of Adeline's adaptive curriculum, integrating:
    - Student profile (interests, grade level, learning style)
    - ZPD Engine (concepts ready to learn based on prerequisites)
    - Track mastery (balance progress across all 10 tracks)
    - Portfolio projects (real-world accomplishments, not assignments)
    - Registrar credits (what the student has earned, what they still need)
    - Agent routing (HistorianAgent, ScienceAgent, DiscipleshipAgent)

    Caching:
    - Learning plans are cached in Redis for 5 minutes to avoid expensive
      regeneration on every dashboard load.
    - Pass ?refresh=true to force regeneration.

    The algorithm:
    1. Load student profile (interests, grade, learning style)
    2. Load student state (track mastery, lesson counts)
    3. Get credit summary (total earned, this week)
    4. Generate interest-based suggestions (highest priority for engagement)
    5. Fetch ZPD candidates from the knowledge graph
    6. Add starter topics for tracks with no ZPD data
    7. Fetch available portfolio projects
    8. Rank and return balanced suggestions across tracks

    Priority factors:
    - Interest-based topics → highest (student engagement)
    - ZPD candidates (ready to learn, prerequisites met) → high
    - Tracks with lower mastery → boosted (help balance progress)
    - Starter/exploration topics → lower priority
    """
    # ── Redis sliding-window cache check ─────────────────────────────────────────────────────────────────────
    cache_key = _plan_cache_key(student_id)
    if not refresh:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"[LearningPlan] Cache HIT for student={student_id}")
                return LearningPlanResponse(**json.loads(cached))
        except Exception as e:
            logger.warning(f"[LearningPlan] Redis cache read failed (non-fatal): {e}")

    suggestions: list[LessonSuggestion] = []

    # 1. Load student profile (interests, grade, learning style)
    try:
        profile = await _get_student_profile(student_id)
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get student profile: {e}")
        profile = {}
    interests = profile.get("interests", [])
    grade_level = profile.get("grade_level", "8")
    learning_style = profile.get("learning_style", "EXPEDITION")
    
    logger.info(
        f"[LearningPlan] Generating plan for student={student_id}, "
        f"grade={grade_level}, interests={interests}, style={learning_style}"
    )

    # 2. Load student state (track mastery, lesson counts)
    try:
        student_state = await load_student_state(student_id)
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to load student state: {e}")
        student_state = None

    # 3. Get credit summary and graduation progress
    try:
        total_credits, weekly_credits = await _get_credit_summary(student_id)
        credits_by_bucket = await _get_credits_by_bucket(student_id)
        graduation_progress = _calculate_graduation_progress(credits_by_bucket, grade_level)
        credit_gaps = _calculate_credit_gaps(credits_by_bucket, grade_level)
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get graduation data: {e}")
        total_credits, weekly_credits = 0.0, 0.0
        credits_by_bucket = {bucket: 0.0 for bucket in GRADUATION_REQUIREMENTS}
        graduation_progress = GraduationProgress(
            total_required=TOTAL_REQUIRED,
            total_earned=0.0,
            percentage_complete=0.0,
            credits_remaining=TOTAL_REQUIRED,
            on_track=False,
            is_high_school=False,
        )
        credit_gaps = _calculate_credit_gaps(credits_by_bucket, grade_level)

    # 4. Get recent lessons to avoid repetition
    recent_lesson_ids: set[str] = set()
    try:
        recent = await journal_store.get_recent(student_id, limit=20)
        recent_lesson_ids = {r["lesson_id"] for r in recent}
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get recent lessons: {e}")

    # 5. Determine which tracks to include
    all_tracks = list(Track)
    active_tracks: list[str] = []
    track_scores: dict[str, float] = {}

    if student_state and student_state.tracks:
        for track_name, mastery in student_state.tracks.items():
            active_tracks.append(track_name)
            track_scores[track_name] = mastery.mastery_score
    
    # If no active tracks or include_all_tracks, use all tracks
    if not active_tracks or include_all_tracks:
        active_tracks = [t.value for t in all_tracks]

    # Find strongest and weakest tracks
    strongest_track = None
    weakest_track = None
    if track_scores:
        strongest_track = max(track_scores, key=track_scores.get)
        weakest_track = min(track_scores, key=track_scores.get)

    # 6. PRIORITIZE BASED ON CREDIT GAPS (graduation requirements first)
    # Map gaps to tracks and prioritize suggestions for missing credits
    gap_priorities = {}
    for gap in credit_gaps:
        if gap.remaining > 0:
            # Find tracks that fulfill this bucket (bucket may be a string or a list)
            for track, bucket in TRACK_TO_BUCKET.items():
                bucket_matches = (
                    bucket == gap.bucket
                    if isinstance(bucket, str)
                    else gap.bucket in bucket
                )
                if bucket_matches and track in active_tracks:
                    gap_priorities[track] = gap.priority
                    break
    
    # 7. Generate gap-based suggestions (highest priority)
    for track in sorted(gap_priorities.keys(), key=lambda t: gap_priorities[t]):
        # Boost priority significantly for missing credits
        priority_boost = (1.0 - track_scores.get(track, 0.0)) * 0.2  # Up to 0.2 boost
        
        try:
            candidates = await tool_get_zpd_candidates(student_id, track, limit=2)
            
            for candidate in candidates:
                suggestion = _zpd_to_suggestion(candidate, priority_boost + 0.3)  # Extra boost for gaps
                # Don't add duplicates
                if not any(s.title == suggestion.title for s in suggestions):
                    suggestions.append(suggestion)
                    
            # If no ZPD candidates, use a grade-appropriate starter for this gap track
            if not candidates:
                grade_starters = _get_grade_appropriate_starters(track, grade_level)
                for topic in grade_starters[:1]:
                    suggestion = _starter_suggestion(track, topic, 0)
                    suggestion.priority = 0.8  # High priority for gaps
                    if not any(s.title == suggestion.title for s in suggestions):
                        suggestions.append(suggestion)

        except Exception as e:
            logger.warning(f"[LearningPlan] Gap-based suggestions failed for track={track}: {e}")

    # 8. Generate interest-based suggestions (high priority — student engagement drives completion)
    # Interests surface early so every student sees personalized cards, even without ZPD graph data.
    for interest in interests[:3]:  # Top 3 interests
        if interest in INTEREST_TRACK_MAP:
            track, topics = INTEREST_TRACK_MAP[interest]
            for idx, topic in enumerate(topics[:2]):  # 2 topics per interest for variety
                suggestion = _interest_suggestion(interest, topic, track, idx)
                # Boost slightly if this interest aligns with a graduation gap
                if track in gap_priorities:
                    suggestion.priority = min(1.0, suggestion.priority + 0.1)
                # Don't add duplicates
                if not any(s.title == suggestion.title for s in suggestions):
                    suggestions.append(suggestion)

    # 9. Fetch ZPD candidates for each track
    for track in active_tracks:
        try:
            candidates = await tool_get_zpd_candidates(student_id, track, limit=2)
            
            # Boost priority for weaker tracks (help balance progress)
            mastery = track_scores.get(track, 0.0)
            priority_boost = (1.0 - mastery) * 0.1  # Up to 0.1 boost for low mastery
            
            for candidate in candidates:
                suggestion = _zpd_to_suggestion(candidate, priority_boost)
                # Don't add duplicates
                if not any(s.title == suggestion.title for s in suggestions):
                    suggestions.append(suggestion)
        except Exception as e:
            logger.warning(f"[LearningPlan] ZPD query failed for track={track}: {e}")

    # 10. If we don't have enough suggestions, add grade-appropriate starter topics
    if len(suggestions) < limit:
        # Prioritize tracks with no ZPD suggestions
        tracks_with_suggestions = {s.track for s in suggestions}
        tracks_needing_starters = [t for t in active_tracks if t not in tracks_with_suggestions]
        
        # Also add starters for all tracks if we're really short
        if len(suggestions) < limit // 2:
            tracks_needing_starters = active_tracks

        for track in tracks_needing_starters:
            starters = _get_grade_appropriate_starters(track, grade_level)
            for idx, topic in enumerate(starters[:2]):  # Max 2 starters per track
                suggestion = _starter_suggestion(track, topic, idx)
                # Don't add duplicates
                if not any(s.title == suggestion.title for s in suggestions):
                    suggestions.append(suggestion)

    # 9. Sort by priority and limit
    suggestions.sort(key=lambda s: s.priority, reverse=True)
    suggestions = suggestions[:limit * 2]  # Keep extra for variety filtering

    # 10. Ensure variety — don't show more than 2 from the same track
    final_suggestions: list[LessonSuggestion] = []
    track_counts: dict[str, int] = {}
    for s in suggestions:
        if track_counts.get(s.track, 0) < 2:
            final_suggestions.append(s)
            track_counts[s.track] = track_counts.get(s.track, 0) + 1
        if len(final_suggestions) >= limit:
            break

    # If we still need more, add from remaining suggestions
    if len(final_suggestions) < limit:
        for s in suggestions:
            if s not in final_suggestions:
                final_suggestions.append(s)
            if len(final_suggestions) >= limit:
                break

    # 11. Fetch grade-level standards for K-8 students
    grade_standards = []
    try:
        grade_standards = await _get_grade_level_standards(student_id, grade_level)
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get grade standards: {e}")

    # 12. Fetch available portfolio projects — prefer tracks matching interests or weakest track
    try:
        preferred_track = None
        if interests:
            # Map the first interest to a track for project filtering
            first_interest = interests[0]
            if first_interest in INTEREST_TRACK_MAP:
                preferred_track = INTEREST_TRACK_MAP[first_interest][0]
        if not preferred_track and weakest_track:
            preferred_track = weakest_track
        projects = await _get_available_projects(track=preferred_track, limit=3)
        if len(projects) < 3:
            # Backfill with projects from any track if the preferred track doesn't have enough
            extra = await _get_available_projects(limit=3 - len(projects))
            existing_ids = {p.id for p in projects}
            projects += [p for p in extra if p.id not in existing_ids]
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get projects: {e}")
        projects = []

    # 13. Fetch gap-weighted book recommendations
    recommended_books: list[BookRecommendation] = []
    try:
        from app.api.books import get_gap_weighted_recommendations
        gap_dicts = [{"bucket": g.bucket, "remaining": g.remaining} for g in credit_gaps]
        raw_books = await get_gap_weighted_recommendations(
            student_id=student_id,
            grade_level=grade_level,
            interests=interests,
            credit_gaps=gap_dicts,
            weakest_track=weakest_track,
            is_high_school=graduation_progress.is_high_school,
            limit=4,
        )
        recommended_books = [
            BookRecommendation(
                id=b["id"],
                title=b["title"],
                author=b["author"],
                track=b.get("track", ""),
                lexile_level=b.get("lexile_level", 0),
                grade_band=b.get("grade_band"),
                cover_url=b.get("cover_url"),
                relevance_score=b.get("relevance_score", 0.0),
            )
            for b in raw_books
        ]
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get book recommendations: {e}")

    logger.info(
        f"[LearningPlan] Generated {len(final_suggestions)} suggestions, "
        f"{len(projects)} projects, {len(recommended_books)} books, "
        f"{len(grade_standards)} standards for student={student_id}"
    )

    response = LearningPlanResponse(
        student_id=student_id,
        suggestions=final_suggestions,
        projects=projects,
        recommended_books=recommended_books,
        total_tracks_active=len(active_tracks),
        strongest_track=strongest_track,
        weakest_track=weakest_track,
        total_credits_earned=total_credits,
        credits_this_week=weekly_credits,
        graduation_progress=graduation_progress,
        credit_gaps=credit_gaps if graduation_progress.is_high_school else [],  # Empty for K-8
        grade_standards=grade_standards,  # Only populated for K-8
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    # ── Cache the response (1 hour TTL — replenishment extends as lessons complete) ──
    try:
        await redis_client.set(cache_key, response.model_dump_json(), ex=3600)
        logger.info(f"[LearningPlan] Cached response for student={student_id} (1 hr TTL)")
    except Exception as e:
        logger.warning(f"[LearningPlan] Redis cache write failed (non-fatal): {e}")

    return response
