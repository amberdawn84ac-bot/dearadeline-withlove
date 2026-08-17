"""Curriculum relationship helpers backed by the existing Postgres database."""
from __future__ import annotations

import logging
from typing import Optional

from app.connections.curriculum_graph import curriculum_graph

logger = logging.getLogger(__name__)

TRACKS_METADATA = {
    "TRUTH_HISTORY": {"theme": "History & Truth", "color": "#3D1419"},
    "CREATION_SCIENCE": {"theme": "Science & Creation", "color": "#2F4731"},
    "HOMESTEADING": {"theme": "Land & Self-Sufficiency", "color": "#5C7A2F"},
    "GOVERNMENT_ECONOMICS": {"theme": "Civics & Economics", "color": "#BD6809"},
    "JUSTICE_CHANGEMAKING": {"theme": "Justice & Social Change", "color": "#9A3F4A"},
    "DISCIPLESHIP": {"theme": "Faith & Character", "color": "#4F46E5"},
    "HEALTH_NATUROPATHY": {"theme": "Health & Natural Medicine", "color": "#047857"},
    "ENGLISH_LITERATURE": {"theme": "Language & Literature", "color": "#7C3AED"},
    "APPLIED_MATHEMATICS": {"theme": "Math & Real-World Application", "color": "#1E3A5F"},
    "CREATIVE_ECONOMY": {"theme": "Making, Craft & Entrepreneurship", "color": "#7B2D8B"},
}

CROSS_TRACK_INFLUENCE_MAP: dict[str, list[tuple[str, float]]] = {
    "APPLIED_MATHEMATICS": [("GOVERNMENT_ECONOMICS", .3), ("HOMESTEADING", .25), ("CREATIVE_ECONOMY", .3)],
    "CREATION_SCIENCE": [("HEALTH_NATUROPATHY", .35), ("HOMESTEADING", .3)],
    "DISCIPLESHIP": [("ENGLISH_LITERATURE", .25), ("TRUTH_HISTORY", .2)],
    "TRUTH_HISTORY": [("JUSTICE_CHANGEMAKING", .3), ("ENGLISH_LITERATURE", .25)],
    "GOVERNMENT_ECONOMICS": [("JUSTICE_CHANGEMAKING", .3), ("APPLIED_MATHEMATICS", .25)],
    "HOMESTEADING": [("CREATION_SCIENCE", .3), ("APPLIED_MATHEMATICS", .2)],
    "CREATIVE_ECONOMY": [("APPLIED_MATHEMATICS", .2), ("HOMESTEADING", .15)],
    "ENGLISH_LITERATURE": [("TRUTH_HISTORY", .2), ("DISCIPLESHIP", .2)],
}

_TRACK_LABELS = {key: value["theme"] for key, value in TRACKS_METADATA.items()}


async def apply_schema_constraints() -> None:
    """Schema is managed by Prisma migrations; verify it is reachable."""
    await curriculum_graph.connect()


async def seed_tracks() -> None:
    """Track values live in the existing Postgres Track enum."""
    return None


async def upsert_concept(
    concept_id: str, title: str, description: str, track: str, difficulty: str,
    standard_code: Optional[str] = None, grade_band: Optional[str] = None,
    tags: Optional[list[str]] = None, is_primary_source: bool = False,
) -> None:
    await curriculum_graph.upsert_concept(
        concept_id, title, description, track, difficulty,
        standard_code or "", grade_band or "", tags, is_primary_source,
    )


async def add_prerequisite(from_concept_id: str, to_concept_id: str, weight: float = 1.0) -> None:
    await curriculum_graph.add_prerequisite(from_concept_id, to_concept_id, weight)


async def link_concept_to_standard(concept_id: str, standard_id: str) -> None:
    return None


async def link_concept_to_evidence(
    concept_id: str, evidence_id: str, chunk: str, truth_score: float
) -> None:
    from sqlalchemy import text
    from app.connections.postgres import _get_session_factory
    async with _get_session_factory()() as session:
        await session.execute(text('''
            INSERT INTO "CurriculumConceptEvidence" ("conceptId", "evidenceId", chunk, "truthScore")
            VALUES (:concept_id, :evidence_id, :chunk, :truth_score)
            ON CONFLICT ("conceptId", "evidenceId") DO UPDATE SET
                chunk = EXCLUDED.chunk, "truthScore" = EXCLUDED."truthScore"
        '''), {"concept_id": concept_id, "evidence_id": evidence_id,
                "chunk": chunk, "truth_score": truth_score})
        await session.commit()


async def record_concept_mastery(
    student_id: str, concept_id: str, score: float, sealed_at: Optional[str] = None
) -> None:
    await curriculum_graph.record_concept_mastery(student_id, concept_id, score, sealed_at)


async def get_concept_graph_for_track(track: str) -> list[dict]:
    try:
        return await curriculum_graph.get_concept_graph_for_track(track)
    except Exception as exc:
        logger.error("[CurriculumGraph] concept query failed for %s: %s", track, exc)
        return []


async def get_zpd_candidates_with_bkt(track: str, mastery_snapshots: dict, limit: int = 5) -> list:
    from app.algorithms.zpd_engine import compute_zpd_from_snapshots
    rows = await get_concept_graph_for_track(track)
    return compute_zpd_from_snapshots(mastery_snapshots, rows)[:limit] if rows else []


async def get_zpd_candidates(student_id: str, track: str, limit: int = 5) -> list[dict]:
    try:
        return await curriculum_graph.get_zpd_candidates(student_id, track, limit)
    except Exception as exc:
        logger.error("[CurriculumGraph] ZPD query failed for %s: %s", track, exc)
        return []


async def get_prerequisite_chain(concept_id: str, depth: int = 3) -> list[dict]:
    try:
        return await curriculum_graph.get_prerequisite_chain(concept_id, depth)
    except Exception as exc:
        logger.error("[CurriculumGraph] prerequisite query failed for %s: %s", concept_id, exc)
        return []


async def get_cross_track_concepts(track: str, topic_keywords: list[str], limit: int = 4) -> list[dict]:
    try:
        return await curriculum_graph.get_cross_track_concepts(track, topic_keywords, limit)
    except Exception as exc:
        logger.error("[CurriculumGraph] cross-track query failed for %s: %s", track, exc)
        return []


async def get_cross_track_bias(student_id: str, target_track: str) -> tuple[float, str | None]:
    influencers = [
        (source, weight)
        for source, targets in CROSS_TRACK_INFLUENCE_MAP.items()
        for track, weight in targets if track == target_track
    ]
    bias = 0.0
    strongest_source = None
    strongest_contribution = 0.0
    for source_track, weight in influencers:
        try:
            count, average = await curriculum_graph.count_mastered_concepts(student_id, source_track)
        except Exception as exc:
            logger.warning("[CurriculumGraph] mastery bias query failed: %s", exc)
            continue
        contribution = min(1.0, count / 8.0) * average * weight
        bias += contribution
        if contribution > strongest_contribution:
            strongest_source, strongest_contribution = source_track, contribution
    if bias <= 0.15 or not strongest_source:
        return bias, None
    source_label = _TRACK_LABELS.get(strongest_source, strongest_source.replace("_", " ").title())
    target_label = _TRACK_LABELS.get(target_track, target_track.replace("_", " ").title())
    return bias, (
        f"Since you've built real skill in {source_label}, I think {target_label} is going "
        "to feel familiar — some of what you already know maps directly here."
    )
