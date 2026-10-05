"""Exercise the production prerequisite query against isolated Postgres tables."""
import os
from unittest.mock import patch
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.connections.curriculum_graph import curriculum_graph


@pytest.mark.asyncio
async def test_only_this_learners_demonstration_unlocks_next_concept():
    dsn = os.getenv('POSTGRES_DSN')
    if not dsn:
        pytest.skip('Postgres is exercised in GitHub CI')
    engine = create_async_engine(dsn.replace('postgresql://', 'postgresql+asyncpg://', 1))
    try:
        async with engine.connect() as connection:
            for statement in [
                '''CREATE TEMP TABLE "CurriculumConcept" (id text PRIMARY KEY,title text,description text,track "Track",difficulty text,"standardCode" text,"gradeBand" text)''',
                '''CREATE TEMP TABLE "CurriculumConceptPrerequisite" ("conceptId" text,"prerequisiteId" text)''',
                '''CREATE TEMP TABLE "StudentSkillState" ("studentId" text,"skillId" text,status text)''',
                '''INSERT INTO "CurriculumConcept" VALUES ('fraction','Fractions','','APPLIED_MATHEMATICS','','','6'),('ratio','Ratios','','APPLIED_MATHEMATICS','','','6')''',
                '''INSERT INTO "CurriculumConceptPrerequisite" VALUES ('ratio','fraction')''',
                '''INSERT INTO "StudentSkillState" VALUES ('child','fraction','developing'),('sibling','fraction','secure')''',
            ]:
                await connection.execute(text(statement))
            await connection.commit()
            factory = async_sessionmaker(connection, expire_on_commit=False)
            with patch('app.connections.curriculum_graph._get_session_factory', return_value=factory):
                first = await curriculum_graph.get_zpd_candidates('child', 'APPLIED_MATHEMATICS')
                assert [row['concept_id'] for row in first] == ['fraction']
                await connection.execute(text('''UPDATE "StudentSkillState" SET status='demonstrated' WHERE "studentId"='child' '''))
                await connection.commit()
                second = await curriculum_graph.get_zpd_candidates('child', 'APPLIED_MATHEMATICS')
                assert [row['concept_id'] for row in second] == ['ratio']
    finally:
        await engine.dispose()
