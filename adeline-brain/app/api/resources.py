"""Approved outside-resource search endpoint."""
from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from app.api.middleware import verify_student_access
from app.services.resource_router import ResourceQuery, resource_router

router = APIRouter(prefix="/resources", tags=["resources"])


class ResourceSearchRequest(BaseModel):
    student_id: str
    topic: str = Field(min_length=2, max_length=240)
    track: str
    grade_level: str = "8"
    objective: str = ""
    resource_types: list[str] = Field(default_factory=list)
    interactive_preferred: bool = True
    commercial_context: bool = True
    limit: int = Field(default=5, ge=1, le=12)


@router.post("/search")
async def search_resources(body: ResourceSearchRequest, authorization: str | None = Header(default=None)):
    await verify_student_access(body.student_id, authorization)
    return await resource_router.search(ResourceQuery(
        topic=body.topic, track=body.track, grade_level=body.grade_level,
        objective=body.objective, resource_types=tuple(body.resource_types),
        interactive_preferred=body.interactive_preferred,
        commercial_context=body.commercial_context, limit=body.limit,
    ))
