"""
Registrar Reports API - /api/registrar/reports endpoints
Provides reading progress analytics, OAS standards tracking, and graduation readiness reports.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import asyncpg
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.schemas.api_models import UserRole
from app.api.middleware import require_role, get_current_user_id
from app.config import POSTGRES_DSN as _DSN
from app.connections.postgres import get_db_session
from app.services.standards_mapper import StandardsMapper, StandardsProgressReport

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/registrar/reports", tags=["registrar-reports"])

# Pydantic models for responses
class ReadingProgressStats(BaseModel):
    studentId: str
    studentName: str
    gradeLevel: str
    booksCompleted: int
    averageReadingLevel: float
    totalReadingMinutes: int
    adaptiveLexileMin: int
    adaptiveLexileMax: int
    confidenceScore: float
    lastRecommendationDate: Optional[datetime]

class GradeLevelStats(BaseModel):
    gradeLevel: str
    totalStudents: int
    studentsWithRecommendations: int
    averageBooksCompleted: float
    averageReadingLevel: float
    averageConfidenceScore: float

class RecommendationAnalytics(BaseModel):
    totalRecommendations: int
    uniqueStudentsRecommended: int
    averageBooksPerRecommendation: float
    mostRecommendedTracks: List[Dict[str, Any]]
    adaptiveLevelDistribution: Dict[str, int]

# Database connection helper
async def _get_conn():
    """Get database connection."""
    return await asyncpg.connect(_DSN)

@router.get(
    "/reading-progress",
    response_model=List[ReadingProgressStats],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_reading_progress_report(
    grade_level: Optional[str] = Query(None, description="Filter by grade level"),
    days_since_last_recommendation: Optional[int] = Query(None, description="Filter students with no recommendations in X days"),
) -> List[ReadingProgressStats]:
    """
    Get comprehensive reading progress report for all students.
    
    Query Parameters:
    - grade_level: Filter by specific grade level (optional)
    - days_since_last_recommendation: Filter students who haven't received recommendations in X days (optional)
    
    Returns:
    - List of student reading progress statistics including adaptive levels and confidence scores
    """
    conn = await _get_conn()
    try:
        # Build base query
        query = """
        SELECT 
            u.id as "studentId",
            u.name as "studentName", 
            u."gradeLevel",
            COUNT(CASE WHEN rs.status = 'finished' THEN 1 END) as "booksCompleted",
            AVG(b.lexile_level) as "averageReadingLevel",
            COALESCE(SUM(rs."readingMinutes"), 0) as "totalReadingMinutes",
            MAX(rrl."adaptiveLexileMin") as "adaptiveLexileMin",
            MAX(rrl."adaptiveLexileMax") as "adaptiveLexileMax",
            MAX(rrl."confidenceScore") as "confidenceScore",
            MAX(rrl."recommendationDate") as "lastRecommendationDate"
        FROM "User" u
        LEFT JOIN "ReadingSession" rs ON u.id = rs."studentId"
        LEFT JOIN "Book" b ON rs."bookId" = b.id AND rs.status = 'finished'
        LEFT JOIN "ReadingRecommendationsLog" rrl ON u.id = rrl."studentId"
        WHERE u.role = 'STUDENT'
        """
        
        params = []
        param_count = 0
        
        # Add grade level filter if specified
        if grade_level:
            param_count += 1
            query += f' AND u."gradeLevel" = ${param_count}'
            params.append(grade_level)
        
        # Add days since last recommendation filter if specified
        if days_since_last_recommendation:
            param_count += 1
            query += f' AND (rrl."recommendationDate" < NOW() - INTERVAL \'1 day\' * ${param_count} OR rrl."recommendationDate" IS NULL)'
            params.append(days_since_last_recommendation)
        
        query += """
        GROUP BY u.id, u.name, u."gradeLevel"
        ORDER BY u."gradeLevel", u.name
        """
        
        rows = await conn.fetch(query, *params)
        
        # Convert to response models
        progress_stats = []
        for row in rows:
            stats = ReadingProgressStats(
                studentId=row["studentId"],
                studentName=row["studentName"] or "Unknown",
                gradeLevel=row["gradeLevel"] or "Unknown",
                booksCompleted=row["booksCompleted"] or 0,
                averageReadingLevel=float(row["averageReadingLevel"] or 0),
                totalReadingMinutes=row["totalReadingMinutes"] or 0,
                adaptiveLexileMin=row["adaptiveLexileMin"] or 0,
                adaptiveLexileMax=row["adaptiveLexileMax"] or 0,
                confidenceScore=float(row["confidenceScore"] or 0),
                lastRecommendationDate=row["lastRecommendationDate"],
            )
            progress_stats.append(stats)
        
        logger.info(f"[Registrar] Generated reading progress report for {len(progress_stats)} students")
        return progress_stats
        
    except Exception as e:
        logger.error(f"[Registrar] Failed to generate reading progress report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")
    finally:
        await conn.close()

@router.get(
    "/grade-level-stats",
    response_model=List[GradeLevelStats],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_grade_level_stats() -> List[GradeLevelStats]:
    """
    Get reading statistics aggregated by grade level.
    
    Returns:
    - List of grade-level statistics including completion rates and adaptive reading levels
    """
    conn = await _get_conn()
    try:
        rows = await conn.fetch("""
        SELECT 
            u."gradeLevel",
            COUNT(*) as "totalStudents",
            COUNT(DISTINCT rrl."studentId") as "studentsWithRecommendations",
            AVG(CASE WHEN rs.status = 'finished' THEN 1 ELSE 0 END) as "averageBooksCompleted",
            AVG(b.lexile_level) as "averageReadingLevel",
            AVG(rrl."confidenceScore") as "averageConfidenceScore"
        FROM "User" u
        LEFT JOIN "ReadingSession" rs ON u.id = rs."studentId"
        LEFT JOIN "Book" b ON rs."bookId" = b.id AND rs.status = 'finished'
        LEFT JOIN "ReadingRecommendationsLog" rrl ON u.id = rrl."studentId"
        WHERE u.role = 'STUDENT' AND u."gradeLevel" IS NOT NULL
        GROUP BY u."gradeLevel"
        ORDER BY u."gradeLevel"
        """)
        
        grade_stats = []
        for row in rows:
            stats = GradeLevelStats(
                gradeLevel=row["gradeLevel"] or "Unknown",
                totalStudents=row["totalStudents"] or 0,
                studentsWithRecommendations=row["studentsWithRecommendations"] or 0,
                averageBooksCompleted=float(row["averageBooksCompleted"] or 0),
                averageReadingLevel=float(row["averageReadingLevel"] or 0),
                averageConfidenceScore=float(row["averageConfidenceScore"] or 0),
            )
            grade_stats.append(stats)
        
        logger.info(f"[Registrar] Generated grade level stats for {len(grade_stats)} grades")
        return grade_stats
        
    except Exception as e:
        logger.error(f"[Registrar] Failed to generate grade level stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate grade stats")
    finally:
        await conn.close()

@router.get(
    "/recommendation-analytics",
    response_model=RecommendationAnalytics,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_recommendation_analytics(
    days_back: int = Query(30, description="Number of days to analyze"),
) -> RecommendationAnalytics:
    """
    Get analytics about book recommendations for registrar oversight.
    
    Query Parameters:
    - days_back: Number of days to look back for analysis (default: 30)
    
    Returns:
    - Comprehensive analytics about recommendations, tracks, and adaptive levels
    """
    conn = await _get_conn()
    try:
        # Get overall recommendation stats
        overall_stats = await conn.fetchrow("""
        SELECT 
            COUNT(*) as "totalRecommendations",
            COUNT(DISTINCT "studentId") as "uniqueStudentsRecommended",
            AVG(array_length("recommendedBookIds", 1)) as "averageBooksPerRecommendation"
        FROM "ReadingRecommendationsLog" 
        WHERE "recommendationDate" >= NOW() - INTERVAL '1 day' * $1
        """, days_back)
        
        # Get most recommended tracks
        track_stats = await conn.fetch("""
        SELECT 
            b.track,
            COUNT(*) as "recommendationCount"
        FROM "ReadingRecommendationsLog" rrl
        JOIN unnest(rrl."recommendedBookIds") as book_id ON true
        JOIN "Book" b ON book_id = b.id
        WHERE rrl."recommendationDate" >= NOW() - INTERVAL '1 day' * $1
        GROUP BY b.track
        ORDER BY "recommendationCount" DESC
        LIMIT 10
        """, days_back)
        
        # Get adaptive level distribution
        level_dist = await conn.fetch("""
        SELECT 
            CASE 
                WHEN "adaptiveLexileMin" < 300 THEN 'Emerging (K-2)'
                WHEN "adaptiveLexileMin" < 600 THEN 'Developing (3-5)'
                WHEN "adaptiveLexileMin" < 900 THEN 'Expanding (6-8)'
                ELSE 'Mastering (9-12)'
            END as "levelCategory",
            COUNT(*) as "count"
        FROM "ReadingRecommendationsLog" 
        WHERE "recommendationDate" >= NOW() - INTERVAL '1 day' * $1
        GROUP BY "levelCategory"
        ORDER BY "count" DESC
        """, days_back)
        
        # Build response
        analytics = RecommendationAnalytics(
            totalRecommendations=overall_stats["totalRecommendations"] or 0,
            uniqueStudentsRecommended=overall_stats["uniqueStudentsRecommended"] or 0,
            averageBooksPerRecommendation=float(overall_stats["averageBooksPerRecommendation"] or 0),
            mostRecommendedTracks=[
                {"track": row["track"], "count": row["recommendationCount"]} 
                for row in track_stats
            ],
            adaptiveLevelDistribution={
                row["levelCategory"]: row["count"] for row in level_dist
            },
        )
        
        logger.info(f"[Registrar] Generated recommendation analytics for {days_back} days")
        return analytics
        
    except Exception as e:
        logger.error(f"[Registrar] Failed to generate recommendation analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate analytics")
    finally:
        await conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# OAS Standards Progress & Graduation Readiness (Cached)
# ═══════════════════════════════════════════════════════════════════════════════

class OASSubjectProgress(BaseModel):
    """OAS standards progress for a single subject."""
    subject: str
    total_standards: int
    developing: int
    approaching: int
    understanding: int
    extending: int
    saturation_percentage: float


class OASStandardsProgress(BaseModel):
    """Student's OAS standards mastery progress."""
    student_id: str
    by_subject: list[OASSubjectProgress]
    total_standards: int
    mastered_standards: int
    overall_saturation: float
    last_updated: datetime


