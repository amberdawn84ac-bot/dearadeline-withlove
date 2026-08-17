#!/usr/bin/env python3
"""Load all Oklahoma standards into the existing Postgres database."""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.connections.curriculum_graph import curriculum_graph
from app.connections.postgres import _get_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

OAS_SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "oas_to_8track.json"
OVERALL_TIMEOUT = 600


async def seed_oas_standards() -> None:
    await curriculum_graph.connect()
    with OAS_SEED_PATH.open("r", encoding="utf-8") as source:
        mappings = json.load(source).get("mappings", [])

    standards: list[dict] = []
    relations: list[dict] = []
    tracks = {mapping.get("track") for mapping in mappings}
    for mapping in mappings:
        # Human-readable OAS codes repeat across subjects and grades. The
        # compound seed ID is the stable unique key used throughout mastery.
        standard_id = (
            mapping.get("standard_node", {}).get("properties", {}).get("id")
            or mapping.get("neo4j_node", {}).get("properties", {}).get("id")
            or mapping.get("standard_id")
        )
        if not standard_id:
            continue
        node_properties = (
            mapping.get("standard_node", {}).get("properties", {})
            or mapping.get("neo4j_node", {}).get("properties", {})
        )
        standards.append({
            "code": standard_id,
            "grade": mapping.get("grade", 0),
            "subject": mapping.get("subject", "ELA"),
            "strand": mapping.get("strand") or node_properties.get("strand", ""),
            "description": mapping.get("standard_text", ""),
            "grade_band": mapping.get("grade_band", ""),
            "lesson_hook": mapping.get("adeline_lesson_hook", ""),
            "homestead": mapping.get("homestead_adaptation", ""),
            "difficulty": mapping.get("difficulty", "EMERGING"),
            "track": mapping.get("track", "ENGLISH_LITERATURE"),
        })
        for relation in mapping.get("standard_relationships", mapping.get("neo4j_relationships", [])):
            target = relation.get("target") or relation.get("target_id")
            relation_type = relation.get("type", "RELATED_TO")
            if target and target not in tracks:
                relations.append({
                    "from_id": standard_id,
                    "relation_type": relation_type,
                    "to_id": target,
                    "weight": float(relation.get("weight", 1.0)),
                })

    async with _get_session_factory()() as session:
        await session.execute(text('''
            INSERT INTO "OASStandard"
                (id, code, subject, grade, "gradeBand", strand, description, track,
                 "lessonHook", "homesteadAdaptation", difficulty, "createdAt")
            VALUES
                (gen_random_uuid(), :code, :subject, :grade, :grade_band, :strand,
                 :description, :track, :lesson_hook, :homestead, :difficulty, NOW())
            ON CONFLICT (code) DO UPDATE SET
                subject = EXCLUDED.subject, grade = EXCLUDED.grade,
                "gradeBand" = EXCLUDED."gradeBand", strand = EXCLUDED.strand,
                description = EXCLUDED.description, track = EXCLUDED.track,
                "lessonHook" = EXCLUDED."lessonHook",
                "homesteadAdaptation" = EXCLUDED."homesteadAdaptation",
                difficulty = EXCLUDED.difficulty
        '''), standards)
        if relations:
            await session.execute(text('''
                INSERT INTO "OASStandardRelation"
                    ("fromStandardId", "relationType", "toStandardId", weight)
                VALUES (:from_id, :relation_type, :to_id, :weight)
                ON CONFLICT ("fromStandardId", "relationType", "toStandardId")
                DO UPDATE SET weight = EXCLUDED.weight
            '''), relations)
        await session.commit()
        count = (await session.execute(text('SELECT COUNT(*) FROM "OASStandard"'))).scalar_one()
    logger.info("Loaded %s standards; Postgres now contains %s", len(standards), count)


async def main() -> None:
    await asyncio.wait_for(seed_oas_standards(), timeout=OVERALL_TIMEOUT)


if __name__ == "__main__":
    asyncio.run(main())
