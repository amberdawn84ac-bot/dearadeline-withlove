"""Validate the shipped mapping and exercise its real learner readiness gates."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.connections.curriculum_graph import curriculum_graph
from app.curriculum.progression_import import (
    load_progression_file, prerequisite_cycles, validate_known_standards,
)
from scripts.import_standard_progressions import run

SEED_DIRECTORY = Path(__file__).resolve().parents[1] / 'data' / 'seeds'
MAPPING = SEED_DIRECTORY / 'verified_standard_progressions.json'


def test_shipped_mapping_has_reviewed_sources_and_existing_terminal_ids():
    edges = load_progression_file(MAPPING)
    catalog = json.loads((SEED_DIRECTORY / 'oas_to_8track.json').read_text())['mappings']
    known = {(row.get('standard_node') or row.get('neo4j_node'))['properties']['id'] for row in catalog}
    assert len(edges) == 30
    assert validate_known_standards(edges, known) == []
    assert prerequisite_cycles(edges) == []
    assert all(edge.review_status == 'VERIFIED' for edge in edges)
    assert len({(e.from_standard_id, e.to_standard_id) for e in edges}) == len(edges)


@pytest.mark.asyncio
async def test_imported_map_backtracks_and_unlocks_only_after_this_childs_evidence():
    dsn = os.getenv('POSTGRES_DSN')
    if not dsn:
        pytest.skip('Postgres is exercised in GitHub CI')
    engine = create_async_engine(dsn.replace('postgresql://', 'postgresql+asyncpg://', 1))
    try:
        async with engine.connect() as connection:
            await connection.execute(text('''CREATE TEMP TABLE "OASStandard" (
                code text PRIMARY KEY, description text, grade integer, subject text,
                track text, strand text DEFAULT '', "lessonHook" text DEFAULT '',
                difficulty text DEFAULT 'EMERGING', "progressionLane" text DEFAULT '',
                "progressionMode" text DEFAULT 'SEQUENTIAL', "progressionOrdinal" integer DEFAULT 0,
                "progressionSourceTitle" text DEFAULT '', "progressionSourceUrl" text DEFAULT '',
                "progressionSourceVersion" text DEFAULT '', "progressionReviewStatus" text DEFAULT 'PLACED',
                "progressionIsTerminal" boolean DEFAULT TRUE)'''))
            await connection.execute(text('''CREATE TEMP TABLE "OASStandardRelation" (
                "fromStandardId" text, "toStandardId" text, "relationType" text, weight float,
                "sourceTitle" text, "sourceUrl" text, "sourceVersion" text, "evidenceNote" text,
                "reviewStatus" text, "reviewedAt" timestamptz,
                PRIMARY KEY ("fromStandardId", "relationType", "toStandardId"))'''))
            await connection.execute(text('''CREATE TEMP TABLE "StudentSkillState" (
                "studentId" text, "skillId" text, status text)'''))
            catalog = json.loads((SEED_DIRECTORY / 'oas_to_8track.json').read_text())['mappings']
            await connection.execute(text('''INSERT INTO "OASStandard" (code,description,grade,subject,track,"progressionLane")
                VALUES (:code,:description,:grade,:subject,:track,:code)'''), [
                dict(code=(row.get('standard_node') or row.get('neo4j_node'))['properties']['id'],
                     description=row['standard_text'], grade=row['grade'], subject=row['subject'],track=row['track'])
                for row in catalog
            ])
            await connection.commit()
            factory = async_sessionmaker(connection, expire_on_commit=False)
            with patch('scripts.import_standard_progressions._get_session_factory', return_value=factory):
                await run(MAPPING, apply=True, allow_verified=True)
                await run(MAPPING, apply=True, allow_verified=True)
            count = (await connection.execute(text('SELECT count(*) FROM "OASStandardRelation"'))).scalar_one()
            assert count == 30  # restart must not duplicate or discard reviewed provenance
            await connection.execute(text('''INSERT INTO "StudentSkillState" VALUES
                ('child','MATHEM_G5_5.N.1.3','developing'),
                ('sibling','MATHEM_G5_5.N.1.3','secure'),
                ('child','MATHEM_G5_5.A.1.1','demonstrated')'''))
            await connection.commit()
            with patch('app.connections.curriculum_graph._get_session_factory', return_value=factory):
                rows = await curriculum_graph.get_grade_standards('child', 6, 1000, None)
                by_id = {row['id']: row for row in rows}
                assert by_id['MATHEM_G5_5.N.1.3']['grade'] == 5
                assert not by_id['MATHEM_G6_6.N.3.1']['prerequisites_met']
                assert not by_id['MATHEM_G6_6.N.3.2']['prerequisites_met']
                await connection.execute(text('''UPDATE "StudentSkillState" SET status='demonstrated'
                    WHERE "studentId"='child' AND "skillId"='MATHEM_G5_5.N.1.3' '''))
                await connection.commit()
                rows = await curriculum_graph.get_grade_standards('child', 6, 1000, None)
                by_id = {row['id']: row for row in rows}
                assert by_id['MATHEM_G6_6.N.3.1']['prerequisites_met']
                assert not by_id['MATHEM_G6_6.N.3.2']['prerequisites_met']
                await connection.execute(text('''INSERT INTO "StudentSkillState" VALUES
                    ('child','MATHEM_G6_6.N.3.1','demonstrated')'''))
                await connection.commit()
                rows = await curriculum_graph.get_grade_standards('child', 6, 1000, None)
                assert next(row for row in rows if row['id']=='MATHEM_G6_6.N.3.2')['prerequisites_met']
    finally:
        await engine.dispose()
