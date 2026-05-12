"""
BKT State Tracker — bridges zpd_engine.py math with SpacedRepetitionCard persistence.

Per-concept BKT pL is stored in SpacedRepetitionCard.masteryLevel.
When pL crosses the mastery threshold (0.7), a MASTERED edge is written to Neo4j.

This closes the feedback loop that makes ZPD proactive:
  student answers quiz       → update_bkt(correct=True/False)
  → new pL stored in SpacedRepetitionCard.masteryLevel
  → if pL >= 0.7: MASTERED edge written to Neo4j
  → next get_zpd_candidates_with_bkt() reflects new mastery
  → higher-order concepts become available in ZPD

Previously, TrackMastery.mastery_score = lesson_count / 10 was used as a BKT proxy.
This module replaces that proxy with actual per-concept BKT state.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import get_db_conn
from app.algorithms.zpd_engine import (
    BKTParams,
    AdaptiveBKTParams,
    bkt_update,
    adaptive_bkt_update,
    apply_decay,
    MasterySnapshot,
    MASTERY_THRESHOLD,
)
from app.connections.knowledge_graph import record_concept_mastery

logger = logging.getLogger(__name__)

# Default BKT priors for a student seeing a concept for the first time
_DEFAULT_BKT = AdaptiveBKTParams(
    pL=0.1,   # low initial mastery assumption
    pT=0.15,  # 15% chance of learning per interaction
    pS=0.05,  # 5% slip rate
    pG=0.25,  # 25% guess rate
)


async def get_mastery_map(student_id: str, track: str) -> dict[str, float]:
    """
    Read all per-concept BKT pL values for a student/track from SpacedRepetitionCard.
    Returns {concept_id: pL} — empty dict if none exist yet.
    """
    try:
        conn = await get_db_conn()
        try:
            rows = await conn.fetch(
                """
                SELECT "conceptId", "masteryLevel", "updatedAt"
                FROM "SpacedRepetitionCard"
                WHERE "studentId" = $1 AND "track" = $2
                """,
                student_id, track,
            )
        finally:
            await conn.close()
        return {r["conceptId"]: float(r["masteryLevel"]) for r in rows}
    except Exception as e:
        logger.warning(f"[BKTTracker] get_mastery_map failed for {student_id}/{track}: {e}")
        return {}


async def get_mastery_map_with_timestamps(student_id: str, track: str) -> dict[str, tuple[float, Optional[datetime]]]:
    """
    Returns {concept_id: (pL, last_practiced_at)} — used to apply forgetting-curve decay.
    """
    try:
        conn = await get_db_conn()
        try:
            rows = await conn.fetch(
                """
                SELECT "conceptId", "masteryLevel", "updatedAt"
                FROM "SpacedRepetitionCard"
                WHERE "studentId" = $1 AND "track" = $2
                """,
                student_id, track,
            )
        finally:
            await conn.close()
        result = {}
        for r in rows:
            ts = r["updatedAt"]
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            result[r["conceptId"]] = (float(r["masteryLevel"]), ts)
        return result
    except Exception as e:
        logger.warning(f"[BKTTracker] get_mastery_map_with_timestamps failed: {e}")
        return {}


async def update_bkt(
    student_id: str,
    concept_id: str,
    track: str,
    correct: bool,
) -> float:
    """
    Apply a Bayesian Knowledge Tracing update after one student interaction.

    1. Read current pL from SpacedRepetitionCard (defaults to 0.1 if unseen)
    2. Run bkt_update(params, correct) → new_pL
    3. UPSERT SpacedRepetitionCard with new masteryLevel
    4. If new_pL >= MASTERY_THRESHOLD: write MASTERED edge to Neo4j

    Returns the new pL value.
    """
    try:
        conn = await get_db_conn()

        row = await conn.fetchrow(
            """
            SELECT "masteryLevel", "easeFactor", "repetitions"
            FROM "SpacedRepetitionCard"
            WHERE "studentId" = $1 AND "conceptId" = $2
            """,
            student_id, concept_id,
        )

        current_pL = float(row["masteryLevel"]) if row else _DEFAULT_BKT.pL
        params = AdaptiveBKTParams(
            pL=current_pL,
            pT=_DEFAULT_BKT.pT,
            pS=_DEFAULT_BKT.pS,
            pG=_DEFAULT_BKT.pG,
        )

        updated = adaptive_bkt_update(params, correct)
        new_pL = updated.pL

        # UPSERT the card — create if absent, update masteryLevel if present
        await conn.execute(
            """
            INSERT INTO "SpacedRepetitionCard"
                ("studentId", "conceptId", "conceptName", "track", "masteryLevel", "updatedAt")
            VALUES ($1, $2, $3, $4, $5, now())
            ON CONFLICT ("studentId", "conceptId")
            DO UPDATE SET
                "masteryLevel" = EXCLUDED."masteryLevel",
                "updatedAt"    = now()
            """,
            student_id, concept_id, concept_id, track, new_pL,
        )
        await conn.close()

        logger.info(
            f"[BKTTracker] update: student={student_id[:8]} concept={concept_id} "
            f"correct={correct} pL: {current_pL:.3f} → {new_pL:.3f}"
        )

        # Write Neo4j MASTERED edge when BKT crosses threshold
        if new_pL >= MASTERY_THRESHOLD and current_pL < MASTERY_THRESHOLD:
            logger.info(
                f"[BKTTracker] MASTERY THRESHOLD CROSSED for {concept_id} "
                f"(pL={new_pL:.3f}) — writing MASTERED edge to Neo4j"
            )
            try:
                await record_concept_mastery(
                    student_id=student_id,
                    concept_id=concept_id,
                    score=new_pL,
                    sealed_at=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as e:
                logger.warning(f"[BKTTracker] Neo4j MASTERED edge write failed (non-fatal): {e}")

        return new_pL

    except Exception as e:
        logger.warning(f"[BKTTracker] update_bkt failed for {concept_id}: {e}")
        return _DEFAULT_BKT.pL


def build_mastery_snapshots(
    concept_rows: list[dict],
    mastery_map_with_ts: dict[str, tuple[float, Optional[datetime]]],
) -> dict[str, MasterySnapshot]:
    """
    Build a {concept_id: MasterySnapshot} dict for compute_zpd_from_snapshots().

    concept_rows: list of concept dicts from Neo4j (must have 'id' and 'name').
    mastery_map_with_ts: {concept_id: (pL, last_practiced_at)} from SpacedRepetitionCard.
    """
    snapshots: dict[str, MasterySnapshot] = {}

    for c in concept_rows:
        cid = c.get("id") or c.get("concept_id", "")
        if not cid:
            continue

        entry = mastery_map_with_ts.get(cid)
        if entry:
            pL, last_practiced = entry
            # Apply forgetting-curve decay if we have a timestamp
            decay_adj = apply_decay(pL, last_practiced) if last_practiced else pL
        else:
            pL = _DEFAULT_BKT.pL
            decay_adj = pL
            last_practiced = None

        status = "unknown"
        if decay_adj >= MASTERY_THRESHOLD:
            status = "mastered"
        elif decay_adj >= 0.3:
            status = "in_zpd"
        else:
            status = "not_ready"

        snapshots[cid] = MasterySnapshot(
            concept_id=cid,
            name=c.get("name") or c.get("title", ""),
            mastery_level=pL,
            decay_adjusted=decay_adj,
            bkt_probability=pL,
            last_practiced=last_practiced,
            status=status,
        )

    return snapshots


def zpd_zone_to_correctness(zpd_zone: str) -> Optional[bool]:
    """
    Convert a ZPD zone signal to a BKT correctness value.

    FRUSTRATED  → False (student struggled — negative evidence)
    IN_ZPD      → True  (student engaged correctly — positive evidence)
    BORED       → True  (student knew it — strong positive evidence)
    """
    mapping = {
        "FRUSTRATED": False,
        "IN_ZPD":     True,
        "BORED":      True,
    }
    return mapping.get(zpd_zone)


async def update_card_after_lesson(
    student_id: str,
    concept_id: str,
    concept_name: str,
    track: str,
    quality: int = 3,
) -> float:
    """
    Combined BKT pL update + SM-2 scheduling after lesson completion or journal seal.

    quality (SM-2 scale, 0–5):
      5 = perfect recall, 4 = correct after hesitation, 3 = correct with difficulty (lesson default),
      2 = incorrect but easy to recall, 1 = incorrect, 0 = complete blackout

    Updates SpacedRepetitionCard with new mastery level + review schedule (interval, dueAt, easeFactor).
    Writes MASTERED edge to Neo4j if pL crosses threshold.
    Returns the new pL value.
    """
    from app.algorithms.spaced_repetition import sm2

    try:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                """
                SELECT "masteryLevel", "easeFactor", "repetitions", "interval"
                FROM "SpacedRepetitionCard"
                WHERE "studentId" = $1 AND "conceptId" = $2
                """,
                student_id, concept_id,
            )
        finally:
            await conn.close()

        current_pL    = float(row["masteryLevel"]) if row else _DEFAULT_BKT.pL
        prev_ease     = float(row["easeFactor"])    if row else 2.5
        prev_reps     = int(row["repetitions"])     if row else 0
        prev_interval = int(row["interval"])        if row else 1

        # BKT update — quality >= 3 counts as correct evidence
        correct = quality >= 3
        params  = AdaptiveBKTParams(
            pL=current_pL,
            pT=_DEFAULT_BKT.pT,
            pS=_DEFAULT_BKT.pS,
            pG=_DEFAULT_BKT.pG,
        )
        updated = adaptive_bkt_update(params, correct)
        new_pL  = updated.pL

        # SM-2 scheduling
        sm2_result = sm2(quality, prev_interval, prev_ease, prev_reps)

        # Full UPSERT — all card fields updated
        conn = await get_db_conn()
        try:
            await conn.execute(
                """
                INSERT INTO "SpacedRepetitionCard"
                    ("studentId","conceptId","conceptName","track","masteryLevel",
                     "easeFactor","repetitions","interval","dueAt","lastQuality","lastReviewedAt")
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,now())
                ON CONFLICT ("studentId","conceptId") DO UPDATE SET
                    "masteryLevel"   = EXCLUDED."masteryLevel",
                    "easeFactor"     = EXCLUDED."easeFactor",
                    "repetitions"    = EXCLUDED."repetitions",
                    "interval"       = EXCLUDED."interval",
                    "dueAt"          = EXCLUDED."dueAt",
                    "lastQuality"    = EXCLUDED."lastQuality",
                    "lastReviewedAt" = now(),
                    "updatedAt"      = now()
                """,
                student_id, concept_id, concept_name, track, new_pL,
                sm2_result.ease_factor, sm2_result.repetitions, sm2_result.interval,
                sm2_result.next_due_at, quality,
            )
        finally:
            await conn.close()

        logger.info(
            f"[BKTTracker] card updated: student={student_id[:8]} concept={concept_id} "
            f"pL={current_pL:.3f}→{new_pL:.3f} interval={sm2_result.interval}d "
            f"dueAt={sm2_result.next_due_at.date()} quality={quality}"
        )

        # Write MASTERED edge to Neo4j when pL crosses threshold
        if new_pL >= MASTERY_THRESHOLD and current_pL < MASTERY_THRESHOLD:
            logger.info(
                f"[BKTTracker] MASTERY THRESHOLD CROSSED for {concept_id} "
                f"(pL={new_pL:.3f}) — writing MASTERED edge to Neo4j"
            )
            try:
                await record_concept_mastery(
                    student_id=student_id,
                    concept_id=concept_id,
                    score=new_pL,
                    sealed_at=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as e:
                logger.warning(f"[BKTTracker] Neo4j MASTERED edge write failed (non-fatal): {e}")

        return new_pL

    except Exception as e:
        logger.warning(f"[BKTTracker] update_card_after_lesson failed for {concept_id}: {e}")
        return _DEFAULT_BKT.pL
