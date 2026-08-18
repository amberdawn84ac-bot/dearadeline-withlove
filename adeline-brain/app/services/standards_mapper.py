"""
StandardsMapper — Production-ready OAS integration service.

Provides:
- Semantic search via Hippocampus (pgvector) for standard matching
- Mastery tracking with 4-level OAS proficiency (developing→extending)
- Evidence validation and recording
- Graduation readiness analytics

OAS is an overlay (not controlling), but metadata enriches transcripts.
"""
from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field

import openai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.curriculum_graph import curriculum_graph

logger = logging.getLogger(__name__)

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536


class OASProficiencyLevel(str, Enum):
    """Oklahoma Academic Standards 4-level proficiency scale."""
    DEVELOPING = "developing"      # 0-49% mastery - Student identifies concepts
    APPROACHING = "approaching"    # 50-74% mastery - Applies with guidance
    UNDERSTANDING = "understanding" # 75-89% mastery - Independent application
    EXTENDING = "extending"        # 90-100% mastery - Can teach/create examples


class StandardsSubject(str, Enum):
    ELA = "ELA"
    MATH = "MATH"
    SCIENCE = "SCIENCE"
    SOCIAL_STUDIES = "SOCIAL_STUDIES"
    HEALTH = "HEALTH"
    WORLD_LANGUAGES = "WORLD_LANGUAGES"
    INFO_LIT = "INFO_LIT"


@dataclass
class OASStandard:
    """Represents an Oklahoma Academic Standard."""
    code: str
    subject: StandardsSubject
    grade: int
    grade_band: str
    strand: str
    description: str
    track: str
    lesson_hook: str = ""
    homestead_adaptation: str = ""
    difficulty: str = "EMERGING"
    confidence: float = 0.0


@dataclass
class MasteryEvidence:
    """Evidence submitted to claim standard mastery."""
    evidence_type: str  # "quiz", "photo", "video", "project", "discussion"
    score: Optional[float] = None  # 0-100 for quiz scores
    file_url: Optional[str] = None  # For photo/video evidence
    description: str = ""
    submitted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StandardMastery:
    """Student's mastery record for a specific OAS standard."""
    student_id: str
    standard_id: str
    subject: StandardsSubject
    grade: int
    proficiency: OASProficiencyLevel
    evidence_count: int
    last_evidence_at: Optional[datetime]
    last_assessed_at: datetime


@dataclass
class StandardsProgressReport:
    """Aggregated standards progress for a student."""
    student_id: str
    by_subject: dict[str, SubjectProgress]
    total_standards: int
    mastered_standards: int  # UNDERSTANDING + EXTENDING
    overall_saturation: float


@dataclass
class SubjectProgress:
    """Progress within a single subject."""
    subject: str
    total_standards: int
    standards_by_proficiency: dict[str, int]
    saturation_percentage: float
    gap_standards: list[str]  # Standards needing attention


# Track to subject mapping
TRACK_TO_SUBJECT: dict[str, StandardsSubject] = {
    "CREATION_SCIENCE": StandardsSubject.SCIENCE,
    "HEALTH_NATUROPATHY": StandardsSubject.HEALTH,
    "HOMESTEADING": StandardsSubject.SCIENCE,
    "GOVERNMENT_ECONOMICS": StandardsSubject.SOCIAL_STUDIES,
    "JUSTICE_CHANGEMAKING": StandardsSubject.SOCIAL_STUDIES,
    "DISCIPLESHIP": StandardsSubject.SOCIAL_STUDIES,
    "TRUTH_HISTORY": StandardsSubject.SOCIAL_STUDIES,
    "ENGLISH_LITERATURE": StandardsSubject.ELA,
    "APPLIED_MATHEMATICS": StandardsSubject.MATH,
    "CREATIVE_ECONOMY": StandardsSubject.ELA,
}


