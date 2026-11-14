"""Issue #92: service-backed regression for the saved investigation path."""

import asyncio
import json
import os
import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from app import config
from app.agents import cognitive_twin
from app.api import classrooms, experience_builder, journal, learning_plan, spaces
from app.connections import canonical_store, redis_client
from app.connections.daily_plan_store import daily_plan_store
from app.connections.family_unit_store import family_unit_store
from app.connections.journal_store import journal_store
from app.curriculum.family_style import CANONICAL_FORMAT_VERSION
from app.curriculum.estuary_classroom import ESTUARY_ITEM, ESTUARY_SOURCE, estuary_classroom
from app.main import app as production_app
from app.services import instructional_resources, rate_limit
from tests.test_today_persistence import _saved_plan

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_FAMILY_JOURNEY") != "1",
    reason="Requires the disposable Postgres and Redis CI services",
)


def checked(response):
    assert response.is_success, response.text
    return response.json()


def token(student_id):
    return jwt.encode(
        {"sub": student_id, "aud": "authenticated", "exp": time.time() + 300},
        config.STUDENT_JWT_SECRET,
        algorithm="HS256",
    )


def disposable_redis():
    from urllib.parse import urlparse

    db = urlparse(config.POSTGRES_DSN)
    redis_url = urlparse(config.REDIS_URL)
    loopback = {"localhost", "127.0.0.1", "::1"}
    assert config.ADELINE_ENV == "test" and db.hostname in loopback
    assert db.path in {"/adeline_test", "/adeline_ci"}
    assert redis_url.hostname in loopback
    return Redis.from_url(config.REDIS_URL, decode_responses=True)


@pytest.fixture(autouse=True)
def isolate_database_pool(monkeypatch):
    # Other tests may have used a pool created for a different pytest event loop.
    monkeypatch.setattr(config, "_db_pool", None)
    monkeypatch.setattr(config, "_db_pool_lock", None)


