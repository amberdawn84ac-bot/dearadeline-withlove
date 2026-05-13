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

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

import openai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.neo4j_client import neo4j_client
from app.config import POSTGRES_DSN

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
            rows = await neo4j_client.run(
                """
                MATCH (s:OASStandard)-[:MAPS_TO_TRACK]->(t:Track {name: $track})
                RETURN s.id AS code, s.standard_text AS description,
                       s.grade AS grade, s.strand AS strand
                ORDER BY s.grade, s.strand
                """,
                {"track": track},
            )

            standards = []
            for row in rows:
                grade = row.get("grade", 1)
                if grade_range and not (grade_range[0] <= grade <= grade_range[1]):
                    continue

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
            logger.warning(f"Neo4j query failed: {e}")
            return []

    async def get_next_logical_standards(
        self,
        standard_id: str,
        student_id: str,
    ) -> list[OASStandard]:
        """
        Query Neo4j for FEEDS_INTO relationships to find the next standards
        to master after completing the given standard.

        Example: "Multiplication" → "Division" → "Fractions"

        Returns standards that:
        1. Are directly fed by the given standard (FEEDS_INTO)
        2. Have not yet been mastered by the student
        3. Have all their prerequisites already mastered
        """
        try:
            # Find standards that this standard feeds into
            rows = await neo4j_client.run(
                """
                MATCH (current:OASStandard {id: $standard_id})-[:FEEDS_INTO]->(next:OASStandard)
                MATCH (next)-[:MAPS_TO_TRACK]->(t:Track)
                OPTIONAL MATCH (next)<-[:PREREQUISITE_FOR]-(prereq:OASStandard)
                OPTIONAL MATCH (st:Student {id: $student_id})-[:MASTERED]->(prereq)
                WITH next, t, 
                     collect(DISTINCT prereq.id) as prereq_ids,
                     collect(DISTINCT CASE WHEN st.id IS NOT NULL THEN prereq.id END) as mastered_prereqs
                WHERE NOT EXISTS {
                    MATCH (:Student {id: $student_id})-[:MASTERED]->(next)
                }
                AND ALL(p IN prereq_ids WHERE p IN mastered_prereqs OR p = $standard_id)
                RETURN next.id as code,
                       next.standard_text as description,
                       next.grade as grade,
                       next.strand as strand,
                       t.name as track,
                       size(prereq_ids) as prereq_count
                ORDER BY next.grade, prereq_count
                LIMIT 5
                """,
                {"standard_id": standard_id, "student_id": student_id},
            )

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
            logger.warning(f"Neo4j prerequisite query failed: {e}")
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
            rows = await neo4j_client.run(
                """
                MATCH (s:OASStandard {id: $standard_id})<-[:PREREQUISITE_FOR]-(prereq:OASStandard)
                MATCH (prereq)-[:MAPS_TO_TRACK]->(t:Track)
                OPTIONAL MATCH (:Student {id: $student_id})-[:MASTERED]->(prereq)
                WITH prereq, t, EXISTS((:Student {id: $student_id})-[:MASTERED]->(prereq)) as is_mastered
                RETURN prereq.id as code,
                       prereq.standard_text as description,
                       prereq.grade as grade,
                       prereq.strand as strand,
                       t.name as track,
                       is_mastered
                ORDER BY prereq.grade
                """,
                {"standard_id": standard_id, "student_id": student_id},
            )

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
            logger.warning(f"Neo4j prerequisites query failed: {e}")
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
                        WHEN :proficiency = 'extending' OR "StandardMastery".proficiency = 'extending'
                        THEN 'extending'
                        WHEN :proficiency = 'understanding' OR "StandardMastery".proficiency = 'understanding'
                        THEN 'understanding'
                        WHEN :proficiency = 'approaching' OR "StandardMastery".proficiency = 'approaching'
                        THEN 'approaching'
                        ELSE 'developing'
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
                "proficiency": proficiency.value,
                "evidence_at": evidence.submitted_at,
            },
        )

        # Update Neo4j mastery relationship
        try:
            await neo4j_client.run(
                """
                MERGE (st:Student {id: $student_id})
                MERGE (s:OASStandard {id: $standard_id})
                MERGE (st)-[m:MASTERED]->(s)
                SET m.proficiency = $proficiency,
                    m.evidence_count = coalesce(m.evidence_count, 0) + 1,
                    m.last_assessed = datetime()
                """,
                {
                    "student_id": student_id,
                    "standard_id": standard_id,
                    "proficiency": proficiency.value,
                },
            )
        except Exception as e:
            logger.warning(f"Neo4j mastery update failed (non-fatal): {e}")

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
                    COUNT(*) FILTER (WHERE proficiency = 'developing') as developing,
                    COUNT(*) FILTER (WHERE proficiency = 'approaching') as approaching,
                    COUNT(*) FILTER (WHERE proficiency = 'understanding') as understanding,
                    COUNT(*) FILTER (WHERE proficiency = 'extending') as extending
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
                       OR m.proficiency IN ('developing', 'approaching')
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
