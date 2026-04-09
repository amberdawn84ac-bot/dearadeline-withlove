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
import logging
import random
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Header
from pydantic import BaseModel

from app.schemas.api_models import Track
from app.models.student import load_student_state, MasteryBand
from app.connections.journal_store import journal_store
from app.connections.neo4j_client import neo4j_client
from app.connections.pgvector_client import hippocampus
from app.tools.graph_query import tool_get_zpd_candidates, ZPDCandidate

# Graduation requirements (Oklahoma public school standards - 23 credits)
GRADUATION_REQUIREMENTS = {
    "ENGLISH_CORE": 4.0,      # Language Arts (English Literature)
    "MATH_CORE": 3.0,         # Math (Applied Mathematics, Algebra 1+)
    "SCIENCE_CORE": 3.0,      # Lab Science (Creation Science + Physical Science + Biology)
    "SOCIAL_STUDIES": 3.0,    # Social Studies (Truth History + Oklahoma History + Government)
    "WORLD_LANGUAGE": 2.0,     # Technology or World Language (2 units same language)
    "PERSONAL_FINANCE": 0.5,   # Personal Financial Literacy
    "FINE_ARTS": 1.0,          # Art or Speech (Creative Economy)
    "ELECTIVES": 6.5,        # Additional electives (Homesteading + Discipleship + Justice Changemaking)
}
TOTAL_REQUIRED = sum(GRADUATION_REQUIREMENTS.values())  # 23.0 credits

# Map tracks to credit buckets
TRACK_TO_BUCKET = {
    "ENGLISH_LITERATURE": "ENGLISH_CORE",
    "APPLIED_MATHEMATICS": "MATH_CORE",
    "CREATION_SCIENCE": "SCIENCE_CORE",
    "TRUTH_HISTORY": "SOCIAL_STUDIES",
    "GOVERNMENT_ECONOMICS": "SOCIAL_STUDIES",
    "HEALTH_NATUROPATHY": "PERSONAL_FINANCE",  # Health + Financial Literacy
    "CREATIVE_ECONOMY": "FINE_ARTS",
    "HOMESTEADING": "ELECTIVES",
    "DISCIPLESHIP": "ELECTIVES",
    "JUSTICE_CHANGEMAKING": "ELECTIVES",
    # Note: WORLD_LANGUAGE requirement can be met with Technology track or 2 units of same language
    # We'll map Technology requirements to existing tracks where applicable
}

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/learning-plan", tags=["learning-plan"])


# ── Response Models ────────────────────────────────────────────────────────────

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


class CreditGap(BaseModel):
    bucket: str
    required: float
    earned: float
    remaining: float
    priority: int  # 1=highest priority, 7=lowest

class GraduationProgress(BaseModel):
    total_required: float
    total_earned: float
    percentage_complete: float
    credits_remaining: float
    on_track: bool  # Based on grade level and expected progress

class LearningPlanResponse(BaseModel):
    student_id: str
    suggestions: list[LessonSuggestion]
    projects: list[ProjectSuggestion]  # Portfolio projects ready to start
    total_tracks_active: int
    strongest_track: Optional[str] = None
    weakest_track: Optional[str] = None
    total_credits_earned: float = 0.0
    credits_this_week: float = 0.0
    graduation_progress: GraduationProgress
    credit_gaps: list[CreditGap]  # What's still needed for graduation
    generated_at: str


# ── Track metadata ─────────────────────────────────────────────────────────────

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
    "TRUTH_HISTORY": "🏛️",
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

# Starter topics for tracks with no ZPD data yet
STARTER_TOPICS = {
    "TRUTH_HISTORY": [
        ("The Declaration of Independence", "What the founders actually wrote — and what they left out"),
        ("The Trail of Tears", "Primary sources from those who survived forced removal"),
        ("The American Revolution", "Letters and documents from the founding era"),
    ],
    "CREATION_SCIENCE": [
        ("Butterfly Life Cycles", "Metamorphosis and adaptation in nature"),
        ("The Water Cycle", "Hands-on experiments with evaporation"),
        ("Soil Biology", "The living world beneath your feet"),
    ],
    "HOMESTEADING": [
        ("Starting a Garden", "Planning and planting your first beds"),
        ("Raising Chickens", "From chicks to eggs — the basics"),
        ("Food Preservation", "Canning, drying, and storing the harvest"),
    ],
    "DISCIPLESHIP": [
        ("The Psalms", "Hebrew poetry and original meanings"),
        ("The Sermon on the Mount", "What Jesus actually said — and meant"),
        ("Genesis Creation Account", "Reading the text in its original context"),
    ],
    "JUSTICE_CHANGEMAKING": [
        ("Corporate Accountability", "Following the money to find the truth"),
        ("Environmental Justice", "Who profits when communities are poisoned"),
        ("Media Literacy", "How to spot propaganda and manipulation"),
    ],
    "HEALTH_NATUROPATHY": [
        ("How the Body Heals", "Understanding your immune system"),
        ("Herbal Medicine Basics", "Plants that actually work"),
        ("Nutrition Truth", "What the food industry doesn't want you to know"),
    ],
    "GOVERNMENT_ECONOMICS": [
        ("How Laws Really Get Made", "Lobbying, money, and power"),
        ("The Federal Reserve", "Who controls the money supply"),
        ("Local Government", "Where your voice actually matters"),
    ],
    "ENGLISH_LITERATURE": [
        ("Reading Critically", "What is the author asking you to believe?"),
        ("Narrative Voice", "Who is telling the story — and why"),
        ("Poetry as Resistance", "Words that changed movements"),
    ],
    "APPLIED_MATHEMATICS": [
        ("Budgeting Basics", "Managing money in the real world"),
        ("Measuring and Building", "Math for construction and crafts"),
        ("Understanding Interest", "How loans and savings really work"),
    ],
    "CREATIVE_ECONOMY": [
        ("Pricing Your Work", "What your time and skill are worth"),
        ("Building a Brand", "Standing out in the marketplace"),
        ("From Idea to Product", "Taking a project from concept to sale"),
    ],
}