# Small deterministic registry used by synchronous callers such as the credit
# ledger.  The richer StandardsMapper API below remains the source for database
# and embedding-backed matches; these entries provide a reliable, offline
# fallback for the subjects currently represented in the curriculum.
OAS_STANDARDS_REGISTRY: dict[str, OASStandard] = {
    "OK-ELA-8.R.1": OASStandard(
        code="OK-ELA-8.R.1", subject=StandardsSubject.ELA, grade=8,
        grade_band="6-8", strand="Reading",
        description="Students will identify and analyze main idea and supporting details.",
        track="ENGLISH_LITERATURE",
    ),
    "OK-ELA-HS.R.2": OASStandard(
        code="OK-ELA-HS.R.2", subject=StandardsSubject.ELA, grade=9,
        grade_band="9-12", strand="Reading",
        description="Students will analyze author's purpose and craft.",
        track="ENGLISH_LITERATURE",
    ),
    "OK-SCIENCE-8.LS.1": OASStandard(
        code="OK-SCIENCE-8.LS.1", subject=StandardsSubject.SCIENCE, grade=8,
        grade_band="6-8", strand="Life Science",
        description="Students will understand the relationship between structure and function.",
        track="CREATION_SCIENCE",
    ),
    "OK-MATH-HS.A.1": OASStandard(
        code="OK-MATH-HS.A.1", subject=StandardsSubject.MATH, grade=9,
        grade_band="9-12", strand="Algebra",
        description="Students will solve linear and quadratic equations.",
        track="APPLIED_MATHEMATICS",
    ),
    "OK-SOCIAL-STUDIES-HS.1": OASStandard(
        code="OK-SOCIAL-STUDIES-HS.1", subject=StandardsSubject.SOCIAL_STUDIES,
        grade=9, grade_band="9-12", strand="History",
        description="Students will analyze major events in United States history.",
        track="TRUTH_HISTORY",
    ),
}


def get_track_subject(track: str) -> Optional[StandardsSubject]:
    """Return the OAS subject associated with a curriculum track."""
    return TRACK_TO_SUBJECT.get(track)


def lookup_oas_standard(code: str) -> Optional[OASStandard]:
    """Look up a standard available to the deterministic mapper."""
    return OAS_STANDARDS_REGISTRY.get(code)


def infer_oas_confidence(content: str, oas_code: str) -> float:
    """Estimate a transparent keyword-overlap score for an OAS standard."""
    if not content:
        return 0.0
    standard = lookup_oas_standard(oas_code)
    if standard is None:
        return 0.0

    content_lower = content.lower()
    keywords = standard.description.lower().split()
    matches = sum(1 for keyword in keywords if len(keyword) > 3 and keyword in content_lower)
    return min(1.0, matches / max(1, len(keywords)))


def map_lesson_to_oas(
    track: str,
    content: str,
    grade_band: str = "9-12",
) -> list[OASStandard]:
    """Synchronously map lesson text for ledger and transcript enrichment."""
    subject = get_track_subject(track)
    if subject is None:
        return []

    matches = []
    for code, standard in OAS_STANDARDS_REGISTRY.items():
        if standard.subject != subject or standard.grade_band != grade_band:
            continue
        confidence = infer_oas_confidence(content, code)
        if confidence > 0.3:
            matches.append(OASStandard(
                code=standard.code,
                subject=standard.subject,
                grade=standard.grade,
                grade_band=standard.grade_band,
                strand=standard.strand,
                description=standard.description,
                track=track,
                confidence=confidence,
            ))
    return sorted(matches, key=lambda standard: standard.confidence, reverse=True)


def validate_oas_code(code: str) -> bool:
    """Return whether a code exists in the deterministic registry."""
    return code in OAS_STANDARDS_REGISTRY


def _score_to_proficiency(score: float, evidence_type: str) -> OASProficiencyLevel:
    """Convert numerical score to OAS proficiency level."""
    if evidence_type == "quiz":
        if score >= 90:
            return OASProficiencyLevel.EXTENDING
        elif score >= 75:
            return OASProficiencyLevel.UNDERSTANDING
        elif score >= 50:
            return OASProficiencyLevel.APPROACHING
        else:
            return OASProficiencyLevel.DEVELOPING
    else:  # photo/video/project
        return OASProficiencyLevel.UNDERSTANDING  # Requires human review for extending


async def _embed(text_input: str) -> list[float]:
    """Generate embedding for semantic search."""
    client = openai.AsyncOpenAI()
    try:
        resp = await client.embeddings.create(
            model=EMBED_MODEL,
            input=text_input,
        )
        return resp.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise


