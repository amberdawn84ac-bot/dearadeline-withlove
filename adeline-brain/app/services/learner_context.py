"""Hydrate canonical adaptation from the learner's live profile and evidence."""
from __future__ import annotations

import logging

from app.agents.adapter import AdaptationRequest
from app.algorithms.bkt_tracker import get_mastery_map
from app.config import get_db_conn

logger = logging.getLogger(__name__)


async def adaptation_for(student_id: str, grade_level: str, track: str) -> AdaptationRequest:
    interests: list[str] = []
    modality = "text"
    try:
        conn = await get_db_conn()
        try:
            row = await conn.fetchrow(
                'SELECT "interests", "learningStyle" FROM "User" WHERE "id" = $1', student_id
            )
        finally:
            await conn.close()
        if row:
            interests = list(row["interests"] or [])
            modality = str(row["learningStyle"] or "text").lower()
    except Exception as exc:
        logger.warning("Learner profile unavailable for adaptation: %s", exc)

    proficiency = await get_mastery_map(student_id, track)
    mastery = sum(proficiency.values()) / len(proficiency) if proficiency else 0.1
    return AdaptationRequest(
        grade_level=grade_level,
        track=track,
        interests=interests,
        preferred_modality=modality,
        bkt_pL=mastery,
        decay_adjusted_mastery=mastery,
        proficiency_map=proficiency,
    )


def learner_contribution(contract: dict, adaptation: AdaptationRequest) -> dict:
    """Select the learner's role and assessment criteria without making a second lesson."""
    try:
        grade = 0 if adaptation.grade_level.upper() == "K" else int(adaptation.grade_level)
    except (TypeError, ValueError):
        grade = 0
    band = "elementary" if grade <= 5 else "middle" if grade <= 8 else "high_school"
    demonstration = contract.get("demonstration_contract") or {}
    real_task = contract.get("real_world_task") or {}
    experience_design = contract.get("experience_design") or {}
    portfolio = contract.get("portfolio_task") or {}
    role = (contract.get("family_roles") or {}).get(band) or real_task.get("individual_contribution") or "Make one meaningful contribution to the shared investigation."
    interests = adaptation.interests[:3]
    return {
        "role": role,
        "prompt": demonstration.get("learner_prompt") or real_task.get("individual_contribution") or role,
        "artifact_prompt": demonstration.get("artifact_prompt") or "Preserve a photo, recording, drawing, model, calculation, or explanation that shows what you discovered.",
        "success_criteria": list(demonstration.get("success_criteria") or []),
        "response_options": [
            "photo or video", "audio", "drawing or design sketch", "written explanation",
            "calculation, measurement, graph, or data", "model, prototype, performance, or code",
        ],
        "experience_mode": experience_design.get("primary_mode") or "investigation",
        "learner_facing_choices": list(experience_design.get("learner_facing_choices") or []),
        "evidence_to_preserve": {
            "process": list(portfolio.get("process_evidence") or []),
            "product": list(portfolio.get("product_evidence") or []),
            "failure_and_revision": list(portfolio.get("failure_and_revision_evidence") or []),
        },
        "mastery_evidence_map": list(contract.get("mastery_evidence_map") or []),
        "interest_connections": interests,
        "mastery_snapshot": round(adaptation.bkt_pL, 3),
        "portfolio_destination": True,
        "credit_requires_demonstrated_understanding": True,
    }