def _zpd_to_suggestion(candidate: ZPDCandidate, priority_boost: float = 0.0) -> LessonSuggestion:
    """Convert a ZPD candidate to a lesson suggestion."""
    return LessonSuggestion(
        id=f"zpd-{candidate.concept_id}",
        title=candidate.title,
        track=candidate.track,
        description=candidate.description or TRACK_DESCRIPTIONS.get(candidate.track, ""),
        emoji=TRACK_EMOJI.get(candidate.track, "📚"),
        priority=0.9 + priority_boost,  # ZPD candidates are high priority
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
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
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
    )


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
            difficulty=proj.difficulty.value,
            estimated_hours=proj.estimated_hours,
            portfolio_credit=True,
        ))
        if len(projects) >= limit:
            break
    return projects


@router.get("/{student_id}", response_model=LearningPlanResponse)
async def get_learning_plan(
    student_id: str,
    limit: int = Query(6, ge=1, le=12),
    include_all_tracks: bool = Query(False),
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
            # Find tracks that fulfill this bucket
            for track, bucket in TRACK_TO_BUCKET.items():
                if bucket == gap.bucket and track in active_tracks:
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
                    
            # If no ZPD candidates, add starter topics for gaps
            if not candidates and track in STARTER_TOPICS:
                starters = STARTER_TOPICS[track][:1]  # Just 1 starter for gaps
                for topic in starters:
                    suggestion = _starter_suggestion(track, topic, 0)
                    suggestion.priority = 0.8  # High priority for gaps
                    if not any(s.title == suggestion.title for s in suggestions):
                        suggestions.append(suggestion)
                        
        except Exception as e:
            logger.warning(f"[LearningPlan] Gap-based suggestions failed for track={track}: {e}")

    # 8. Generate interest-based suggestions (medium priority)
    for interest in interests[:2]:  # Top 2 interests (reduced to make room for gaps)
        if interest in INTEREST_TRACK_MAP:
            track, topics = INTEREST_TRACK_MAP[interest]
            # Lower priority if this track isn't a gap
            priority = 0.6 if track not in gap_priorities else 0.75
            
            for idx, topic in enumerate(topics[:1]):  # 1 topic per interest
                suggestion = _interest_suggestion(interest, topic, track, idx)
                suggestion.priority = priority
                # Don't add duplicates
                if not any(s.title == suggestion.title for s in suggestions):
                    suggestions.append(suggestion)

    # 7. Fetch ZPD candidates for each track
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

    # 8. If we don't have enough suggestions, add starter topics
    if len(suggestions) < limit:
        # Prioritize tracks with no ZPD suggestions
        tracks_with_suggestions = {s.track for s in suggestions}
        tracks_needing_starters = [t for t in active_tracks if t not in tracks_with_suggestions]
        
        # Also add starters for all tracks if we're really short
        if len(suggestions) < limit // 2:
            tracks_needing_starters = active_tracks

        for track in tracks_needing_starters:
            starters = STARTER_TOPICS.get(track, [])
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

    # 11. Fetch available portfolio projects
    try:
        projects = await _get_available_projects(limit=3)
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get projects: {e}")
        projects = []

    logger.info(
        f"[LearningPlan] Generated {len(final_suggestions)} suggestions, "
        f"{len(projects)} projects for student={student_id}"
    )

    return LearningPlanResponse(
        student_id=student_id,
        suggestions=final_suggestions,
        projects=projects,
        total_tracks_active=len(active_tracks),
        strongest_track=strongest_track,
        weakest_track=weakest_track,
        total_credits_earned=total_credits,
        credits_this_week=weekly_credits,
        graduation_progress=graduation_progress,
        credit_gaps=credit_gaps,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
