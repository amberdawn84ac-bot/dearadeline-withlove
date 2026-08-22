"""PostgreSQL source of truth for a learner's dated Today plan."""
from __future__ import annotations

import json
from datetime import date

from app.config import get_db_conn


class DailyPlanStore:
    async def get(self, student_id: str, for_date: date) -> dict | None:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT "planJson" FROM "DailyPlan" WHERE "studentId" = $1 AND "forDate" = $2',
                student_id, for_date,
            )
            return dict(row["planJson"]) if row else None
        finally:
            await conn.close()

    async def save(self, student_id: str, for_date: date, plan: dict) -> None:
        conn = await get_db_conn()
        try:
            await conn.execute(
                '''INSERT INTO "DailyPlan" ("studentId", "forDate", "planJson", "createdAt", "updatedAt")
                   VALUES ($1, $2, $3::jsonb, NOW(), NOW())
                   ON CONFLICT ("studentId", "forDate") DO UPDATE SET
                     "planJson" = EXCLUDED."planJson", "updatedAt" = NOW()''',
                student_id, for_date, json.dumps(plan),
            )
        finally:
            await conn.close()

    async def invalidate(self, student_id: str, for_date: date | None = None) -> None:
        conn = await get_db_conn()
        try:
            if for_date:
                await conn.execute('DELETE FROM "DailyPlan" WHERE "studentId" = $1 AND "forDate" = $2', student_id, for_date)
            else:
                await conn.execute('DELETE FROM "DailyPlan" WHERE "studentId" = $1 AND "forDate" >= CURRENT_DATE', student_id)
        finally:
            await conn.close()


daily_plan_store = DailyPlanStore()
