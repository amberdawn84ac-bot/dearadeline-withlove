"""Curriculum-grounded mini-game API."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.agents.mission_team import GameSmithAgent
from app.api.middleware import verify_student_access

router = APIRouter(prefix="/games", tags=["games"])


class GameBuildRequest(BaseModel):
    student_id: str
    topic: str
    track: str
    grade_level: str = "8"


@router.post("/build")
async def build_game(body: GameBuildRequest, authorization: str | None = Header(default=None)):
    await verify_student_access(body.student_id, authorization)
    game = await GameSmithAgent().build_playable(body.topic, body.track, body.grade_level)
    if not game.get("canonical_ready"):
        raise HTTPException(status_code=409, detail="The canonical lesson must be ready before GameSmith can build this game")
    if not game.get("interactive"):
        raise HTTPException(status_code=503, detail="GameSmith could not build the interactive challenge yet")
    return game
