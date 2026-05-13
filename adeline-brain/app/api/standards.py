"""
Standards API — /api/standards/* endpoints

Provides:
- POST /evidence — Submit mastery evidence for OAS standards
- POST /evidence/upload — Upload photo/video evidence files
- GET /progress/{student_id} — Get student's standards progress
- GET /match — Find relevant standards for lesson content
- GET /gaps/{student_id} — Identify learning gaps for gap-filler loop

Integration points:
- MasteryCheckWidget.tsx submits evidence here
- PedagogyAgent queries match endpoint
- Daily Bread uses gaps endpoint for personalization
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware import get_current_user_id
from app.connections.postgres import get_db_session
from app.services.standards_mapper import (
    StandardsMapper,
    MasteryEvidence,
    OASProficiencyLevel,
    StandardsSubject,
)
from app.services.storage import upload_mastery_evidence

router = APIRouter(prefix="/api/standards", tags=["standards"])


# ═══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceSubmitRequest(BaseModel):
    student_id: str
    standard_id: str
    evidence_type: str  # "quiz", "photo", "video", "project", "discussion"
    score: Optional[float] = None  # 0-100 for quiz scores
    file_url: Optional[str] = None
    description: str = ""


class EvidenceSubmitResponse(BaseModel):
    success: bool
    standard_id: str
    proficiency: str
    evidence_count: int
    message: str


class StandardsMatchRequest(BaseModel):
    content: str
    track: str
    grade: int
    top_k: int = 5


class StandardMatchResult(BaseModel):
    code: str
    subject: str
    grade: int
    description: str
    confidence: float


class StandardsMatchResponse(BaseModel):
    standards: list[StandardMatchResult]
    query_track: str
    query_grade: int


class SubjectProgressItem(BaseModel):
    subject: str
    total_standards: int
    developing: int
    approaching: int
    understanding: int
    extending: int
    saturation_percentage: float
    gap_standards: list[str]


class StandardsProgressResponse(BaseModel):
    student_id: str
    by_subject: list[SubjectProgressItem]
    total_standards: int
    mastered_standards: int
    overall_saturation: float


class GapStandard(BaseModel):
    standard_id: str
    reason: str


class LearningGapsResponse(BaseModel):
    student_id: str
    priority_subject: str
    saturation: float
    gap_standards: list[GapStandard]
    suggested_daily_bread: str


# ═══════════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/evidence", response_model=EvidenceSubmitResponse)
async def submit_standard_evidence(
    request: EvidenceSubmitRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Submit evidence for OAS standard mastery.
    
    This endpoint:
    1. Validates the evidence (photo/video/quiz score)
    2. Determines proficiency level (developing/approaching/understanding/extending)
    3. Creates/updates StandardMastery record
    4. Updates Neo4j (Student)-[:MASTERED]->(OASStandard)
    5. Invalidates graduation report cache
    
    Called by: MasteryCheckWidget.tsx when quiz passed, or evidence upload
    """
    # Security: Only allow submitting for self or parent submitting for child
    if request.student_id != current_user_id:
        # TODO: Add parent-child relationship check
        raise HTTPException(status_code=403, detail="Cannot submit evidence for other students")
    
    mapper = StandardsMapper(db)
    
    evidence = MasteryEvidence(
        evidence_type=request.evidence_type,
        score=request.score,
        file_url=request.file_url,
        description=request.description,
        submitted_at=datetime.utcnow(),
    )
    
    try:
        mastery = await mapper.record_mastery_evidence(
            student_id=request.student_id,
            standard_id=request.standard_id,
            evidence=evidence,
            pg_session=db,
        )
        
        await db.commit()
        
        return EvidenceSubmitResponse(
            success=True,
            standard_id=mastery.standard_id,
            proficiency=mastery.proficiency.value,
            evidence_count=mastery.evidence_count,
            message=f"Evidence recorded. Proficiency: {mastery.proficiency.value}",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record evidence: {str(e)}")


@router.post("/evidence/upload")
async def upload_evidence_file(
    student_id: str = Form(...),
    standard_id: str = Form(...),
    evidence_type: str = Form(...),  # "photo" | "video"
    description: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Upload photo/video evidence file for OAS standard mastery.
    
    **CRITICAL: Files are stored in S3/Supabase, NOT PostgreSQL.**
    The StandardMastery table only stores the URL to the file.
    
    Supports: image/jpeg, image/png, image/gif, video/mp4, video/webm
    Max file size: 50MB (enforced by nginx/railway)
    
    Returns: EvidenceSubmitResponse with file_url pointing to cloud storage
    """
    # Security check
    if student_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot upload evidence for other students")
    
    # Validate file type
    allowed_types = {
        "image/jpeg": "photo",
        "image/jpg": "photo",
        "image/png": "photo",
        "image/gif": "photo",
        "video/mp4": "video",
        "video/webm": "video",
        "video/quicktime": "video",
    }
    
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {content_type}. Allowed: {list(allowed_types.keys())}"
        )
    
    if allowed_types[content_type] != evidence_type:
        raise HTTPException(
            status_code=400,
            detail=f"File type {content_type} doesn't match evidence_type {evidence_type}"
        )
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")
        
        # Upload to S3/Supabase (Wire 2: Blob Storage)
        file_url = await upload_mastery_evidence(
            student_id=student_id,
            standard_id=standard_id,
            file_bytes=file_bytes,
            content_type=content_type,
            original_filename=file.filename,
        )
        
        # Record in database (just the URL, not the bytes!)
        mapper = StandardsMapper(db)
        evidence = MasteryEvidence(
            evidence_type=evidence_type,
            file_url=file_url,
            description=description or f"Evidence upload: {file.filename}",
            submitted_at=datetime.utcnow(),
        )
        
        mastery = await mapper.record_mastery_evidence(
            student_id=student_id,
            standard_id=standard_id,
            evidence=evidence,
            pg_session=db,
        )
        
        await db.commit()
        
        return EvidenceSubmitResponse(
            success=True,
            standard_id=mastery.standard_id,
            proficiency=mastery.proficiency.value,
            evidence_count=mastery.evidence_count,
            message=f"Evidence uploaded to {file_url[:50]}... Proficiency: {mastery.proficiency.value}",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"[Standards] Evidence upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload evidence: {str(e)}")
    finally:
        await file.close()


@router.post("/match", response_model=StandardsMatchResponse)
async def match_content_to_standards(
    request: StandardsMatchRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Semantic search for OAS standards matching lesson content.
    
    Uses Hippocampus (pgvector) embeddings to find relevant standards.
    Called by: PedagogyAgent when generating lessons
    
    Example:
        POST /api/standards/match
        {
            "content": "Solve 7th-grade equations with variables on both sides",
            "track": "APPLIED_MATHEMATICS",
            "grade": 7
        }
    """
    mapper = StandardsMapper(db)
    
    try:
        standards = await mapper.match_lesson_to_standards(
            lesson_content=request.content,
            track=request.track,
            grade=request.grade,
            top_k=request.top_k,
        )
        
        return StandardsMatchResponse(
            standards=[
                StandardMatchResult(
                    code=s.code,
                    subject=s.subject.value,
                    grade=s.grade,
                    description=s.description[:200] + "..." if len(s.description) > 200 else s.description,
                    confidence=round(s.confidence, 3),
                )
                for s in standards
            ],
            query_track=request.track,
            query_grade=request.grade,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Standards matching failed: {str(e)}")


@router.get("/progress/{student_id}", response_model=StandardsProgressResponse)
async def get_student_standards_progress(
    student_id: str,
    subject: Optional[str] = Query(None, description="Filter by subject (MATH, ELA, etc.)"),
    db: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Get comprehensive OAS standards progress for a student.
    
    Returns:
    - By-subject breakdown with proficiency distribution
    - Saturation percentage (% of standards at understanding/extending)
    - Gap standards needing attention
    
    Called by: CreditDashboard, Parent Dashboard
    """
    # Security check
    if student_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot view other student's progress")
    
    mapper = StandardsMapper(db)
    
    subject_enum = None
    if subject:
        try:
            subject_enum = StandardsSubject(subject.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid subject: {subject}")
    
    try:
        report = await mapper.get_student_standards_progress(
            student_id=student_id,
            pg_session=db,
            subject=subject_enum,
        )
        
        return StandardsProgressResponse(
            student_id=report.student_id,
            by_subject=[
                SubjectProgressItem(
                    subject=s.subject,
                    total_standards=s.total_standards,
                    developing=s.standards_by_proficiency["developing"],
                    approaching=s.standards_by_proficiency["approaching"],
                    understanding=s.standards_by_proficiency["understanding"],
                    extending=s.standards_by_proficiency["extending"],
                    saturation_percentage=s.saturation_percentage,
                    gap_standards=s.gap_standards,
                )
                for s in report.by_subject.values()
            ],
            total_standards=report.total_standards,
            mastered_standards=report.mastered_standards,
            overall_saturation=report.overall_saturation,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/gaps/{student_id}", response_model=LearningGapsResponse)
async def identify_learning_gaps(
    student_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Identify learning gaps and recommend Daily Bread content.
    
    The "Gap Filler Loop" — finds lowest-saturation subject and suggests
    prioritized standards to address.
    
    Called by: Daily Bread generator for personalized prompts
    """
    # Security check
    if student_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot view other student's gaps")
    
    mapper = StandardsMapper(db)
    
    try:
        report = await mapper.get_student_standards_progress(
            student_id=student_id,
            pg_session=db,
        )
        
        if not report.by_subject:
            return LearningGapsResponse(
                student_id=student_id,
                priority_subject="MATH",
                saturation=0.0,
                gap_standards=[],
                suggested_daily_bread="Start with foundational math concepts.",
            )
        
        # Find lowest saturation subject
        lowest_subject = min(
            report.by_subject.values(),
            key=lambda s: s.saturation_percentage,
        )
        
        # Build gap standards with reasons
        gap_standards = []
        for std_id in lowest_subject.gap_standards[:5]:
            gap_standards.append(GapStandard(
                standard_id=std_id,
                reason=f"Prerequisite for {lowest_subject.subject} mastery",
            ))
        
        # Generate Daily Bread suggestion
        daily_bread = (
            f"Let's focus on {lowest_subject.subject} today. "
            f"You have {len(lowest_subject.gap_standards)} standards to strengthen. "
            "Ready to practice with a homestead example?"
        )
        
        return LearningGapsResponse(
            student_id=student_id,
            priority_subject=lowest_subject.subject,
            saturation=lowest_subject.saturation_percentage,
            gap_standards=gap_standards,
            suggested_daily_bread=daily_bread,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to identify gaps: {str(e)}")


@router.get("/tracks/{track}")
async def get_standards_for_track(
    track: str,
    grade_min: Optional[int] = Query(None),
    grade_max: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get all OAS standards mapped to a specific track.
    
    Called by: PedagogyAgent to inject standards into lesson context
    """
    grade_range = None
    if grade_min is not None and grade_max is not None:
        grade_range = (grade_min, grade_max)
    
    mapper = StandardsMapper(db)
    
    try:
        standards = await mapper.get_standards_for_track(track, grade_range)
        return {
            "track": track,
            "count": len(standards),
            "standards": [
                {
                    "code": s.code,
                    "subject": s.subject.value,
                    "grade": s.grade,
                    "description": s.description[:150] + "..." if len(s.description) > 150 else s.description,
                }
                for s in standards
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get standards: {str(e)}")
