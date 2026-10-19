"""Actual PostgreSQL engine and statements; controlled model output, no production data."""

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.api import classrooms, credits
from app.curriculum.classroom import CLASSROOM_VERSION
from app.services.classroom_assessment import (
    Finding,
    Review,
    assess_saved_work,
    checked_findings,
)
from app.services.curriculum_state import evaluate_evidence
from app.services.learning_loop import course_progress
from fastapi import HTTPException

from tests.test_classroom import blueprint, scene

ROOT = Path(__file__).resolve().parents[2]


class DB:
    def __init__(self):
        self.process = subprocess.Popen(
            ["node", str(Path(__file__).with_name("pglite_bridge.cjs"))],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )

    def query(self, sql, args=(), exec=False):
        self.process.stdin.write(
            json.dumps(
                {
                    "sql": sql,
                    "args": [
                        str(x) if isinstance(x, int) and abs(x) > 2**53 else x
                        for x in args
                    ],
                    "exec": exec,
                }
            )
            + "\n"
        )
        self.process.stdin.flush()
        response = self.process.stdout.readline()
        if not response:
            raise RuntimeError(
                "PostgreSQL test bridge stopped. Run pnpm install first."
            )
        result = json.loads(response)
        if "error" in result:
            raise RuntimeError(result["error"] + "\n" + sql)
        return result["rows"]

    async def fetch(self, sql, *args):
        return self.query(sql, args)

    async def fetchrow(self, sql, *args):
        rows = self.query(sql, args)
        return rows[0] if rows else None

    async def fetchval(self, sql, *args):
        row = await self.fetchrow(sql, *args)
        return next(iter(row.values())) if row else None

    async def execute(self, sql, *args):
        return self.query(sql, args)

    async def close(self):
        pass

    def transaction(self):
        db = self

        class Transaction:
            async def __aenter__(self):
                await db.execute("BEGIN")

            async def __aexit__(self, typ, value, tb):
                await db.execute("ROLLBACK" if typ else "COMMIT")

        return Transaction()


@pytest.fixture
def db():
    if (
        not shutil.which("node")
        or not (ROOT / "node_modules/@electric-sql/pglite").exists()
    ):
        pytest.skip("Run pnpm install for the PostgreSQL integration engine")
    db = DB()
    tracks = ",".join("'" + t.value + "'" for t in classrooms.Track)
    db.query(
        f"""CREATE TYPE "Track" AS ENUM ({tracks});
        CREATE TYPE "CreditType" AS ENUM ('CORE','ELECTIVE','FINE_ARTS');
        CREATE TABLE "User" (id text PRIMARY KEY,role text,"gradeLevel" text);
        INSERT INTO "User" VALUES ('child','STUDENT','9'),('parent','PARENT',NULL),('other','STUDENT','9');
        CREATE TABLE "StudentExperience"(id text PRIMARY KEY,"studentId" text,"planItemId" text,"metadataJson" jsonb,"updatedAt" timestamp);
        CREATE TABLE "CurriculumConcept"(id text PRIMARY KEY,title text,track "Track");
        CREATE TABLE "OASStandard"(code text PRIMARY KEY,description text,track text);
        CREATE TABLE "TranscriptEntry"(id text PRIMARY KEY,"studentId" text,"lessonId" text,"courseTitle" text,track "Track",
            "oasStandards" text[],"activityDescription" text,"creditHours" float,"creditType" "CreditType","completedAt" timestamp,"sealedAt" timestamp);
        INSERT INTO "CurriculumConcept" VALUES ('ratio-1','Compare ratios','APPLIED_MATHEMATICS');
    """,
        exec=True,
    )
    original = (
        ROOT
        / "adeline-brain/prisma/migrations/20261003_unified_curriculum/migration.sql"
    ).read_text()
    db.query(
        original[
            original.index('CREATE TABLE "EvidenceAttempt"') : original.index(
                'CREATE TABLE "TimelineCard"'
            )
        ],
        exec=True,
    )
    db.query(
        (
            ROOT
            / "adeline-brain/prisma/migrations/20261019_learning_loop/migration.sql"
        ).read_text(),
        exec=True,
    )
    yield db
    db.process.terminate()
    db.process.wait(timeout=10)


def finding():
    return Finding(
        skill_id="ratio-1",
        result="demonstrated",
        confidence=0.95,
        evidence_quote="same ratio",
        reasoning="The learner correctly applies proportional reasoning.",
        next_step="Compare a fresh pair of mixtures and explain your reasoning.",
    )


