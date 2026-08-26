"""Read-only audit of existing CanonicalLesson quality.

Computes, per canonical, the signals from the experience-first architecture
design report's migration-triage section: TEXT-block ratio, evidence
presence, and stage/type mismatches (a block whose experience_stage claims
ACTION/CREATION/DEMONSTRATION without a block_type from the corresponding
type set — the exact gap that lets a plain TEXT block satisfy validation by
self-labeling).

This script performs no writes, updates, deletes, or archive() calls. It only
SELECTs from "CanonicalLesson" and prints a report. Safe to run against
production for real numbers; nothing here mutates state.

Usage:
    cd adeline-brain
    python -m app.scripts.audit_canonical_quality
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from app.config import get_db_conn

ACTION_TYPES = frozenset({
    "LAB_MISSION", "EXPERIMENT", "REAL_WORLD_APP", "SIMULATION",
    "RESEARCH_MISSION", "DISCUSSION_FORUM",
})
CREATION_TYPES = frozenset({"PROJECT_BUILDER", "TIMELINE", "MIND_MAP", "CONCEPT_MAP"})
DEMONSTRATION_TYPES = frozenset({"QUIZ", "FLASHCARD", "SCAFFOLDED_PROBLEM", "GENUI_ASSEMBLY"})
STAGE_TYPE_MAP = {
    "ACTION": ACTION_TYPES,
    "CREATION": CREATION_TYPES,
    "DEMONSTRATION": DEMONSTRATION_TYPES,
}

# Superset of family_style.py's _TRACKS_EXPECTING_SUBSTANTIVE_BLOCKS — this
# audit additionally flags DISCIPLESHIP so the known gap shows up in the report.
TRACKS_EXPECTING_EVIDENCE = frozenset({
    "TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "CREATION_SCIENCE", "HOMESTEADING",
    "ENGLISH_LITERATURE", "APPLIED_MATHEMATICS", "CREATIVE_ECONOMY", "DISCIPLESHIP",
})

TEXT_RATIO_FLAG_THRESHOLD = 0.5


@dataclass
class CanonicalAudit:
    id: str
    topic: str
    track: str
    generated_at: str
    updated_at: str
    total_blocks: int = 0
    text_blocks: int = 0
    blocks_with_evidence: int = 0
    stage_type_mismatches: int = 0
    flags: list[str] = field(default_factory=list)

    @property
    def text_ratio(self) -> float:
        return self.text_blocks / self.total_blocks if self.total_blocks else 0.0


def _audit_one(row: dict) -> CanonicalAudit:
    audit = CanonicalAudit(
        id=row["id"], topic=row["topic"], track=row["track"],
        generated_at=str(row["generatedAt"]), updated_at=str(row["updatedAt"]),
    )
    blocks_raw = row["blocksJson"]
    blocks = json.loads(blocks_raw) if isinstance(blocks_raw, str) else (blocks_raw or [])
    if not isinstance(blocks, list):
        audit.flags.append("UNPARSEABLE_BLOCKS")
        return audit

    audit.total_blocks = len(blocks)

    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("block_type") or "").upper()
        stage = str(block.get("experience_stage") or "").upper()

        if block_type == "TEXT":
            audit.text_blocks += 1

        evidence = block.get("evidence")
        if isinstance(evidence, list) and evidence:
            audit.blocks_with_evidence += 1

        expected_types = STAGE_TYPE_MAP.get(stage)
        if expected_types is not None and block_type not in expected_types:
            audit.stage_type_mismatches += 1

    if audit.total_blocks and audit.text_ratio > TEXT_RATIO_FLAG_THRESHOLD:
        audit.flags.append(f"HIGH_TEXT_RATIO({audit.text_ratio:.2f})")

    if audit.track in TRACKS_EXPECTING_EVIDENCE and audit.blocks_with_evidence == 0:
        audit.flags.append("NO_EVIDENCE_IN_EVIDENCE_EXPECTING_TRACK")

    if audit.stage_type_mismatches:
        audit.flags.append(f"STAGE_TYPE_MISMATCH(x{audit.stage_type_mismatches})")

    return audit


async def run_audit() -> list[CanonicalAudit]:
    conn = await get_db_conn()
    try:
        rows = await conn.fetch(
            'SELECT "id", "topic", "track", "blocksJson", "generatedAt", "updatedAt" '
            'FROM "CanonicalLesson" ORDER BY "generatedAt" ASC'
        )
    finally:
        await conn.close()
    return [_audit_one(dict(row)) for row in rows]


def print_report(audits: list[CanonicalAudit]) -> None:
    if not audits:
        print("No CanonicalLesson rows found. Nothing to audit.")
        return

    total = len(audits)
    flagged = [a for a in audits if a.flags]
    by_track: dict[str, list[CanonicalAudit]] = defaultdict(list)
    for a in audits:
        by_track[a.track].append(a)

    print(f"\n=== Canonical Quality Audit — {total} canonicals ===\n")
    print(f"Flagged (any signal): {len(flagged)} / {total} ({len(flagged) / total:.0%})\n")

    flag_counts: Counter[str] = Counter()
    for a in flagged:
        for f in a.flags:
            flag_counts[f.split("(")[0]] += 1
    print("By flag type:")
    for flag_name, count in flag_counts.most_common():
        print(f"  {flag_name}: {count}")

    print("\nBy track:")
    for track, items in sorted(by_track.items(), key=lambda kv: -len(kv[1])):
        track_flagged = [a for a in items if a.flags]
        avg_text_ratio = sum(a.text_ratio for a in items) / len(items) if items else 0
        print(
            f"  {track:24s} total={len(items):4d}  flagged={len(track_flagged):4d}"
            f"  avg_text_ratio={avg_text_ratio:.2f}"
        )

    print(f"\n=== {min(20, len(flagged))} most-flagged examples (worst text ratio first) ===\n")
    worst = sorted(flagged, key=lambda a: -a.text_ratio)[:20]
    for a in worst:
        print(
            f"  [{a.track}] {a.topic!r} blocks={a.total_blocks} "
            f"text={a.text_blocks} evidence={a.blocks_with_evidence} "
            f"mismatches={a.stage_type_mismatches} flags={a.flags} "
            f"generated={a.generated_at}"
        )
    print()


async def main() -> None:
    audits = await run_audit()
    print_report(audits)


if __name__ == "__main__":
    asyncio.run(main())