class OSRHECoreStatus(BaseModel):
    """OSRHE 15-unit core compliance status."""
    english: float
    math: float
    lab_science: float
    social_studies: float


class GraduationReadiness(BaseModel):
    """Complete graduation readiness report."""
    student_id: str
    osrhe_core_status: OSRHECoreStatus
    total_credits: float
    oas_saturation: float
    readiness_score: float  # 0-100
    recommendations: list[str]
    last_updated: datetime


@router.get(
    "/oas-standards-progress/{student_id}",
    response_model=OASStandardsProgress,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_oas_standards_progress(
    student_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get student's OAS standards mastery progress.
    
    Uses StandardsMapper for comprehensive progress tracking.
    Admin-only for privacy; parents see their own children via parent dashboard.
    """
    try:
        mapper = StandardsMapper(db)
        report = await mapper.get_student_standards_progress(
            student_id=student_id,
            pg_session=db,
        )
        
        return OASStandardsProgress(
            student_id=report.student_id,
            by_subject=[
                OASSubjectProgress(
                    subject=s.subject,
                    total_standards=s.total_standards,
                    developing=s.standards_by_proficiency["developing"],
                    approaching=s.standards_by_proficiency["approaching"],
                    understanding=s.standards_by_proficiency["understanding"],
                    extending=s.standards_by_proficiency["extending"],
                    saturation_percentage=s.saturation_percentage,
                )
                for s in report.by_subject.values()
            ],
            total_standards=report.total_standards,
            mastered_standards=report.mastered_standards,
            overall_saturation=report.overall_saturation,
            last_updated=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"[Registrar] Failed to get OAS progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to get standards progress")


@router.get(
    "/graduation-readiness/{student_id}",
    response_model=GraduationReadiness,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_graduation_readiness(
    student_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get student's graduation readiness report.
    
    Combines:
    - OSRHE 15-unit core compliance
    - OAS standards saturation
    - Credit accumulation
    - Readiness score (composite)
    
    Uses cached materialized view when available for performance.
    """
    try:
        # Try cached view first
        cached = await db.execute(
            text("""
                SELECT student_id, subject, mastered_count, saturation_pct
                FROM graduation_readiness_cache
                WHERE student_id = :student_id
            """),
            {"student_id": student_id},
        )
        cached_rows = cached.mappings().all()
        
        if cached_rows:
            # Use cached data
            by_subject = {row["subject"]: row for row in cached_rows}
            overall_saturation = sum(r["saturation_pct"] for r in cached_rows) / len(cached_rows)
        else:
            # Compute fresh
            mapper = StandardsMapper(db)
            report = await mapper.get_student_standards_progress(
                student_id=student_id,
                pg_session=db,
            )
            by_subject = report.by_subject
            overall_saturation = report.overall_saturation
        
        # Get credit hours from CreditLedger
        conn = await _get_conn()
        try:
            credit_result = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(hours), 0) as total_hours
                FROM "CreditLedgerEntry"
                WHERE "studentId" = $1
                """,
                student_id,
            )
            total_credits = credit_result["total_hours"] if credit_result else 0
        finally:
            await conn.close()
        
        # Calculate OSRHE core status (simplified - use actual bucket data)
        osrhe_status = OSRHECoreStatus(
            english=by_subject.get("ELA", {}).get("saturation_percentage", 0) if isinstance(by_subject.get("ELA"), dict) else getattr(by_subject.get("ELA"), "saturation_percentage", 0),
            math=by_subject.get("MATH", {}).get("saturation_percentage", 0) if isinstance(by_subject.get("MATH"), dict) else getattr(by_subject.get("MATH"), "saturation_percentage", 0),
            lab_science=by_subject.get("SCIENCE", {}).get("saturation_percentage", 0) if isinstance(by_subject.get("SCIENCE"), dict) else getattr(by_subject.get("SCIENCE"), "saturation_percentage", 0),
            social_studies=by_subject.get("SOCIAL_STUDIES", {}).get("saturation_percentage", 0) if isinstance(by_subject.get("SOCIAL_STUDIES"), dict) else getattr(by_subject.get("SOCIAL_STUDIES"), "saturation_percentage", 0),
        )
        
        # Calculate readiness score (0-100)
        readiness = (
            osrhe_status.english * 0.25 +
            osrhe_status.math * 0.25 +
            osrhe_status.lab_science * 0.25 +
            osrhe_status.social_studies * 0.25
        )
        
        # Generate recommendations
        recommendations = []
        if osrhe_status.english < 70:
            recommendations.append("Increase ELA practice to reach 70% saturation")
        if osrhe_status.math < 70:
            recommendations.append("Focus on math fundamentals for college readiness")
        if total_credits < 15:
            recommendations.append(f"Accumulate more credits (currently {total_credits:.1f}/15)")
        if overall_saturation < 80:
            recommendations.append("Work toward 80% OAS standards mastery")
        
        return GraduationReadiness(
            student_id=student_id,
            osrhe_core_status=osrhe_status,
            total_credits=round(total_credits, 2),
            oas_saturation=round(overall_saturation, 2),
            readiness_score=round(readiness, 2),
            recommendations=recommendations or ["On track for graduation"],
            last_updated=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"[Registrar] Failed to get graduation readiness: {e}")
        raise HTTPException(status_code=500, detail="Failed to get graduation readiness")


# ═══════════════════════════════════════════════════════════════════════════════
# Wire 3: Transcript Translation (10-Track → Traditional Oklahoma Courses)
# ═══════════════════════════════════════════════════════════════════════════════

class TranslatedCourse(BaseModel):
    """Traditional Oklahoma course name mapped from 10-track progress."""
    traditional_name: str  # e.g., "Algebra I"
    oas_codes: list[str]   # Contributing OAS standards
    track_sources: list[str]  # e.g., ["APPLIED_MATHEMATICS", "JUSTICE_CHANGEMAKING"]
    credit_hours: float
    grade_letter: str
    rationale: str


class TranscriptTranslationResponse(BaseModel):
    """Public School Parity transcript for external institutions."""
    student_id: str
    profile: str  # "oklahoma_college_prep" or "oklahoma_public_school_parity"
    courses: list[TranslatedCourse]
    total_credits: float
    osrhe_core_compliant: bool


# Credit translation map: 10-track → Traditional Oklahoma courses
# Example: APPLIED_MATHEMATICS + JUSTICE (finance) = Personal Financial Literacy
CREDIT_TRANSLATION_MAP = {
    # Math track combinations
    "ALGEBRA_I": {
        "tracks": ["APPLIED_MATHEMATICS"],
        "min_saturation": 70,
        "credit_hours": 1.0,
        "bucket": "MATH_CORE",
        "description": "Linear equations, functions, and graphing",
    },
    "GEOMETRY": {
        "tracks": ["APPLIED_MATHEMATICS"],
        "min_saturation": 70,
        "credit_hours": 1.0,
        "bucket": "MATH_CORE",
        "description": "Euclidean geometry and proofs",
    },
    "ALGEBRA_II": {
        "tracks": ["APPLIED_MATHEMATICS"],
        "min_saturation": 75,
        "credit_hours": 1.0,
        "bucket": "MATH_CORE",
        "description": "Advanced algebraic concepts",
    },
    # Personal Financial Literacy (special combo)
    "PERSONAL_FINANCIAL_LITERACY": {
        "tracks": ["APPLIED_MATHEMATICS", "GOVERNMENT_ECONOMICS"],
        "min_saturation": 60,  # Lower threshold for combined tracks
        "credit_hours": 0.5,
        "bucket": "PERSONAL_FINANCE",
        "description": "Budgeting, investing, and economic decision-making",
        "requires_both": True,  # Must have progress in BOTH tracks
    },
    # English/Language Arts
    "ENGLISH_I": {
        "tracks": ["ENGLISH_LITERATURE"],
        "min_saturation": 70,
        "credit_hours": 1.0,
        "bucket": "ENGLISH_CORE",
        "description": "Literature, composition, and grammar",
    },
    "ENGLISH_II": {
        "tracks": ["ENGLISH_LITERATURE", "TRUTH_HISTORY"],  # Includes research writing
        "min_saturation": 70,
        "credit_hours": 1.0,
        "bucket": "ENGLISH_CORE",
        "description": "Advanced composition and research skills",
    },
    # Science
    "BIOLOGY": {
        "tracks": ["CREATION_SCIENCE"],
        "min_saturation": 70,
        "credit_hours": 1.0,
        "bucket": "SCIENCE_CORE",
        "description": "Life sciences and biology fundamentals",
    },
    "PHYSICAL_SCIENCE": {
        "tracks": ["CREATION_SCIENCE", "APPLIED_MATHEMATICS"],  # Physics + Math
        "min_saturation": 65,
        "credit_hours": 1.0,
        "bucket": "SCIENCE_CORE",
        "description": "Chemistry and physics foundations",
    },
    # Social Studies
    "OKLAHOMA_HISTORY": {
        "tracks": ["TRUTH_HISTORY", "GOVERNMENT_ECONOMICS"],
        "min_saturation": 70,
        "credit_hours": 0.5,
        "bucket": "SOCIAL_STUDIES",
        "description": "Oklahoma state history and government",
    },
    "US_HISTORY": {
        "tracks": ["TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"],
        "min_saturation": 75,
        "credit_hours": 1.0,
        "bucket": "SOCIAL_STUDIES",
        "description": "United States history with primary sources",
    },
    "US_GOVERNMENT": {
        "tracks": ["GOVERNMENT_ECONOMICS", "JUSTICE_CHANGEMAKING"],
        "min_saturation": 70,
        "credit_hours": 0.5,
        "bucket": "SOCIAL_STUDIES",
        "description": "Civics and American government",
    },
    # Electives (from specialized tracks)
    "ENVIRONMENTAL_SCIENCE": {
        "tracks": ["HOMESTEADING", "CREATION_SCIENCE"],
        "min_saturation": 60,
        "credit_hours": 1.0,
        "bucket": "ELECTIVES",
        "description": "Sustainable agriculture and ecology",
    },
    "HEALTH_WELLNESS": {
        "tracks": ["HEALTH_NATUROPATHY", "DISCIPLESHIP"],
        "min_saturation": 65,
        "credit_hours": 0.5,
        "bucket": "ELECTIVES",
        "description": "Holistic health and wellness practices",
    },
}


@router.get(
    "/transcript-translation/{student_id}",
    response_model=TranscriptTranslationResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_transcript_translation(
    student_id: str,
    profile: str = Query("oklahoma_college_prep", description="Transcript profile: oklahoma_college_prep or oklahoma_public_school_parity"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Translate 10-track progress into traditional Oklahoma course names.

    **Wire 3: Public School Parity Translation Layer**

    This endpoint converts Dear Adeline's 10-track mastery into course names
    that technical schools and colleges understand.

    Example translation:
    - APPLIED_MATHEMATICS (75% saturation) + JUSTICE (finance unit) 
      → "Personal Financial Literacy" (0.5 credits)
    - TRUTH_HISTORY (80% saturation) + JUSTICE (civics unit) 
      → "US Government" (0.5 credits)

    Query Parameters:
    - profile: "oklahoma_college_prep" (default) or "oklahoma_public_school_parity"

    Returns:
    - List of traditional courses with credit hours and grade estimates
    - OSRHE core compliance status
    - Total credits for transcript
    """
    try:
        # Get student's track mastery data
        mapper = StandardsMapper(db)
        report = await mapper.get_student_standards_progress(
            student_id=student_id,
            pg_session=db,
        )

        # Build track saturation map
        track_saturation = {}
        for subject_progress in report.by_subject.values():
            # Map subject back to track
            track_name = subject_progress.subject.replace("ELA", "ENGLISH_LITERATURE")
            track_saturation[track_name] = subject_progress.saturation_percentage

        # Calculate traditional courses
        translated_courses: list[TranslatedCourse] = []
        
        for course_name, rules in CREDIT_TRANSLATION_MAP.items():
            tracks_required = rules["tracks"]
            min_saturation = rules["min_saturation"]
            requires_both = rules.get("requires_both", False)
            
            # Check if student meets requirements
            track_saturations = [
                track_saturation.get(t, 0) 
                for t in tracks_required
            ]
            
            if requires_both:
                # Must meet threshold in ALL required tracks
                qualifies = all(s >= min_saturation for s in track_saturations)
            else:
                # Can meet threshold in ANY required track
                qualifies = any(s >= min_saturation for s in track_saturations)
            
            if qualifies:
                # Calculate grade based on average saturation
                avg_saturation = sum(track_saturations) / len(track_saturations)
                if avg_saturation >= 90:
                    grade = "A"
                elif avg_saturation >= 80:
                    grade = "B"
                elif avg_saturation >= 70:
                    grade = "C"
                elif avg_saturation >= 60:
                    grade = "D"
                else:
                    grade = "F"
                
                # Get contributing OAS standards
                # In production, this would query which specific standards
                # from these tracks contributed to the credit
                contributing_codes = [
                    f"OAS.{t[:3].upper()}.X.X"  # Placeholder - would be actual codes
                    for t in tracks_required
                ]
                
                translated_courses.append(TranslatedCourse(
                    traditional_name=course_name.replace("_", " "),
                    oas_codes=contributing_codes,
                    track_sources=tracks_required,
                    credit_hours=rules["credit_hours"],
                    grade_letter=grade,
                    rationale=rules["description"],
                ))
        
        # Calculate total credits
        total_credits = sum(c.credit_hours for c in translated_courses)
        
        # Check OSRHE core compliance
        core_buckets = {"ENGLISH_CORE": 4, "MATH_CORE": 3, "SCIENCE_CORE": 3, "SOCIAL_STUDIES": 3}
        bucket_credits = {bucket: 0.0 for bucket in core_buckets}
        
        for course in translated_courses:
            for course_name, rules in CREDIT_TRANSLATION_MAP.items():
                if course.traditional_name == course_name.replace("_", " "):
                    bucket = rules.get("bucket", "ELECTIVES")
                    if bucket in bucket_credits:
                        bucket_credits[bucket] += course.credit_hours
        
        osrhe_compliant = all(
            bucket_credits[b] >= required 
            for b, required in core_buckets.items()
        )
        
        return TranscriptTranslationResponse(
            student_id=student_id,
            profile=profile,
            courses=translated_courses,
            total_credits=round(total_credits, 2),
            osrhe_core_compliant=osrhe_compliant,
        )
        
    except Exception as e:
        logger.error(f"[Registrar] Transcript translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to translate transcript: {str(e)}")
