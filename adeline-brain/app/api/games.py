"""Curriculum-grounded mini-game API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agents.mission_team import GameSmithAgent
from app.api.middleware import get_current_user_id

router = APIRouter(prefix="/games", tags=["games"])


class GameBuildRequest(BaseModel):
    student_id: str
    topic: str
    track: str
    grade_level: str = "8"


@router.post("/build")
async def build_game(body: GameBuildRequest, current_user_id: str = Depends(get_current_user_id)):
    if body.student_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot build a game for another student")
    game = await GameSmithAgent().build_playable(body.topic, body.track, body.grade_level)
    if not game.get("canonical_ready"):
        raise HTTPException(status_code=409, detail="The canonical lesson must be ready before GameSmith can build this game")
    if not game.get("interactive"):
        raise HTTPException(status_code=503, detail="GameSmith could not build the interactive challenge yet")
    return game
