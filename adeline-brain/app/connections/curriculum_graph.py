"""Postgres-backed curriculum relationship store.

This is the single source of truth for curriculum concepts, prerequisites,
cross-track relationships, standards progression, and student mastery.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from app.connections.postgres import _get_session_factory

logger = logging.getLogger(__name__)


class CurriculumGraph:
    async def connect(self) -> None:
        """Verify the migrated curriculum tables are available."""
        async with _get_session_factory()() as session:
            await session.execute(text('SELECT 1 FROM "CurriculumConcept" LIMIT 1'))
        logger.info("[CurriculumGraph] Postgres relationship store connected")

    async def close(self) -> None:
        return None

    async def seed_catalog(
        self,
        concepts: list[tuple],
        prerequisites: list[tuple],
        track_links: list[tuple[str, str]],
    ) -> None:
        """Idempotently seed the complete small concept graph in one transaction."""
        concept_rows = [{
            "id": row[0], "title": row[1], "description": row[2],
            "track": row[3], "difficulty": row[4], "standard_code": row[5] or "",
            "grade_band": row[6] or "", "is_primary_source": bool(row[7]),
            "tags": [],
        } for row in concepts]
        prerequisite_rows = [{
            "concept_id": row[0], "prerequisite_id": row[1], "weight": row[2],
        } for row in prerequisites]
        track_rows = [{"from_track": row[0], "to_track": row[1]} for row in track_links]
        async with _get_session_factory()() as session:
            await session.execute(text('''
                INSERT INTO "CurriculumConcept"
                    (id, title, description, track, difficulty, "standardCode",
                     "gradeBand", tags, "isPrimarySource", "createdAt", "updatedAt")
                VALUES
                    (:id, :title, :description, CAST(:track AS "Track"), :difficulty,
                     :standard_code, :grade_band, :tags, :is_primary_source, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title, description = EXCLUDED.description,
                    track = EXCLUDED.track, difficulty = EXCLUDED.difficulty,
                    "standardCode" = EXCLUDED."standardCode",
                    "gradeBand" = EXCLUDED."gradeBand", tags = EXCLUDED.tags,
                    "isPrimarySource" = EXCLUDED."isPrimarySource", "updatedAt" = NOW()
            '''), concept_rows)
            if prerequisite_rows:
                await session.execute(text('''
                    INSERT INTO "CurriculumConceptPrerequisite"
                        ("conceptId", "prerequisiteId", weight)
                    VALUES (:concept_id, :prerequisite_id, :weight)
                    ON CONFLICT ("conceptId", "prerequisiteId")
                    DO UPDATE SET weight = EXCLUDED.weight
                '''), prerequisite_rows)
            if track_rows:
                await session.execute(text('''
                    INSERT INTO "CurriculumTrackLink" ("fromTrack", "toTrack")
                    VALUES (CAST(:from_track AS "Track"), CAST(:to_track AS "Track"))
                    ON CONFLICT DO NOTHING
                '''), track_rows)
            await session.commit()

    async def upsert_concept(
        self,
        concept_id: str,
        title: str,
        description: str,
        track: str,
        difficulty: str,
        standard_code: str = "",
        grade_band: str = "",
        tags: Optional[list[str]] = None,
        is_primary_source: bool = False,
    ) -> None:
        async with _get_session_factory()() as session:
            await session.execute(text('''
                INSERT INTO "CurriculumConcept"
                    (id, title, description, track, difficulty, "standardCode",
                     "gradeBand", tags, "isPrimarySource", "createdAt", "updatedAt")
                VALUES
                    (:id, :title, :description, CAST(:track AS "Track"), :difficulty,
                     :standard_code, :grade_band, :tags, :is_primary_source, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    track = EXCLUDED.track,
                    difficulty = EXCLUDED.difficulty,
                    "standardCode" = EXCLUDED."standardCode",
                    "gradeBand" = EXCLUDED."gradeBand",
                    tags = EXCLUDED.tags,
                    "isPrimarySource" = EXCLUDED."isPrimarySource",
                    "updatedAt" = NOW()
            '''), {
                "id": concept_id, "title": title, "description": description,
                "track": track, "difficulty": difficulty,
                "standard_code": standard_code or "", "grade_band": grade_band or "",
                "tags": tags or [], "is_primary_source": is_primary_source,
            })
            await session.commit()

    async def add_prerequisite(
        self, concept_id: str, prerequisite_id: str, weight: float = 1.0
    ) -> None:
        async with _get_session_factory()() as session:
            await session.execute(text('''
                INSERT INTO "CurriculumConceptPrerequisite"
                    ("conceptId", "prerequisiteId", weight)
                VALUES (:concept_id, :prerequisite_id, :weight)
                ON CONFLICT ("conceptId", "prerequisiteId")
                DO UPDATE SET weight = EXCLUDED.weight
            '''), {"concept_id": concept_id, "prerequisite_id": prerequisite_id, "weight": weight})
            await session.commit()

    async def add_cross_track_link(self, from_track: str, to_track: str) -> None:
        async with _get_session_factory()() as session:
            await session.execute(text('''
                INSERT INTO "CurriculumTrackLink" ("fromTrack", "toTrack")
                VALUES (CAST(:from_track AS "Track"), CAST(:to_track AS "Track"))
                ON CONFLICT DO NOTHING
            '''), {"from_track": from_track, "to_track": to_track})
            await session.commit()

    async def upsert_standard(self, standard_id: str, properties: dict, track: str) -> None:
        grade = properties.get("grade", 0)
        description = properties.get("standard_text") or properties.get("text") or properties.get("description") or ""
        async with _get_session_factory()() as session:
            await session.execute(text('''
                INSERT INTO "OASStandard"
                    (id, code, subject, grade, "gradeBand", strand, description, track,
                     "lessonHook", "homesteadAdaptation", difficulty,
                     "progressionLane", "progressionMode", "progressionOrdinal",
                     "progressionSourceTitle", "progressionSourceUrl", "progressionSourceVersion",
                     "progressionEvidenceNote", "progressionReviewStatus",
                     "progressionParentId", "progressionIsTerminal", "createdAt")
                VALUES
                    (gen_random_uuid(), :code, :subject, :grade, :grade_band, :strand,
                     :description, :track, :lesson_hook, :homestead, :difficulty,
                     :progression_lane, :progression_mode, :progression_ordinal,
                     :progression_source_title, :progression_source_url, :progression_source_version,
                     :progression_evidence_note, :progression_review_status,
                     :progression_parent_id, :progression_is_terminal, NOW())
                ON CONFLICT (code) DO UPDATE SET
                    subject = EXCLUDED.subject,
                    grade = EXCLUDED.grade,
                    "gradeBand" = EXCLUDED."gradeBand",
                    strand = EXCLUDED.strand,
                    description = EXCLUDED.description,
                    track = EXCLUDED.track,
                    "lessonHook" = EXCLUDED."lessonHook",
                    "homesteadAdaptation" = EXCLUDED."homesteadAdaptation",
                    difficulty = EXCLUDED.difficulty,
                    "progressionLane" = EXCLUDED."progressionLane",
                    "progressionMode" = EXCLUDED."progressionMode",
                    "progressionOrdinal" = EXCLUDED."progressionOrdinal",
                    "progressionSourceTitle" = EXCLUDED."progressionSourceTitle",
                    "progressionSourceUrl" = EXCLUDED."progressionSourceUrl",
                    "progressionSourceVersion" = EXCLUDED."progressionSourceVersion",
                    "progressionEvidenceNote" = EXCLUDED."progressionEvidenceNote",
                    "progressionReviewStatus" = EXCLUDED."progressionReviewStatus",
                    "progressionParentId" = EXCLUDED."progressionParentId",
                    "progressionIsTerminal" = EXCLUDED."progressionIsTerminal"
            '''), {
                "code": standard_id,
                "subject": properties.get("subject", "ELA"),
                "grade": int(grade) if str(grade).isdigit() else 0,
                "grade_band": properties.get("grade_band", ""),
                "strand": properties.get("strand", ""),
                "description": description,
                "track": track,
                "lesson_hook": properties.get("lesson_hook", ""),
                "homestead": properties.get("homestead_adaptation", ""),
                "difficulty": properties.get("difficulty", "EMERGING"),
                "progression_lane": properties.get("progression_lane", ""),
                "progression_mode": properties.get("progression_mode", "OPEN"),
                "progression_ordinal": int(properties.get("progression_ordinal", 0)),
                "progression_source_title": properties.get("progression_source_title", ""),
                "progression_source_url": properties.get("progression_source_url", ""),
                "progression_source_version": properties.get("progression_source_version", ""),
                "progression_evidence_note": properties.get("progression_evidence_note", ""),
                "progression_review_status": properties.get("progression_review_status", "PLACED"),
                "progression_parent_id": properties.get("progression_parent_id"),
                "progression_is_terminal": bool(properties.get("progression_is_terminal", True)),
            })
            await session.commit()

    async def add_standard_relation(
        self, from_id: str, relation_type: str, to_id: str, weight: float = 1.0,
        *, source_title: str = "", source_url: str = "", source_version: str = "",
        evidence_note: str = "", review_status: str = "PENDING",
    ) -> None:
        async with _get_session_factory()() as session:
            await session.execute(text('''
                INSERT INTO "OASStandardRelation"
                    ("fromStandardId", "relationType", "toStandardId", weight,
                     "sourceTitle", "sourceUrl", "sourceVersion", "evidenceNote",
                     "reviewStatus", "reviewedAt")
                VALUES (:from_id, :relation_type, :to_id, :weight,
                        :source_title, :source_url, :source_version, :evidence_note,
                        :review_status,
                        CASE WHEN :review_status = 'VERIFIED' THEN NOW() ELSE NULL END)
                ON CONFLICT ("fromStandardId", "relationType", "toStandardId")
                DO UPDATE SET weight = EXCLUDED.weight,
                    "sourceTitle" = EXCLUDED."sourceTitle",
                    "sourceUrl" = EXCLUDED."sourceUrl",
                    "sourceVersion" = EXCLUDED."sourceVersion",
                    "evidenceNote" = EXCLUDED."evidenceNote",
                    "reviewStatus" = EXCLUDED."reviewStatus",
                    "reviewedAt" = EXCLUDED."reviewedAt"
            '''), {"from_id": from_id, "relation_type": relation_type,
                    "to_id": to_id, "weight": weight, "source_title": source_title,
                    "source_url": source_url, "source_version": source_version,
                    "evidence_note": evidence_note, "review_status": review_status})
            await session.commit()

    async def record_concept_mastery(
        self, student_id: str, concept_id: str, score: float,
        sealed_at: Optional[str] = None,
    ) -> None:
        sealed = sealed_at or datetime.now(timezone.utc).isoformat()
        async with _get_session_factory()() as session:
            await session.execute(text('''
                INSERT INTO "StudentConceptMastery"
                    ("studentId", "conceptId", score, "sealedAt", "updatedAt")
                VALUES (:student_id, :concept_id, :score, CAST(:sealed_at AS timestamptz), NOW())
                ON CONFLICT ("studentId", "conceptId") DO UPDATE SET
                    score = EXCLUDED.score, "sealedAt" = EXCLUDED."sealedAt", "updatedAt" = NOW()
            '''), {"student_id": student_id, "concept_id": concept_id,
                    "score": score, "sealed_at": sealed})
            await session.commit()

    async def record_standard_mastery(
        self, student_id: str, track: str, standards: list[dict],
        proficiency: str = "DEVELOPING",
    ) -> None:
        allowed = {"DEVELOPING", "APPROACHING", "UNDERSTANDING", "EXTENDING"}
        level = proficiency if proficiency in allowed else "DEVELOPING"
        async with _get_session_factory()() as session:
            for standard in standards:
                standard_id = standard.get("standard_id") or standard.get("code") or ""
                if not standard_id:
                    continue
                grade = standard.get("grade", 0)
                subject = standard.get("subject") or _subject_from_code(standard_id)
                await session.execute(text('''
                    INSERT INTO "StandardMastery"
                        (id, "studentId", "standardId", subject, grade, proficiency,
                         "evidenceCount", "lastEvidenceAt", "lastAssessedAt")
                    VALUES
                        (gen_random_uuid(), :student_id, :standard_id, :subject, :grade,
                         CAST(:proficiency AS "OASProficiencyLevel"), 1, NOW(), NOW())
                    ON CONFLICT ("studentId", "standardId") DO UPDATE SET
                        proficiency = CASE
                            WHEN CAST(EXCLUDED.proficiency AS text) = 'EXTENDING' THEN EXCLUDED.proficiency
                            WHEN CAST("StandardMastery".proficiency AS text) = 'EXTENDING' THEN "StandardMastery".proficiency
                            WHEN CAST(EXCLUDED.proficiency AS text) = 'UNDERSTANDING' THEN EXCLUDED.proficiency
                            WHEN CAST("StandardMastery".proficiency AS text) = 'UNDERSTANDING' THEN "StandardMastery".proficiency
                            WHEN CAST(EXCLUDED.proficiency AS text) = 'APPROACHING' THEN EXCLUDED.proficiency
                            ELSE "StandardMastery".proficiency
                        END,
                        "evidenceCount" = "StandardMastery"."evidenceCount" + 1,
                        "lastEvidenceAt" = NOW(), "lastAssessedAt" = NOW()
                '''), {"student_id": student_id, "standard_id": standard_id,
                        "subject": subject, "grade": int(grade) if str(grade).isdigit() else 0,
                        "proficiency": level})
            await session.commit()

    async def get_concept_graph_for_track(self, track: str) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT c.id, c.title AS name, c.description, c.track::text AS track,
                       c.difficulty, c."standardCode" AS standard_code,
                       c."gradeBand" AS grade_band,
                       COALESCE(array_agg(DISTINCT p."prerequisiteId")
                           FILTER (WHERE p."prerequisiteId" IS NOT NULL), ARRAY[]::text[]) AS prerequisite_ids,
                       COUNT(DISTINCT d."conceptId") AS dependent_count
                FROM "CurriculumConcept" c
                LEFT JOIN "CurriculumConceptPrerequisite" p ON p."conceptId" = c.id
                LEFT JOIN "CurriculumConceptPrerequisite" d ON d."prerequisiteId" = c.id
                WHERE c.track = CAST(:track AS "Track")
                GROUP BY c.id
                ORDER BY c."gradeBand", c.id
            '''), {"track": track})
            return [dict(row) for row in result.mappings().all()]

    async def get_student_concept_mastery(self, student_id: str) -> dict[str, float]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT "conceptId", score FROM "StudentConceptMastery"
                WHERE "studentId" = :student_id
            '''), {"student_id": student_id})
            return {row["conceptId"]: float(row["score"]) for row in result.mappings().all()}

    async def get_mastered_standards(self, student_id: str) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT m."standardId" AS standard_id, m."standardId" AS std_id,
                       COALESCE(s.description, '') AS text,
                       COALESCE(s.grade, m.grade) AS grade,
                       COALESCE(s.track, '') AS track,
                       m.proficiency::text AS proficiency
                FROM "StandardMastery" m
                LEFT JOIN "OASStandard" s ON s.code = m."standardId"
                WHERE m."studentId" = :student_id
                  AND m.proficiency IN ('UNDERSTANDING', 'EXTENDING')
                ORDER BY track, grade, m."standardId"
            '''), {"student_id": student_id})
            return [dict(row) for row in result.mappings().all()]

    async def get_grade_standards(
        self, student_id: str, grade: int, limit: int = 10,
        per_subject_limit: int | None = 6,
    ) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                WITH s AS (
                    SELECT base.*,
                           ROW_NUMBER() OVER (PARTITION BY base.subject ORDER BY base.code) AS subject_rank
                    FROM "OASStandard" base
                    WHERE base.grade = :grade
                      AND base."progressionIsTerminal" = TRUE
                )
                SELECT s.code AS id, s.description, s.grade, s.subject,
                       s.track::text AS track, s.strand, s."lessonHook" AS lesson_hook,
                       s.difficulty, s."progressionLane" AS progression_lane,
                       s."progressionMode" AS progression_mode,
                       s."progressionOrdinal" AS progression_ordinal,
                       s."progressionSourceTitle" AS progression_source_title,
                       s."progressionSourceUrl" AS progression_source_url,
                       s."progressionSourceVersion" AS progression_source_version,
                       s."progressionReviewStatus" AS progression_review_status,
                       NOT EXISTS (
                           SELECT 1
                           FROM "OASStandard" earlier
                           LEFT JOIN "StandardMastery" earlier_mastery
                             ON earlier_mastery."standardId" = earlier.code
                            AND earlier_mastery."studentId" = :student_id
                           WHERE earlier."progressionLane" = s."progressionLane"
                             AND earlier.grade = s.grade
                             AND earlier."progressionIsTerminal" = TRUE
                             AND earlier."progressionOrdinal" < s."progressionOrdinal"
                             AND COALESCE(earlier_mastery.proficiency::text, '')
                                 NOT IN ('UNDERSTANDING', 'EXTENDING')
                       ) AS progression_ready,
                       COALESCE(ARRAY(
                           SELECT relation."fromStandardId"
                           FROM "OASStandardRelation" relation
                           WHERE relation."toStandardId" = s.code
                             AND relation."relationType" = 'PREREQUISITE_FOR'
                             AND relation."reviewStatus" = 'VERIFIED'
                           ORDER BY relation."fromStandardId"
                       ), ARRAY[]::text[]) AS prerequisite_standard_ids,
                       NOT EXISTS (
                           SELECT 1
                           FROM "OASStandardRelation" relation
                           WHERE relation."toStandardId" = s.code
                             AND relation."relationType" = 'PREREQUISITE_FOR'
                             AND relation."reviewStatus" = 'VERIFIED'
                             AND NOT EXISTS (
                                 SELECT 1 FROM "StandardMastery" prerequisite_mastery
                                 WHERE prerequisite_mastery."studentId" = :student_id
                                   AND prerequisite_mastery."standardId" = relation."fromStandardId"
                                   AND prerequisite_mastery.proficiency IN ('UNDERSTANDING', 'EXTENDING')
                             )
                       ) AS prerequisites_met,
                       COALESCE(m.proficiency::text, 'NOT_STARTED') AS proficiency,
                       CASE WHEN m.proficiency IN ('UNDERSTANDING', 'EXTENDING')
                            THEN true ELSE false END AS mastered
                FROM s
                LEFT JOIN "StandardMastery" m
                  ON m."standardId" = s.code AND m."studentId" = :student_id
                WHERE (CAST(:per_subject_limit AS INTEGER) IS NULL
                       OR s.subject_rank <= CAST(:per_subject_limit AS INTEGER))
                ORDER BY s.subject, s."progressionLane", s."progressionOrdinal", s.code LIMIT :limit
            '''), {
                "student_id": student_id, "grade": grade, "limit": limit,
                "per_subject_limit": per_subject_limit,
            })
            return [dict(row) for row in result.mappings().all()]

    async def get_standards_by_codes(self, codes: list[str]) -> list[dict]:
        """Return complete teaching context for planner-assigned standards."""
        if not codes:
            return []
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT code AS standard_id, description AS text, grade, subject,
                       strand, track::text AS track, "lessonHook" AS lesson_hook,
                       'required_plan' AS source_type
                FROM "OASStandard"
                WHERE code = ANY(:codes)
                ORDER BY subject, strand, code
            '''), {"codes": codes})
            return [dict(row) for row in result.mappings().all()]

    async def get_next_standards(self, standard_id: str, student_id: str, limit: int = 5) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT s.code, s.description, s.grade, s.strand, s.track
                FROM "OASStandardRelation" r
                JOIN "OASStandard" s ON s.code = r."toStandardId"
                LEFT JOIN "StandardMastery" own
                  ON own."standardId" = s.code AND own."studentId" = :student_id
                WHERE r."fromStandardId" = :standard_id
                  AND r."relationType" = 'FEEDS_INTO'
                  AND r."reviewStatus" = 'VERIFIED'
                  AND COALESCE(own.proficiency::text, '') NOT IN ('UNDERSTANDING', 'EXTENDING')
                  AND NOT EXISTS (
                    SELECT 1 FROM "OASStandardRelation" prereq
                    WHERE prereq."toStandardId" = s.code
                      AND prereq."relationType" = 'PREREQUISITE_FOR'
                      AND prereq."reviewStatus" = 'VERIFIED'
                      AND prereq."fromStandardId" <> :standard_id
                      AND NOT EXISTS (
                        SELECT 1 FROM "StandardMastery" mastered
                        WHERE mastered."studentId" = :student_id
                          AND mastered."standardId" = prereq."fromStandardId"
                          AND mastered.proficiency IN ('UNDERSTANDING', 'EXTENDING')
                      )
                  )
                ORDER BY s.grade, s.code LIMIT :limit
            '''), {"standard_id": standard_id, "student_id": student_id, "limit": limit})
            return [dict(row) for row in result.mappings().all()]

    async def get_standard_prerequisites(self, standard_id: str, student_id: str) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT s.code, s.description, s.grade, s.strand, s.track,
                       CASE WHEN m.proficiency IN ('UNDERSTANDING', 'EXTENDING')
                            THEN true ELSE false END AS is_mastered
                FROM "OASStandardRelation" r
                JOIN "OASStandard" s ON s.code = r."fromStandardId"
                LEFT JOIN "StandardMastery" m
                  ON m."standardId" = s.code AND m."studentId" = :student_id
                WHERE r."toStandardId" = :standard_id
                  AND r."relationType" = 'PREREQUISITE_FOR'
                  AND r."reviewStatus" = 'VERIFIED'
                ORDER BY s.grade, s.code
            '''), {"standard_id": standard_id, "student_id": student_id})
            return [dict(row) for row in result.mappings().all()]

    async def get_zpd_candidates(self, student_id: str, track: str, limit: int = 5) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT c.id AS concept_id, c.title, c.description, c.track::text AS track,
                       c.difficulty, c."standardCode" AS standard_code,
                       c."gradeBand" AS grade_band,
                       COUNT(DISTINCT dep."conceptId") AS dependent_count,
                       COUNT(DISTINCT prereq."prerequisiteId") AS prereq_count,
                       COALESCE(array_agg(DISTINCT prereq."prerequisiteId")
                           FILTER (WHERE prereq."prerequisiteId" IS NOT NULL), ARRAY[]::text[]) AS prerequisite_ids
                FROM "CurriculumConcept" c
                LEFT JOIN "StudentConceptMastery" own
                  ON own."conceptId" = c.id AND own."studentId" = :student_id
                LEFT JOIN "CurriculumConceptPrerequisite" prereq ON prereq."conceptId" = c.id
                LEFT JOIN "StudentConceptMastery" pm
                  ON pm."conceptId" = prereq."prerequisiteId"
                 AND pm."studentId" = :student_id AND pm.score >= 0.7
                LEFT JOIN "CurriculumConceptPrerequisite" dep ON dep."prerequisiteId" = c.id
                WHERE c.track = CAST(:track AS "Track") AND COALESCE(own.score, 0) < 0.7
                GROUP BY c.id
                HAVING COUNT(DISTINCT prereq."prerequisiteId") = COUNT(DISTINCT pm."conceptId")
                ORDER BY dependent_count DESC, prereq_count ASC
                LIMIT :limit
            '''), {"student_id": student_id, "track": track, "limit": limit})
            return [dict(row) for row in result.mappings().all()]

    async def get_prerequisite_chain(self, concept_id: str, depth: int = 3) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                WITH RECURSIVE chain AS (
                    SELECT p."prerequisiteId" AS id, 1 AS distance
                    FROM "CurriculumConceptPrerequisite" p WHERE p."conceptId" = :concept_id
                    UNION ALL
                    SELECT p."prerequisiteId", chain.distance + 1
                    FROM chain JOIN "CurriculumConceptPrerequisite" p ON p."conceptId" = chain.id
                    WHERE chain.distance < :depth
                )
                SELECT DISTINCT ON (c.id) c.id AS concept_id, c.title,
                       c.track::text AS track, c.difficulty, chain.distance
                FROM chain JOIN "CurriculumConcept" c ON c.id = chain.id
                ORDER BY c.id, chain.distance
            '''), {"concept_id": concept_id, "depth": depth})
            rows = [dict(row) for row in result.mappings().all()]
            return sorted(rows, key=lambda row: row["distance"], reverse=True)

    async def get_cross_track_concepts(
        self, track: str, keywords: list[str], limit: int = 4
    ) -> list[dict]:
        patterns = [f"%{word}%" for word in keywords if word]
        if not patterns:
            return []
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT DISTINCT c.id AS concept_id, c.title, c.track::text AS track,
                       c.description
                FROM "CurriculumConcept" c
                WHERE c.track <> CAST(:track AS "Track")
                  AND EXISTS (
                    SELECT 1 FROM unnest(CAST(:patterns AS text[])) pattern
                    WHERE c.title ILIKE pattern OR c.description ILIKE pattern
                  )
                LIMIT :limit
            '''), {"track": track, "patterns": patterns, "limit": limit})
            return [dict(row) for row in result.mappings().all()]

    async def get_related_concepts(self, concept: str, track: str, limit: int = 5) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT code AS standard_id, description AS text, grade, track
                FROM "OASStandard"
                WHERE track = :track AND (description ILIKE :query OR "lessonHook" ILIKE :query)
                ORDER BY grade LIMIT :limit
            '''), {"track": track, "query": f"%{concept}%", "limit": limit})
            return [dict(row) for row in result.mappings().all()]

    async def get_standards_for_track(
        self, track: str, limit: Optional[int] = None,
        grade_min: Optional[int] = None, grade_max: Optional[int] = None,
    ) -> list[dict]:
        clauses = ["track = :track"]
        params: dict = {"track": track}
        if grade_min is not None:
            clauses.append("grade >= :grade_min")
            params["grade_min"] = grade_min
        if grade_max is not None:
            clauses.append("grade <= :grade_max")
            params["grade_max"] = grade_max
        limit_sql = " LIMIT :limit" if limit is not None else ""
        if limit is not None:
            params["limit"] = limit
        async with _get_session_factory()() as session:
            result = await session.execute(text(f'''
                SELECT code AS standard_id, code, description AS text, description,
                       grade, strand, track, "lessonHook" AS lesson_hook,
                       "gradeBand" AS grade_band, subject
                FROM "OASStandard" WHERE {" AND ".join(clauses)}
                ORDER BY grade, strand, code{limit_sql}
            '''), params)
            return [dict(row) for row in result.mappings().all()]

    async def get_cross_track_context(self, track: str, limit: int = 6) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT s.code AS standard_id, s.description AS text,
                       s."lessonHook" AS lesson_hook, s.grade,
                       s.track AS connected_track
                FROM "CurriculumTrackLink" l
                JOIN "OASStandard" s ON s.track = l."toTrack"::text
                WHERE l."fromTrack" = CAST(:track AS "Track")
                ORDER BY s.grade, s.code LIMIT :limit
            '''), {"track": track, "limit": limit})
            return [dict(row) for row in result.mappings().all()]

    async def find_track_bridge(self, from_track: str, to_track: str, limit: int = 3) -> list[dict]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT s.code AS standard_id, s.description AS text, s.grade,
                       s."lessonHook" AS lesson_hook,
                       :from_track AS from_track, :to_track AS to_track
                FROM "CurriculumTrackLink" l
                JOIN "OASStandard" s ON s.track = l."fromTrack"::text
                WHERE l."fromTrack" = CAST(:from_track AS "Track")
                  AND l."toTrack" = CAST(:to_track AS "Track")
                ORDER BY s.grade LIMIT :limit
            '''), {"from_track": from_track, "to_track": to_track, "limit": limit})
            return [dict(row) for row in result.mappings().all()]

    async def count_mastered_concepts(self, student_id: str, track: str) -> tuple[int, float]:
        async with _get_session_factory()() as session:
            result = await session.execute(text('''
                SELECT COUNT(*) AS mastered_count, COALESCE(AVG(m.score), 0) AS avg_score
                FROM "StudentConceptMastery" m
                JOIN "CurriculumConcept" c ON c.id = m."conceptId"
                WHERE m."studentId" = :student_id
                  AND c.track = CAST(:track AS "Track") AND m.score >= 0.7
            '''), {"student_id": student_id, "track": track})
            row = result.mappings().one()
            return int(row["mastered_count"]), float(row["avg_score"])


def _subject_from_code(code: str) -> str:
    upper = code.upper()
    for token in ("MATH", "ELA", "SCI", "SS", "HLT"):
        if token in upper:
            return token
    return "ELA"


curriculum_graph = CurriculumGraph()
