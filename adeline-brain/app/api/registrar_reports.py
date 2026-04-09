"""
Registrar Reports API - /api/registrar/reports endpoints
Provides reading progress analytics and recommendation tracking for administrative oversight.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import asyncpg
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.schemas.api_models import UserRole
from app.api.middleware import require_role, get_current_user_id
from app.config import POSTGRES_DSN as _DSN

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