def test_ungrounded_or_unmapped_reviews_cannot_update_learning():
    work = {"text": "The mixtures have the same ratio because both amounts double."}
    assert (
        checked_findings(
            Review(findings=[finding()]), [{"id": "ratio-1"}], work, False
        )[0]["result"]
        == "needs_review"
    )
    assert (
        checked_findings(
            Review(findings=[finding().model_copy(update={"confidence": 0.5})]),
            [{"id": "ratio-1"}],
            work,
            True,
        )[0]["result"]
        == "needs_review"
    )
    for bad in [
        finding().model_copy(update={"skill_id": "invented"}),
        finding().model_copy(update={"evidence_quote": "words not written"}),
    ]:
        with pytest.raises(ValueError):
            checked_findings(Review(findings=[bad]), [{"id": "ratio-1"}], work, True)


async def seed_classroom(db):
    b = blueprint()
    b["scenes"][2]["purpose"] = "independent_check"
    scenes = [scene(i) for i in range(4)]
    scenes[2]["type"] = "pbl"
    scenes[2]["steps"] = ["Compare a new pair of mixtures."]
    b["scenes"][2]["type"] = "pbl"
    doc = {
        "format_version": CLASSROOM_VERSION,
        "phase": "ready",
        "canonical_slug": "mixtures",
        "blueprint": b,
        "scenes": scenes,
        "request": {"targets": ["ratio-1"]},
        "responses": {},
    }
    await db.execute(
        'INSERT INTO "StudentExperience" VALUES ($1,$2,$3,$4::jsonb,NOW())',
        "experience",
        "child",
        classrooms.plan_key("lesson"),
        json.dumps(doc),
    )


@pytest.mark.asyncio
async def test_saved_work_review_retry_progress_and_credit_are_durable(db):
    get = AsyncMock(return_value=db)
    with (
        patch("app.api.classrooms.get_db_conn", get),
        patch("app.services.classroom_assessment.get_db_conn", get),
        patch("app.services.curriculum_state.get_db_conn", get),
        patch(
            "app.services.learning_loop.refresh_learning_projection", new=AsyncMock()
        ),
        patch("app.api.credits.get_db_conn", get),
        patch("app.api.credits.refresh_learning_projection", new=AsyncMock()),
        patch(
            "app.services.classroom_assessment.refresh_learning_projection",
            new=AsyncMock(),
        ),
    ):
        await seed_classroom(db)
        text = "The mixtures have the same ratio because both amounts double and preserve the relative concentration."
        await classrooms.save_response(
            "child",
            "lesson",
            classrooms.Submission(
                scene_id="s2", text=text, submission_key="work-12345"
            ),
            _user="child",
        )
        assert await db.fetchval('SELECT COUNT(*) FROM "StudentSkillState"') == 0
        generate = AsyncMock(return_value=Review(findings=[finding()]))
        result = await assess_saved_work("child", "lesson", "work-12345", generate)
        assert result["status"] == "reviewed"
        await assess_saved_work("child", "lesson", "work-12345", generate)
        assert generate.await_count == 1
        assert await db.fetchval('SELECT "evidenceCount" FROM "StudentSkillState"') == 1
        scope = credits.ScopeRequest(
            title="Applied ratio studies",
            track="APPLIED_MATHEMATICS",
            bucket="MATH_CORE",
            credit_units=0.5,
            skill_ids=["ratio-1"],
            rationale="Parent-defined course scope includes independent applications across investigations.",
        )
        scope_id = (await credits.define_course("child", scope, _user="parent"))["id"]
        with pytest.raises(HTTPException) as early:
            await credits.approve_course_proposal("child", scope_id, _user="parent")
        assert early.value.status_code == 409
        attempt = await db.fetchval("""INSERT INTO "EvidenceAttempt"("studentId","canonicalSlug","lessonId",kind,content,"submissionKey")
            VALUES ('child','second','second-lesson','calculation','{"text":"Independent transfer calculation with explanation"}','second-work') RETURNING id""")
        await evaluate_evidence(
            attempt_id=attempt,
            student_id="child",
            skill_id="ratio-1",
            evaluator_id="parent",
            result="demonstrated",
            reasoning="Verified a new transfer calculation.",
        )
        with pytest.raises(HTTPException) as forbidden:
            await credits.approve_course_proposal("child", scope_id, _user="child")
        assert forbidden.value.status_code == 403
        await credits.approve_course_proposal("child", scope_id, _user="parent")
        await credits.approve_course_proposal("child", scope_id, _user="parent")
        assert await db.fetchval('SELECT COUNT(*) FROM "TranscriptEntry"') == 1
        dashboard = await credits.get_credit_dashboard("child", _user="parent")
        assert dashboard["approvedCourses"][0]["creditUnits"] == 0.5
        second = (await credits.define_course("child", scope, _user="parent"))["id"]
        with pytest.raises(HTTPException) as duplicate:
            await credits.approve_course_proposal("child", second, _user="parent")
        assert duplicate.value.status_code == 409
        assert await db.fetchval('SELECT COUNT(*) FROM "TranscriptEntry"') == 1
        await credits.set_student_profile(
            "child", "oklahoma_college_prep", _user="parent"
        )
        assert (await credits.get_student_profile("child", _user="child"))[
            "profileKey"
        ] == "oklahoma_college_prep"


