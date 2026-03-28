"""
StudentState — Live academic profile for the ZPD Engine.

mastery_score: 0.0 → 1.0 per track, derived from sealed lesson count.
  0.00 – 0.29  NOVICE     (fewer than 3 sealed lessons in track)
  0.30 – 0.59  DEVELOPING (3–5 lessons)
  0.60 – 0.84  PROFICIENT (6–8 lessons)
  0.85 – 1.00  ADVANCED   (9+ lessons)

mastered_standards: OAS standard IDs already earned (from Neo4j MASTERED edges).
These become 'Witness Anchors' in bridge responses.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from app.connections.journal_store import journal_store
from app.connections.neo4j_client import neo4j_client
from app.schemas.api_models import Track

logger = logging.getLogger(__name__)

# Lessons required to reach mastery = 1.0
_MASTERY_SCALE = 10.0


class MasteryBand(str, Enum):
    NOVICE     = "NOVICE"      # 0.00 – 0.29
    DEVELOPING = "DEVELOPING"  # 0.30 – 0.59
    PROFICIENT = "PROFICIENT"  # 0.60 – 0.84
    ADVANCED   = "ADVANCED"    # 0.85 – 1.00


def _band(score: float) -> MasteryBand:
    if score < 0.30:
        return MasteryBand.NOVICE
    if score < 0.60:
        return MasteryBand.DEVELOPING
    if score < 0.85:
        return MasteryBand.PROFICIENT
    return MasteryBand.ADVANCED


@dataclass
class TrackMastery:
    track: str
    lesson_count: int
    mastery_score: float          # 0.0 – 1.0
    mastery_band: MasteryBand
    mastered_standards: list[dict] = field(default_factory=list)


@dataclass
class StudentState:
    student_id: str
    tracks: dict[str, TrackMastery] = field(default_factory=dict)

    def get(self, track: str) -> TrackMastery:
        """Return the TrackMastery for a given track, defaulting to NOVICE."""
        return self.tracks.get(
            track,
            TrackMastery(
                track=track,
                lesson_count=0,
                mastery_score=0.0,
                mastery_band=MasteryBand.NOVICE,
                mastered_standards=[],
            ),
        )

    def witness_anchors(self, track: str, limit: int = 3) -> list[dict]:
        """
        Return the student's most recently mastered OAS standards for a track.
        Used by the ZPD Engine as 'Witness Anchors' in bridge responses.
        """
        tm = self.get(track)
        return tm.mastered_standards[:limit]


async def load_student_state(student_id: str) -> StudentState:
    """
    Build a live StudentState from journal_store (lesson counts) and
    Neo4j (mastered OAS standards).
    """
    state = StudentState(student_id=student_id)

    # ── 1. Lesson counts per track ────────────────────────────────────────────
    try:
        progress = await journal_store.get_track_progress(student_id)
    except Exception as e:
        logger.warning(f"[StudentState] journal_store unavailable: {e}")
        progress = {}

    # ── 2. Mastered OAS standards from Neo4j ─────────────────────────────────
    try:
        rows = await neo4j_client.run(
            """
            MATCH (st:Student {id: $student_id})-[:MASTERED]->(s:OASStandard)
            OPTIONAL MATCH (s)-[:MAPS_TO_TRACK]->(t:Track)
            RETURN s.id        AS standard_id,
                   s.text      AS text,
                   s.grade     AS grade,
                   coalesce(t.name, s.track) AS track
            ORDER BY track, s.grade
            """,
            {"student_id": student_id},
        )
    except Exception as e:
        logger.warning(f"[StudentState] Neo4j unavailable: {e}")
        rows = []

    # Group standards by track
    standards_by_track: dict[str, list[dict]] = {}
    for row in rows:
        t = row.get("track", "")
        if t:
            standards_by_track.setdefault(t, []).append(row)

    # ── 3. Build TrackMastery for every known track ───────────────────────────
    all_tracks = set(progress.keys()) | set(standards_by_track.keys())
    for track_name in all_tracks:
        count = progress.get(track_name, 0)
        score = min(count / _MASTERY_SCALE, 1.0)
        state.tracks[track_name] = TrackMastery(
            track=track_name,
            lesson_count=count,
            mastery_score=round(score, 3),
            mastery_band=_band(score),
            mastered_standards=standards_by_track.get(track_name, []),
        )

    logger.info(
        f"[StudentState] Loaded student_id={student_id} — "
        f"{len(state.tracks)} active tracks, "
        f"{len(rows)} mastered standards"
    )
    return state
