"""Private household feed for messages and shared project/game invitations."""
from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from app.api.middleware import get_current_user_id
from app.config import get_db_conn
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/family", tags=["family"])


class FamilyPostCreate(BaseModel):
    kind: Literal["MESSAGE", "PROJECT", "GAME"] = "MESSAGE"
    title: str | None = Field(default=None, max_length=120)
    body: str = Field(..., min_length=1, max_length=2000)
    resource_url: HttpUrl | None = None


async def _identity(conn, user_id: str) -> tuple[str, str]:
    row = await conn.fetchrow(
        'SELECT id, name, role, "parentId" FROM "User" WHERE id = $1', user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Family member not found.")
    role = str(row["role"]).upper()
    if role == "PARENT":
        return user_id, str(row["name"] or "Parent")
    if role == "STUDENT" and row["parentId"]:
        return str(row["parentId"]), str(row["name"] or "Learner")
    raise HTTPException(status_code=409, detail="Connect a parent account before opening the family room.")


@router.get("/feed")
async def family_feed(user_id: str = Depends(get_current_user_id)):
    conn = await get_db_conn()
    try:
        household_id, _ = await _identity(conn, user_id)
        members = await conn.fetch(
            '''SELECT id, name, role, "gradeLevel" FROM "User"
               WHERE id = $1 OR "parentId" = $1 ORDER BY role, name''',
            household_id,
        )
        posts = await conn.fetch(
            '''SELECT id, "authorId", "authorName", kind, title, body, "resourceUrl",
                      "createdAt"::text AS "createdAt"
               FROM "FamilyPost" WHERE "householdId" = $1
               ORDER BY "createdAt" DESC LIMIT 100''',
            household_id,
        )
        return {
            "household_id": household_id,
            "members": [dict(row) for row in members],
            "posts": [dict(row) for row in posts],
        }
    finally:
        await conn.close()


@router.post("/feed", status_code=201)
async def create_family_post(body: FamilyPostCreate, user_id: str = Depends(get_current_user_id)):
    await enforce_rate_limit("family-post", user_id, limit=20)
    conn = await get_db_conn()
    try:
        household_id, author_name = await _identity(conn, user_id)
        post_id = str(uuid4())
        row = await conn.fetchrow(
            '''INSERT INTO "FamilyPost"
                 (id, "householdId", "authorId", "authorName", kind, title, body, "resourceUrl", "createdAt")
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
               RETURNING id, "authorId", "authorName", kind, title, body, "resourceUrl",
                         "createdAt"::text AS "createdAt"''',
            post_id, household_id, user_id, author_name, body.kind,
            body.title.strip() if body.title else None, body.body.strip(),
            str(body.resource_url) if body.resource_url else None,
        )
        return dict(row)
    finally:
        await conn.close()