class StandardsMapper:
    """
    Production-ready OAS standards mapping and mastery tracking.
    """

    def __init__(self, pg_session: Optional[AsyncSession] = None):
        self.pg_session = pg_session

    async def match_lesson_to_standards(
        self,
        lesson_content: str,
        track: str,
        grade: int,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[OASStandard]:
        """
        Semantic search for OAS standards matching lesson content.
        Uses Hippocampus (pgvector) for fast similarity matching.
        """
        if not self.pg_session:
            raise RuntimeError("PostgreSQL session required for semantic search")

        query_embedding = await _embed(lesson_content)

        # Search within track-specific documents
        result = await self.pg_session.execute(
            text("""
                SELECT 
                    source_title,
                    chunk,
                    track,
                    1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM hippocampus_documents
                WHERE track = :track
                  AND source_title LIKE 'OAS Standard%'
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """),
            {
                "embedding": str(query_embedding),
                "track": track,
                "limit": top_k * 2,  # Fetch extra for filtering
            },
        )

        rows = result.mappings().all()
        standards = []

        for row in rows:
            score = float(row["score"])
            if score < similarity_threshold:
                continue

            # Parse standard code from title
            source_title = row["source_title"]
            if "OAS Standard" in source_title:
                code = source_title.replace("OAS Standard ", "")
                standards.append(OASStandard(
                    code=code,
                    subject=TRACK_TO_SUBJECT.get(track, StandardsSubject.ELA),
                    grade=grade,
                    grade_band=self._grade_to_band(grade),
                    strand="",
                    description=row["chunk"],
                    track=track,
                    confidence=score,
                ))

        return sorted(standards, key=lambda s: s.confidence, reverse=True)[:top_k]

    def _grade_to_band(self, grade: int) -> str:
        """Convert grade number to OAS band."""
        if grade <= 2:
            return "k2"
        elif grade <= 5:
            return "35"
        elif grade <= 8:
            return "68"
        else:
            return "912"

    async def get_standards_for_track(
        self,
        track: str,
        grade_range: Optional[tuple[int, int]] = None,
    ) -> list[OASStandard]:
        """
        Retrieve all OAS standards mapped to a specific track.
        """
        try:
            rows = await curriculum_graph.get_standards_for_track(
                track,
                grade_min=grade_range[0] if grade_range else None,
                grade_max=grade_range[1] if grade_range else None,
            )

            standards = []
            for row in rows:
                grade = row.get("grade", 1)
                standards.append(OASStandard(
                    code=row["code"],
                    subject=TRACK_TO_SUBJECT.get(track, StandardsSubject.ELA),
                    grade=grade,
                    grade_band=self._grade_to_band(grade),
                    strand=row.get("strand", ""),
                    description=row.get("description", ""),
                    track=track,
                ))

            return standards
        except Exception as e:
            logger.warning(f"Curriculum standards query failed: {e}")
            return []

    async def get_next_logical_standards(
        self,
        standard_id: str,
        student_id: str,
    ) -> list[OASStandard]:
        """
        Query standards progression relationships to find the next standards
        to master after completing the given standard.

        Example: "Multiplication" → "Division" → "Fractions"

        Returns standards that:
        1. Are directly fed by the given standard (FEEDS_INTO)
        2. Have not yet been mastered by the student
        3. Have all their prerequisites already mastered
        """
        try:
            # Find standards that this standard feeds into
            rows = await curriculum_graph.get_next_standards(standard_id, student_id, limit=5)

            standards = []
            for row in rows:
                standards.append(OASStandard(
                    code=row["code"],
                    subject=self._parse_subject_from_code(row["code"]),
                    grade=row.get("grade", 1),
                    grade_band=self._grade_to_band(row.get("grade", 1)),
                    strand=row.get("strand", ""),
                    description=row.get("description", ""),
                    track=row.get("track", "TRUTH_HISTORY"),
                ))

            logger.info(
                f"[StandardsMapper] Found {len(standards)} logical next standards "
                f"after {standard_id} for student {student_id[:8]}..."
            )
            return standards

        except Exception as e:
            logger.warning(f"Standards progression query failed: {e}")
            return []

    async def get_prerequisites_for_standard(
        self,
        standard_id: str,
        student_id: str,
    ) -> tuple[list[OASStandard], list[OASStandard]]:
        """
        Get prerequisites for a standard, split into mastered and unmastered.

        Returns: (unmastered_prereqs, mastered_prereqs)
        """
        try:
            rows = await curriculum_graph.get_standard_prerequisites(standard_id, student_id)

            unmastered = []
            mastered = []

            for row in rows:
                std = OASStandard(
                    code=row["code"],
                    subject=self._parse_subject_from_code(row["code"]),
                    grade=row.get("grade", 1),
                    grade_band=self._grade_to_band(row.get("grade", 1)),
                    strand=row.get("strand", ""),
                    description=row.get("description", ""),
                    track=row.get("track", "TRUTH_HISTORY"),
                )
                if row.get("is_mastered", False):
                    mastered.append(std)
                else:
                    unmastered.append(std)

            return unmastered, mastered

        except Exception as e:
            logger.warning(f"Standards prerequisites query failed: {e}")
            return [], []

    async def record_mastery_evidence(
        self,
        student_id: str,
        standard_id: str,
        evidence: MasteryEvidence,
        pg_session: AsyncSession,
    ) -> StandardMastery:
        """
        Record evidence of mastery for an OAS standard.
        Updates proficiency level based on evidence quality.
        """
        proficiency = _score_to_proficiency(
            evidence.score or 75, evidence.evidence_type
        )

        # Get subject from standard_id (e.g., "OAS.MATH.7.N.1" -> MATH)
        subject = self._parse_subject_from_code(standard_id)
        grade = self._parse_grade_from_code(standard_id)

        # Upsert StandardMastery record
        await pg_session.execute(
            text("""
                INSERT INTO "StandardMastery" (
                    id, "studentId", "standardId", subject, grade, proficiency,
                    "evidenceCount", "lastEvidenceAt", "lastAssessedAt"
                )
                VALUES (
                    gen_random_uuid(), :student_id, :standard_id, :subject, :grade,
                    :proficiency, 1, :evidence_at, NOW()
                )
                ON CONFLICT ("studentId", "standardId")
                DO UPDATE SET
                    proficiency = CASE
                        WHEN :proficiency = 'EXTENDING' OR "StandardMastery".proficiency = 'EXTENDING'
                        THEN 'EXTENDING'::"OASProficiencyLevel"
                        WHEN :proficiency = 'UNDERSTANDING' OR "StandardMastery".proficiency = 'UNDERSTANDING'
                        THEN 'UNDERSTANDING'::"OASProficiencyLevel"
                        WHEN :proficiency = 'APPROACHING' OR "StandardMastery".proficiency = 'APPROACHING'
                        THEN 'APPROACHING'::"OASProficiencyLevel"
                        ELSE 'DEVELOPING'::"OASProficiencyLevel"
                    END,
                    "evidenceCount" = "StandardMastery"."evidenceCount" + 1,
                    "lastEvidenceAt" = :evidence_at,
                    "lastAssessedAt" = NOW()
            """),
            {
                "student_id": student_id,
                "standard_id": standard_id,
                "subject": subject.value,
                "grade": grade,
                "proficiency": proficiency.name,
                "evidence_at": evidence.submitted_at,
            },
        )

        # Invalidate graduation report cache
        await self._invalidate_cache(student_id)

        return StandardMastery(
            student_id=student_id,
            standard_id=standard_id,
            subject=subject,
            grade=grade,
            proficiency=proficiency,
            evidence_count=1,  # Will be updated on next fetch
            last_evidence_at=evidence.submitted_at,
            last_assessed_at=datetime.utcnow(),
        )

    def _parse_subject_from_code(self, code: str) -> StandardsSubject:
        """Extract subject from OAS code (e.g., OAS.MATH.7.N.1 -> MATH)."""
        parts = code.split(".")
        if len(parts) >= 2:
            subject_map = {
                "MATH": StandardsSubject.MATH,
                "ELA": StandardsSubject.ELA,
                "SCI": StandardsSubject.SCIENCE,
                "SS": StandardsSubject.SOCIAL_STUDIES,
                "HLT": StandardsSubject.HEALTH,
            }
            return subject_map.get(parts[1].upper(), StandardsSubject.ELA)
        return StandardsSubject.ELA

    def _parse_grade_from_code(self, code: str) -> int:
        """Extract grade from OAS code (e.g., OAS.MATH.7.N.1 -> 7)."""
        parts = code.split(".")
        if len(parts) >= 3:
            try:
                return int(parts[2])
            except ValueError:
                pass
        return 1

    async def get_student_standards_progress(
        self,
        student_id: str,
        pg_session: AsyncSession,
        subject: Optional[StandardsSubject] = None,
    ) -> StandardsProgressReport:
        """
        Generate comprehensive standards progress report for a student.
        """
        where_clause = "WHERE \"studentId\" = :student_id"
        params = {"student_id": student_id}
        if subject:
            where_clause += " AND subject = :subject"
            params["subject"] = subject.value

        result = await pg_session.execute(
            text(f"""
                SELECT 
                    subject,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE proficiency = 'DEVELOPING') as developing,
                    COUNT(*) FILTER (WHERE proficiency = 'APPROACHING') as approaching,
                    COUNT(*) FILTER (WHERE proficiency = 'UNDERSTANDING') as understanding,
                    COUNT(*) FILTER (WHERE proficiency = 'EXTENDING') as extending
                FROM "StandardMastery"
                {where_clause}
                GROUP BY subject
            """),
            params,
        )

        by_subject = {}
        total_standards = 0
        mastered_standards = 0

        for row in result.mappings():
            subj = row["subject"]
            total = row["total"]
            understanding = row["understanding"]
            extending = row["extending"]
            mastered = understanding + extending

            by_subject[subj] = SubjectProgress(
                subject=subj,
                total_standards=total,
                standards_by_proficiency={
                    "developing": row["developing"],
                    "approaching": row["approaching"],
                    "understanding": understanding,
                    "extending": extending,
                },
                saturation_percentage=round(mastered / total * 100, 2) if total > 0 else 0,
                gap_standards=[],  # Populated below
            )

            total_standards += total
            mastered_standards += mastered

        # Calculate gaps (standards not yet mastered)
        for subj, progress in by_subject.items():
            gaps_result = await pg_session.execute(
                text("""
                    SELECT s.id as standard_id
                    FROM (
                        SELECT id FROM "OASStandard" WHERE subject = :subject
                    ) s
                    LEFT JOIN "StandardMastery" m
                        ON m."standardId" = s.id AND m."studentId" = :student_id
                    WHERE m.proficiency IS NULL 
                       OR m.proficiency IN ('DEVELOPING', 'APPROACHING')
                    LIMIT 10
                """),
                {"subject": subj, "student_id": student_id},
            )
            progress.gap_standards = [row["standard_id"] for row in gaps_result.mappings()]

        overall_saturation = (
            round(mastered_standards / total_standards * 100, 2)
            if total_standards > 0 else 0
        )

        return StandardsProgressReport(
            student_id=student_id,
            by_subject=by_subject,
            total_standards=total_standards,
            mastered_standards=mastered_standards,
            overall_saturation=overall_saturation,
        )

    async def _invalidate_cache(self, student_id: str) -> None:
        """Invalidate graduation report cache for student."""
        if self.pg_session:
            await self.pg_session.execute(
                text("""
                    DELETE FROM graduation_readiness_cache 
                    WHERE student_id = :student_id
                """),
                {"student_id": student_id},
            )


# Convenience exports
async def match_lesson_content(
    content: str,
    track: str,
    grade: int,
    pg_session: AsyncSession,
) -> list[OASStandard]:
    """Convenience function for matching lesson content to standards."""
    mapper = StandardsMapper(pg_session)
    return await mapper.match_lesson_to_standards(content, track, grade)


async def submit_evidence(
    student_id: str,
    standard_id: str,
    evidence: MasteryEvidence,
    pg_session: AsyncSession,
) -> StandardMastery:
    """Convenience function for submitting mastery evidence."""
    mapper = StandardsMapper(pg_session)
    return await mapper.record_mastery_evidence(student_id, standard_id, evidence, pg_session)
