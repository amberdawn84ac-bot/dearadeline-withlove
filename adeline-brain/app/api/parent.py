"""
Parent Dashboard API — /api/parent/*

Multi-student management for parent accounts.

GET  /api/parent/students           — List all students for a parent
POST /api/parent/students           — Add a new student to family
GET  /api/parent/dashboard          — Aggregated progress across all students
PATCH /api/parent/students/{id}     — Update student profile
DELETE /api/parent/students/{id}    — Archive/remove student from family
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator

from app.api.middleware import get_current_user_id
from app.schemas.api_models import Track, UserRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parent", tags=["parent"])


# ── Request / Response Models ─────────────────────────────────────────────────

class StudentSummary(BaseModel):
    """Lightweight student info for parent dashboard."""
    id: str
    name: str
    email: str
    grade_level: str
    interests: List[str] = []
    created_at: str
    last_active: Optional[str] = None


class AddStudentRequest(BaseModel):
    """Request to add a new student to family."""
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    grade_level: str = Field(default="8")
    interests: List[str] = Field(default_factory=list, max_items=20)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_validator('grade_level')
    @classmethod
    def validate_grade_level(cls, v: str) -> str:
        """Validate grade level is 0-12."""
        try:
            grade = int(v)
            if not 0 <= grade <= 12:
                raise ValueError('Grade level must be between 0 and 12')
        except ValueError:
            raise ValueError('Grade level must be a number between 0 and 12')
        return v


class UpdateStudentRequest(BaseModel):
    """Request to update student profile."""
    name: Optional[str] = None
    grade_level: Optional[str] = None
    interests: Optional[List[str]] = None


class StudentProgress(BaseModel):
    """Per-student progress summary."""
    student_id: str
    student_name: str
    total_credits: float
    lessons_completed: int
    books_finished: int
    projects_sealed: int
    last_activity: Optional[str] = None
    active_track: Optional[str] = None


class FamilyDashboard(BaseModel):
    """Aggregated family progress."""
    parent_id: str
    total_students: int
    students: List[StudentProgress]
    family_total_credits: float
    recent_activity: List[dict]


# ── Helper Functions ──────────────────────────────────────────────────────────

async def _get_conn():
    """Get PostgreSQL connection with error handling."""
    from app.config import get_db_conn
    try:
        return await get_db_conn()
    except Exception as e:
        logger.error(f"[Parent] Database connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")


# ── API Endpoints ─────────────────────────────────────────────────────────────

@router.get("/students", response_model=List[StudentSummary])
async def list_students(
    authorization: Optional[str] = None,
):
    """
    List all students for the authenticated parent.
    Returns lightweight student summaries.
    """
    try:
        parent_id = get_current_user_id(authorization=authorization)
    except Exception as e:
        logger.error(f"[Parent] Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    async with _get_conn() as conn:
        # Verify parent role
        parent_row = await conn.fetchrow(
            'SELECT role FROM "User" WHERE id = $1',
            parent_id,
        )
        if not parent_row or parent_row["role"] != "PARENT":
            raise HTTPException(status_code=403, detail="Parent role required")
        
        # Fetch all children
        rows = await conn.fetch(
            '''
            SELECT id, name, email, "gradeLevel", interests, "createdAt"
            FROM "User"
            WHERE "parentId" = $1
            ORDER BY "createdAt" DESC
            ''',
            parent_id,
        )
        
        students = [
            StudentSummary(
                id=str(row["id"]),
                name=row["name"],
                email=row["email"],
                grade_level=row["gradeLevel"] or "8",
                interests=row["interests"] or [],
                created_at=row["createdAt"].isoformat() if row["createdAt"] else datetime.now(timezone.utc).isoformat(),
                last_active=None,  # TODO: Track last activity timestamp
            )
            for row in rows
        ]
        
        return students


@router.post("/students", response_model=StudentSummary)
async def add_student(
    payload: AddStudentRequest,
    authorization: Optional[str] = None,
):
    """
    Add a new student to the parent's family.
    Creates a new User record with STUDENT role and links to parent.
    """
    parent_id = get_current_user_id(authorization=authorization)
    
    async with _get_conn() as conn:
        # Verify parent role
        parent_row = await conn.fetchrow(
            'SELECT role FROM "User" WHERE id = $1',
            parent_id,
        )
        if not parent_row or parent_row["role"] != "PARENT":
            raise HTTPException(status_code=403, detail="Parent role required")
        
        # Check if email already exists
        existing = await conn.fetchrow(
            'SELECT id FROM "User" WHERE email = $1',
            payload.email,
        )
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")
        
        # Create new student
        student_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        await conn.execute(
            '''
            INSERT INTO "User" (
                id, name, email, role, "gradeLevel", interests, "parentId", "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''',
            student_id,
            payload.name,
            payload.email,
            "STUDENT",
            payload.grade_level,
            payload.interests,
            parent_id,
            now,
            now,
        )
        
        logger.info(f"[Parent] Added student {student_id} to parent {parent_id}")
        
        return StudentSummary(
            id=student_id,
            name=payload.name,
            email=payload.email,
            grade_level=payload.grade_level,
            interests=payload.interests,
            created_at=now.isoformat(),
            last_active=None,
        )


@router.get("/dashboard", response_model=FamilyDashboard)
async def get_family_dashboard(
    authorization: Optional[str] = None,
):
    """
    Get aggregated progress across all students in the family.
    Includes total credits, lessons, books, projects per student.
    """
    parent_id = get_current_user_id(authorization=authorization)
    
    async with _get_conn() as conn:
        # Verify parent role
        parent_row = await conn.fetchrow(
            'SELECT role FROM "User" WHERE id = $1',
            parent_id,
        )
        if not parent_row or parent_row["role"] != "PARENT":
            raise HTTPException(status_code=403, detail="Parent role required")
        
        # Fetch all children
        students_rows = await conn.fetch(
            'SELECT id, name FROM "User" WHERE "parentId" = $1',
            parent_id,
        )
        
        students_progress = []
        family_total_credits = 0.0
        
        for student_row in students_rows:
            student_id = str(student_row["id"])
            student_name = student_row["name"]
            
            # Get transcript entries for credits
            transcript_rows = await conn.fetch(
                'SELECT "creditHours" FROM "TranscriptEntry" WHERE "studentId" = $1',
                student_id,
            )
            total_credits = sum(float(row["creditHours"]) for row in transcript_rows)
            
            # Get lessons completed (sealed journal entries)
            lessons_count = await conn.fetchval(
                'SELECT COUNT(*) FROM "JournalEntry" WHERE "studentId" = $1 AND sealed = true',
                student_id,
            ) or 0
            
            # Get books finished
            books_count = await conn.fetchval(
                'SELECT COUNT(*) FROM "StudentBook" WHERE "studentId" = $1 AND status = $2',
                student_id,
                "finished",
            ) or 0
            
            # Get projects sealed (count journal entries with lesson_id starting with 'project-')
            projects_count = await conn.fetchval(
                '''
                SELECT COUNT(*) FROM "JournalEntry"
                WHERE "studentId" = $1 AND sealed = true AND "lessonId" LIKE 'project-%'
                ''',
                student_id,
            ) or 0
            
            students_progress.append(
                StudentProgress(
                    student_id=student_id,
                    student_name=student_name,
                    total_credits=round(total_credits, 2),
                    lessons_completed=lessons_count,
                    books_finished=books_count,
                    projects_sealed=projects_count,
                    last_activity=None,  # TODO: Track last activity
                    active_track=None,   # TODO: Get most recent track
                )
            )
            
            family_total_credits += total_credits
        
        # Get recent activity (last 10 sealed journal entries across all students)
        activity_rows = await conn.fetch(
            '''
            SELECT j."studentId", u.name as student_name, j."lessonId", j.track, j."sealedAt"
            FROM "JournalEntry" j
            JOIN "User" u ON u.id = j."studentId"
            WHERE u."parentId" = $1 AND j.sealed = true
            ORDER BY j."sealedAt" DESC
            LIMIT 10
            ''',
            parent_id,
        )
        
        recent_activity = [
            {
                "student_id": str(row["studentId"]),
                "student_name": row["student_name"],
                "lesson_id": row["lessonId"],
                "track": row["track"],
                "completed_at": row["sealedAt"].isoformat() if row["sealedAt"] else None,
            }
            for row in activity_rows
        ]
        
        return FamilyDashboard(
            parent_id=parent_id,
            total_students=len(students_rows),
            students=students_progress,
            family_total_credits=round(family_total_credits, 2),
            recent_activity=recent_activity,
        )


@router.patch("/students/{student_id}")
async def update_student(
    student_id: str,
    payload: UpdateStudentRequest,
    authorization: Optional[str] = None,
):
    """
    Update a student's profile.
    Only the parent who owns the student can update.
    """
    parent_id = get_current_user_id(authorization=authorization)
    
    async with _get_conn() as conn:
        # Verify parent owns this student
        student_row = await conn.fetchrow(
            'SELECT "parentId" FROM "User" WHERE id = $1',
            student_id,
        )
        if not student_row or student_row["parentId"] != parent_id:
            raise HTTPException(status_code=404, detail="Student not found or not owned by parent")
        
        # Build update query dynamically
        updates = []
        params = [student_id]
        param_idx = 2
        
        if payload.name is not None:
            updates.append(f'name = ${param_idx}')
            params.append(payload.name)
            param_idx += 1
        
        if payload.grade_level is not None:
            updates.append(f'"gradeLevel" = ${param_idx}')
            params.append(payload.grade_level)
            param_idx += 1
        
        if payload.interests is not None:
            updates.append(f'interests = ${param_idx}')
            params.append(payload.interests)
            param_idx += 1
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append(f'"updatedAt" = ${param_idx}')
        params.append(datetime.now(timezone.utc))
        
        query = f'UPDATE "User" SET {", ".join(updates)} WHERE id = $1'
        await conn.execute(query, *params)
        
        logger.info(f"[Parent] Updated student {student_id} by parent {parent_id}")
        
        return {"message": "Student updated successfully"}


@router.delete("/students/{student_id}")
async def remove_student(
    student_id: str,
    authorization: Optional[str] = None,
):
    """
    Remove a student from the family (soft delete by setting parentId to NULL).
    Student data is preserved but no longer appears in parent dashboard.
    """
    parent_id = get_current_user_id(authorization=authorization)
    
    async with _get_conn() as conn:
        # Verify parent owns this student
        student_row = await conn.fetchrow(
            'SELECT "parentId" FROM "User" WHERE id = $1',
            student_id,
        )
        if not student_row or student_row["parentId"] != parent_id:
            raise HTTPException(status_code=404, detail="Student not found or not owned by parent")
        
        # Soft delete: remove parent link
        await conn.execute(
            'UPDATE "User" SET "parentId" = NULL, "updatedAt" = $1 WHERE id = $2',
            datetime.now(timezone.utc),
            student_id,
        )
        
        logger.info(f"[Parent] Removed student {student_id} from parent {parent_id}")
        
        return {"message": "Student removed from family"}