@pytest.mark.asyncio
async def test_course_coverage_requires_evaluations_not_just_a_state_label(db):
    await db.execute(
        """INSERT INTO "StudentSkillState"("studentId","skillId",status) VALUES ('child','ratio-1','demonstrated')"""
    )
    result = await course_progress(
        db, {"id": "scope", "studentId": "child", "skillIds": ["ratio-1"]}
    )
    assert not result["ready"] and result["missing"] == ["ratio-1"]


@pytest.mark.asyncio
async def test_diagnosed_gap_becomes_practice_without_skipping_sequence(db):
    from app.api.learning_plan import LearningPlanResponse, _attach_evidence_practice

    from tests.test_skill_path import target
    from tests.test_today_persistence import _saved_plan

    get = AsyncMock(return_value=db)
    data = _saved_plan()
    data["student_id"] = "child"
    data["progression_checklist"] = [target().model_dump()]
    plan = LearningPlanResponse(**data)
    with (
        patch("app.api.classrooms.get_db_conn", get),
        patch("app.services.classroom_assessment.get_db_conn", get),
        patch("app.services.curriculum_state.get_db_conn", get),
        patch(
            "app.services.learning_loop.refresh_learning_projection", new=AsyncMock()
        ),
        patch(
            "app.services.classroom_assessment.refresh_learning_projection",
            new=AsyncMock(),
        ),
    ):
        await seed_classroom(db)
        work = "These mixtures must have the same ratio because both contain some amount of water."
        await classrooms.save_response(
            "child",
            "lesson",
            classrooms.Submission(
                scene_id="s2", text=work, submission_key="gap-work-1"
            ),
            _user="child",
        )
        bad = finding().model_copy(
            update={
                "result": "developing",
                "reasoning": "Containing water alone does not establish equivalent proportions.",
            }
        )
        await assess_saved_work(
            "child",
            "lesson",
            "gap-work-1",
            AsyncMock(return_value=Review(findings=[bad])),
        )
        with patch("app.config.get_db_conn", get):
            practice = await _attach_evidence_practice(plan, [])
        assert practice[0].skill_target.concept_id == "ratio-1"
        assert practice[0].assignment == bad.next_step
        assert plan.progression_checklist[0].concept_id == "ratio-1"


@pytest.mark.asyncio
async def test_provider_failure_preserves_work_and_retry_can_review_it(db):
    get = AsyncMock(return_value=db)
    with (
        patch("app.api.classrooms.get_db_conn", get),
        patch("app.services.classroom_assessment.get_db_conn", get),
        patch("app.services.curriculum_state.get_db_conn", get),
        patch(
            "app.services.learning_loop.refresh_learning_projection", new=AsyncMock()
        ),
        patch(
            "app.services.classroom_assessment.refresh_learning_projection",
            new=AsyncMock(),
        ),
    ):
        await seed_classroom(db)
        work = "The mixtures have the same ratio because both amounts double and preserve the relative concentration."
        await classrooms.save_response(
            "child",
            "lesson",
            classrooms.Submission(
                scene_id="s2", text=work, submission_key="retry-work"
            ),
            _user="child",
        )
        with pytest.raises(RuntimeError, match="provider unavailable"):
            await assess_saved_work(
                "child",
                "lesson",
                "retry-work",
                AsyncMock(side_effect=RuntimeError("provider unavailable")),
            )
        assert await db.fetchval('SELECT COUNT(*) FROM "EvidenceAttempt"') == 1
        assert await db.fetchval('SELECT COUNT(*) FROM "StudentSkillState"') == 0
        assert (
            await assess_saved_work(
                "child",
                "lesson",
                "retry-work",
                AsyncMock(return_value=Review(findings=[finding()])),
            )
        )["status"] == "reviewed"