@pytest.mark.asyncio
async def test_saved_family_investigation_preserves_evidence_and_credits_once(monkeypatch):
    # Exercise the original Space contract from #92 separately; this router
    # is no longer mounted in the live app, which now uses classroom scenes.
    redis = disposable_redis()
    suffix = uuid4().hex
    learner, sibling, parent = (f"journey-{role}-{suffix}" for role in ("learner", "sibling", "parent"))
    topic = f"Testing water density — {suffix}"
    track = "CREATION_SCIENCE"
    lesson_id = f"density-{suffix}"
    concept_id, other_concept = f"salinity-{suffix}", f"tides-{suffix}"
    standard = "SCI.JOURNEY.DENSITY"
    concept = "Salt and water density"
    roles = {
        "elementary": "Draw where each water sample settled.",
        "middle": "Compare the samples using measurements.",
        "high_school": "Explain what the controls rule out.",
    }
    blocks = [
        {
            "block_id": f"density-{index}", "block_type": kind, "title": title,
            "content": content, "family_style": True,
            "canonical_format_version": CANONICAL_FORMAT_VERSION, "family_roles": roles,
        }
        for index, (kind, title, content) in enumerate([
            ("TEXT", "Make a prediction", "Predict which equal-volume water sample will be heavier."),
            ("EXPERIMENT", "Compare the samples", "Measure and compare the masses of equal volumes."),
            ("QUIZ", "Explain the result", "Use your measured masses to explain which sample was denser."),
        ])
    ]
    blocks[0]["metadata"] = {"canonical_contract": {
        "family_roles": roles,
        "unit_plan": {
            "essential_concepts": [
                {"concept_id": concept_id, "concept": concept},
                {"concept_id": other_concept, "concept": "Tides"},
            ],
            "lessons": [{
                "lesson_id": lesson_id, "title": "Compare water density",
                "block_ids": [block["block_id"] for block in blocks], "concept_ids": [concept_id],
            }],
        },
    }}

    async def evaluate(messages):
        answer = messages[-1].content
        correct = answer != "I clicked Next."
        return SimpleNamespace(content=json.dumps({
            "adeline_message": "Thanks for recording your work." if correct else "Show your observation first.",
            "evaluation": "correct" if correct else "not_answered",
            "recommended_action": "advance" if correct else "stay",
            "is_waiting_for_user": True,
        }))

    async def no_extra_resources(state, *_args):
        return state

    monkeypatch.setattr(spaces, "_space_turn_llm", lambda: SimpleNamespace(ainvoke=evaluate))
    monkeypatch.setattr(instructional_resources, "prepare_instructional_resource", no_extra_resources)
    monkeypatch.setattr(spaces, "_topic_oas_standards", AsyncMock(return_value=[
        {"standard_id": standard, "subject": "SCI", "grade": 8},
    ]))
    author = AsyncMock(side_effect=AssertionError("A seeded canonical must never be re-authored"))
    monkeypatch.setattr(experience_builder, "_author", author)
    monkeypatch.setattr(experience_builder.resource_router, "search", AsyncMock(return_value={}))
    for module in (canonical_store, cognitive_twin, learning_plan, rate_limit, redis_client):
        monkeypatch.setattr(module, "redis_client", redis)

    app = FastAPI()
    for module in (experience_builder, learning_plan, spaces, journal):
        app.include_router(module.router)

    try:
        assert await redis.ping()
        await journal_store.connect(retries=1)
        conn = await config.get_db_conn()
        try:
            for user_id, role, grade, owner in [
                (parent, "PARENT", None, None),
                (learner, "STUDENT", "8", parent),
                (sibling, "STUDENT", "11", parent),
            ]:
                await conn.execute(
                    'INSERT INTO "User"(id,name,email,role,"gradeLevel","parentId") VALUES ($1,$2,$3,$4,$5,$6)',
                    user_id, user_id, f"{user_id}@example.test", role, grade, owner,
                )
        finally:
            await conn.close()

        today = _saved_plan()
        today.update(student_id=learner, suggestions=[])
        today["family_context"].update(household_id=parent, shared_with_siblings=True, sibling_count=1)
        await daily_plan_store.save(learner, datetime.now(ZoneInfo("America/Chicago")).date(), today)
        await family_unit_store.enqueue(parent, "Water investigation", [{"canonical_topic": topic, "track": track}])
        slug = canonical_store.canonical_slug(topic, track)
        await canonical_store.canonical_store.save(slug, {
            "id": str(uuid4()), "topic": topic, "title": "Water density",
            "track": track, "blocks": blocks, "oas_standards": [],
            "researcher_activated": False, "agent_name": "CI seed",
        })
        cache_key = f"{canonical_store.REDIS_PREFIX}{slug}"
        await redis.delete(cache_key)  # First open must recover the durable canonical.

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
            headers={"Authorization": f"Bearer {token(learner)}"},
        ) as client:
            plan = checked(await client.get(f"/learning-plan/{learner}/today"))
            task = plan["family_investigation"]
            assert task["canonical_topic"] == topic
            item = task["id"]
            build_path = "/experience/build"
            request = {
                "student_id": learner, "plan_item_id": item, "topic": task["canonical_topic"],
                "track": task["track"], "delivery_mode": task["delivery_mode"],
                "shared_investigation_id": task["shared_investigation_id"], "grade_level": "8",
            }
            response = await client.post(build_path, json=request)
            assert response.is_success, response.text
            frames = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
            assert frames[-1]["type"] == "done", frames[-1]
            assert frames[-1]["credits_awarded"] == []
            experience_id = frames[-1]["lesson_id"]
            assert json.loads(await redis.get(cache_key))["title"] == "Water density"
            retry = await client.post(build_path, json=request)
            assert retry.is_success and experience_id in retry.text and '"type": "done"' in retry.text
            author.assert_not_awaited()

            path = f"/brain/spaces/{learner}/{item}"
            assert (await client.get(path, headers={"Authorization": f"Bearer {token(sibling)}"})).status_code == 403
            opened = checked(await client.get(path))
            assert opened["experience_id"] == experience_id
            assert checked(await client.get(path))["session_id"] == opened["session_id"]

            async def turn(answer, version):
                return await client.post(f"{path}/turn", json={"user_message": answer, "expected_version": version})

            insufficient = checked(await turn("I clicked Next.", opened["version"]))
            assert insufficient["completed_block_ids"] == []
            portfolio = f"/journal/portfolio/{learner}"
            assert checked(await client.get(portfolio))["items"] == []

            state = insufficient
            for answer in [
                "I predict the saltwater will weigh more.",
                "I measured 103 g for 100 mL of saltwater and 100 g for 100 mL of fresh water.",
                "With equal volumes, the saltwater's higher mass means it had higher density.",
            ]:
                submitted_version = state["version"]
                state = checked(await turn(answer, submitted_version))
                if state["status"] != "completed":
                    assert state["credited_this_session"] == []
            assert state["status"] == "completed"
            assert state["credited_this_session"] == [concept]
            assert (await turn(answer, submitted_version)).status_code == 409
            assert checked(await turn(answer, state["version"]))["credited_this_session"] == []
            items = checked(await client.get(portfolio))["items"]
            assert [(entry["lesson_id"], entry["plan_item_id"], entry["evidence_only"]) for entry in items] == [
                (lesson_id, item, False),
            ]

        conn = await config.get_db_conn()
        try:
            assert await conn.fetchval(
                'SELECT count(*) FROM "StudentExperience" WHERE "studentId"=$1 AND "planItemId"=$2', learner, item,
            ) == 1
            assert await conn.fetchval(
                'SELECT count(*) FROM "EvidenceAttempt" WHERE "studentId"=$1 AND "lessonId"=$2', learner, lesson_id,
            ) == 1
            assert [tuple(row) for row in await conn.fetch(
                'SELECT "skillId",status,"evidenceCount" FROM "StudentSkillState" WHERE "studentId"=$1 ORDER BY "skillId"',
                learner,
            )] == [(standard, "secure", 1), (concept_id, "secure", 1)]
            assert [tuple(row) for row in await conn.fetch(
                'SELECT "standardId",proficiency,"evidenceCount" FROM "StandardMastery" WHERE "studentId"=$1',
                learner,
            )] == [(standard, "EXTENDING", 1)]
            for _ in range(100):
                card = await conn.fetchrow(
                    'SELECT "dueAt" FROM "SpacedRepetitionCard" WHERE "studentId"=$1 AND "conceptId"=$2',
                    learner, concept_id,
                )
                if card and card["dueAt"]:
                    break
                await asyncio.sleep(0.05)
            assert card and card["dueAt"], "Expected the background BKT/SM-2 scheduling write"
        finally:
            await conn.close()
    finally:
        await config.close_db_pool()
        await redis.aclose()


