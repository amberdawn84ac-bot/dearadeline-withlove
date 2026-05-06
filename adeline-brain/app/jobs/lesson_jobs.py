"""
ARQ job: lesson generation off the HTTP request path.

Accepts a serialized LessonRequest dict + student_id.
Runs the full orchestrator (embed → canonical check → agent → registrar).
Stores result in Redis via ARQ's native result system (TTL: 1 hour).
"""
import logging
from app.schemas.api_models import LessonRequest

logger = logging.getLogger(__name__)


async def generate_lesson_job(ctx: dict, lesson_request_dict: dict, student_id: str) -> dict:
    """
    ARQ job function. ctx is provided by ARQ worker (contains shared connections).
    Returns a dict (JSON-serializable LessonResponse).
    """
    from app.agents.orchestrator import run_orchestrator

    logger.info(
        f"[ARQ] generate_lesson_job start — "
        f"student={student_id[:8]} topic={lesson_request_dict.get('topic', '')[:40]}"
    )
    lesson_request = LessonRequest(**lesson_request_dict)
    response = await run_orchestrator(lesson_request, student_id)
    logger.info(f"[ARQ] generate_lesson_job complete — lesson_id={response.lesson_id}")
    return response.model_dump(mode="json")
