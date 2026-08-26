#!/usr/bin/env python3
"""Dry-run or import an authoritative standards progression file.

Usage:
  python -m scripts.import_standard_progressions path/to/progression.csv
  python -m scripts.import_standard_progressions path/to/progression.csv --apply --allow-verified

The importer never infers relationships.  VERIFIED hard gates require complete
source provenance, known local standard IDs, and an acyclic prerequisite graph.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import text

from app.connections.postgres import _get_session_factory
from app.curriculum.progression_import import (
    load_progression_file,
    prerequisite_cycles,
    validate_known_standards,
)


async def run(path: Path, *, apply: bool, allow_verified: bool) -> None:
    edges = load_progression_file(path)
    verified = [edge for edge in edges if edge.review_status == "VERIFIED"]
    if verified and not allow_verified:
        raise ValueError("file contains VERIFIED edges; rerun with --allow-verified after source review")

    async with _get_session_factory()() as session:
        known_ids = set((await session.execute(text('SELECT code FROM "OASStandard"'))).scalars().all())
        errors = validate_known_standards(edges, known_ids)
        if errors:
            raise ValueError("; ".join(errors[:20]))

        existing = await session.execute(text('''
            SELECT "fromStandardId" AS from_standard_id,
                   "relationType" AS relation_type,
                   "toStandardId" AS to_standard_id,
                   weight, "sourceTitle" AS source_title,
                   "sourceUrl" AS source_url,
                   "sourceVersion" AS source_version,
                   "evidenceNote" AS evidence_note,
                   "reviewStatus" AS review_status
            FROM "OASStandardRelation"
            WHERE "relationType" = 'PREREQUISITE_FOR'
              AND "reviewStatus" = 'VERIFIED'
        '''))
        from app.curriculum.progression_import import edge_from_row
        combined = [edge_from_row(dict(row)) for row in existing.mappings().all()] + edges
        cycles = prerequisite_cycles(combined)
        if cycles:
            raise ValueError(f"verified prerequisite cycle detected: {' -> '.join(cycles[0])}")

        print(f"Validated {len(edges)} edges ({len(verified)} verified) from {path}")
        if not apply:
            print("Dry run only; no database changes were made.")
            return

        await session.execute(text('''
            INSERT INTO "OASStandardRelation"
                ("fromStandardId", "relationType", "toStandardId", weight,
                 "sourceTitle", "sourceUrl", "sourceVersion", "evidenceNote",
                 "reviewStatus", "reviewedAt")
            VALUES
                (:from_standard_id, :relation_type, :to_standard_id, :weight,
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
        '''), [edge.as_row() for edge in edges])
        await session.commit()
        print(f"Imported {len(edges)} provenance-backed progression edges.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-verified", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.path, apply=args.apply, allow_verified=args.allow_verified))


if __name__ == "__main__":
    main()