@pytest.mark.asyncio
async def test_mounted_classroom_saves_portfolio_work_and_reviews_the_mapped_skill_once(monkeypatch):
    redis = disposable_redis()
    suffix = uuid4().hex
    learner = f"classroom-{suffix}"
    parent = f"classroom-parent-{suffix}"
    skill = f"estuary-density-{suffix}"
    first_request = {
        "topic": f"Compare estuary layers {suffix}",
        "track": "CREATION_SCIENCE",
        "targets": [skill],
    }
    reference = estuary_classroom()
    second_request = {**first_request, "topic": f"Apply estuary evidence {suffix}"}
    scene = next(scene for scene in reference.scenes if scene.portfolio_title)
    text = "The saltwater stayed underneath the fresh water, so I would compare samples from both depths."
    second_text = "After stirring, the boundary weakened, so I would repeat paired depth samples at different tides."
    review = AsyncMock(side_effect=lambda _policy, schema, context: schema.model_validate({
        "findings": [{
            "skill_id": skill, "result": "demonstrated", "confidence": 0.95,
            "evidence_quote": context["learner_work"]["text"],
            "reasoning": "The learner linked layering to a depth-specific sampling decision.",
            "next_step": "Compare those samples under a different tide.",
        }],
    }))
    monkeypatch.setattr(classrooms, "generate_json", review)
    for module in (canonical_store, rate_limit, redis_client):
        monkeypatch.setattr(module, "redis_client", redis)
    try:
        assert await redis.ping()
        conn = await config.get_db_conn()
        try:
            for user_id, role, owner in [(parent, "PARENT", None), (learner, "STUDENT", parent)]:
                await conn.execute(
                    'INSERT INTO "User"(id,name,email,role,"parentId") VALUES ($1,$1,$2,$3,$4)',
                    user_id, f"{user_id}@example.test", role, owner,
                )
            await conn.execute(
                'INSERT INTO "CurriculumConcept"(id,title,description,track,difficulty) '
                "VALUES ($1,'Depth sampling','Compare samples at both depths.','CREATION_SCIENCE','EMERGING')",
                skill,
            )
        finally:
            await conn.close()

        for request, classroom in (
            (first_request, reference),
            (second_request, reference.model_copy(update={
                "scenes": [
                    s.model_copy(update={"learner_task": "Explain the changed boundary and design a sampling schedule."})
                    if s.id == scene.id else s for s in reference.scenes
                ],
            })),
        ):
            slug = classrooms.classroom_slug(classrooms.ClassroomRequest(**request), learner)
            await canonical_store.canonical_store.save(slug, {
                "id": slug, "topic": request["topic"], "title": reference.blueprint.title,
                "track": request["track"], "oas_standards": [],
                "researcher_activated": False, "agent_name": "CI seed",
                "blocks": [{"metadata": {
                    "classroom": classroom.model_dump(),
                    "source_context": [ESTUARY_SOURCE],
                }}],
            })
        async with AsyncClient(
            transport=ASGITransport(app=production_app), base_url="http://test",
            headers={"Authorization": f"Bearer {token(learner)}"},
        ) as client:
            collection = f"/brain/classroom/{learner}"
            estuary = checked(await client.post(f"{collection}/{ESTUARY_ITEM}", json=first_request))
            assert estuary["phase"] == "ready"
            path = f"{collection}/{suffix}"
            opened = checked(await client.post(path, json=first_request))
            assert checked(await client.get(path))["id"] == opened["id"]
            assert {row["item_id"] for row in checked(await client.get(collection))} == {ESTUARY_ITEM, suffix}
            assert opened["phase"] == "ready"
            review.assert_not_awaited()

            submission = {"scene_id": scene.id, "text": text, "submission_key": suffix}
            saved = checked(await client.post(f"{path}/responses", json=submission))
            assert saved["saved"] is True and "assessment" not in saved
            assert checked(await client.post(f"{path}/responses", json=submission)) == saved
            altered = {**submission, "text": "This is different work."}
            assert (await client.post(f"{path}/responses", json=altered)).status_code == 409
            portfolio = checked(await client.get(f"/brain/journal/portfolio/{learner}"))
            assert [(item["reflection"], item["evidence_only"]) for item in portfolio["items"]] == [(text, True)]
            review.assert_not_awaited()

            assessment = {"submission_key": suffix}
            reviewed = checked(await client.post(f"{path}/assessment", json=assessment))
            assert reviewed["status"] == "reviewed"
            assert [(f["skill_id"], f["result"]) for f in reviewed["findings"]] == [(skill, "demonstrated")]
            assert checked(await client.post(f"{path}/assessment", json=assessment)) == reviewed
            review.assert_awaited_once()
            credit_path = f"/brain/credits/{learner}"
            reviewer = {"Authorization": f"Bearer {token(parent)}"}
            scope = checked(await client.post(f"{credit_path}/courses", headers=reviewer, json={
                "title": "Estuary field sampling",
                "track": first_request["track"],
                "bucket": "SCIENCE_CORE",
                "credit_units": 0.5,
                "skill_ids": [skill],
                "rationale": "Compare sample depths using independent evidence across two investigations.",
            }))
            approval_path = f"{credit_path}/approve/{scope['id']}"
            assert (await client.post(approval_path, headers=reviewer)).status_code == 409
            credits = checked(await client.get(credit_path))
            assert credits["approvedCourses"] == []

            second_path = f"{collection}/transfer-{suffix}"
            assert checked(await client.post(second_path, json=second_request))["phase"] == "ready"
            second_submission = {**submission, "submission_key": f"transfer-{suffix}", "text": second_text}
            assert checked(await client.post(f"{second_path}/responses", json=second_submission))["saved"]
            assert checked(await client.post(f"{second_path}/assessment", json={
                "submission_key": second_submission["submission_key"],
            }))["status"] == "reviewed"
            assert (await client.post(approval_path)).status_code == 403
            assert checked(await client.post(approval_path, headers=reviewer))["isApproved"]
            assert checked(await client.post(approval_path, headers=reviewer))["isApproved"]
            courses = checked(await client.get(credit_path))["approvedCourses"]
            assert [(course["proposalId"], course["creditUnits"]) for course in courses] == [(scope["id"], 0.5)]

        conn = await config.get_db_conn()
        try:
            assert [tuple(row) for row in await conn.fetch(
                'SELECT "skillId",status,"evidenceCount" FROM "StudentSkillState" WHERE "studentId"=$1',
                learner,
            )] == [(skill, "demonstrated", 2)]
            assert await conn.fetchval(
                'SELECT count(*) FROM "TranscriptEntry" WHERE "studentId"=$1 AND "sealedAt" IS NOT NULL',
                learner,
            ) == 1
        finally:
            await conn.close()
    finally:
        await config.close_db_pool()
        await redis.aclose()
