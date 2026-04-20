"""
Cognitive Twin — Real-Time Student State Model

A lightweight Redis-backed model of each student's current cognitive state.
Updated after every interaction; read by ManagerAgent before routing.

State captures:
  - zpd_zone            Current ZPD zone (FRUSTRATED / IN_ZPD / BORED)
  - working_memory_load 0–1 float; rises with block density, falls with breaks
  - engagement_level    0–1 float; inferred from response length + velocity
  - frustration_score   0–1 float; accumulates on struggle signals
  - session_block_count Blocks delivered in current session
  - consecutive_struggles / consecutive_successes
  - interaction_velocity Interactions per minute (rolling 5-min window)
  - current_track       Track the student is currently studying

All values stored as JSON in Redis under key:  twin:{student_id}
TTL: 8 hours (single school day session)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.connections.redis_client import redis_client
from app.agents.pedagogy import ZPDZone

logger = logging.getLogger(__name__)

_TWIN_TTL_SECONDS = 8 * 60 * 60  # 8 hours
_TWIN_KEY_PREFIX  = "twin:"

# Decay constants — cognitive load/frustration decay toward baseline over time
_LOAD_DECAY_PER_MIN   = 0.04   # 4% per minute idle
_FRUSTRATION_DECAY_PER_MIN = 0.05


@dataclass
class CognitiveTwinState:
    student_id: str
    zpd_zone: str = ZPDZone.IN_ZPD.value
    working_memory_load: float = 0.3
    engagement_level: float = 0.6
    frustration_score: float = 0.0
    session_block_count: int = 0
    consecutive_struggles: int = 0
    consecutive_successes: int = 0
    current_track: Optional[str] = None
    interaction_velocity: float = 0.0
    last_interaction_iso: Optional[str] = None
    interaction_timestamps: list[str] = field(default_factory=list)  # ISO strings, last 10

    @property
    def last_interaction(self) -> Optional[datetime]:
        if self.last_interaction_iso:
            return datetime.fromisoformat(self.last_interaction_iso)
        return None

    def is_overloaded(self) -> bool:
        return self.working_memory_load > 0.78

    def is_frustrated(self) -> bool:
        return (
            self.frustration_score > 0.65
            or self.consecutive_struggles >= 3
            or self.zpd_zone == ZPDZone.FRUSTRATED.value
        )

    def needs_break(self) -> bool:
        return self.session_block_count >= 12 or self.working_memory_load > 0.88

    def should_elevate(self) -> bool:
        return (
            self.zpd_zone == ZPDZone.BORED.value
            or self.consecutive_successes >= 4
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["zpd_zone"] = self.zpd_zone
        return d


def _default_twin(student_id: str) -> CognitiveTwinState:
    return CognitiveTwinState(
        student_id=student_id,
        last_interaction_iso=datetime.now(timezone.utc).isoformat(),
    )


async def get_twin(student_id: str) -> CognitiveTwinState:
    """Load Cognitive Twin state from Redis. Returns a fresh state if absent."""
    try:
        raw = await redis_client.get(f"{_TWIN_KEY_PREFIX}{student_id}")
        if raw:
            data = json.loads(raw)
            twin = CognitiveTwinState(**data)
            return _apply_decay(twin)
    except Exception as e:
        logger.warning(f"[CognitiveTwin] Redis read failed for {student_id}: {e}")
    return _default_twin(student_id)


async def save_twin(twin: CognitiveTwinState) -> None:
    """Persist Cognitive Twin state to Redis with 8-hour TTL."""
    try:
        payload = json.dumps(twin.to_dict())
        await redis_client.set(
            f"{_TWIN_KEY_PREFIX}{twin.student_id}",
            payload,
            ex=_TWIN_TTL_SECONDS,
        )
    except Exception as e:
        logger.warning(f"[CognitiveTwin] Redis write failed for {twin.student_id}: {e}")


async def reset_session(student_id: str) -> CognitiveTwinState:
    """Reset session-level counters while preserving long-term engagement baseline."""
    twin = await get_twin(student_id)
    twin.session_block_count = 0
    twin.consecutive_struggles = 0
    twin.consecutive_successes = 0
    twin.working_memory_load = max(0.2, twin.working_memory_load - 0.3)
    twin.interaction_timestamps = []
    twin.last_interaction_iso = datetime.now(timezone.utc).isoformat()
    await save_twin(twin)
    return twin


def _apply_decay(twin: CognitiveTwinState) -> CognitiveTwinState:
    """Apply time-based decay to cognitive load and frustration."""
    if not twin.last_interaction_iso:
        return twin
    try:
        last = datetime.fromisoformat(twin.last_interaction_iso)
        now = datetime.now(timezone.utc)
        minutes_idle = (now - last).total_seconds() / 60.0

        if minutes_idle > 1:
            twin.working_memory_load = max(
                0.0,
                twin.working_memory_load - (_LOAD_DECAY_PER_MIN * minutes_idle),
            )
            twin.frustration_score = max(
                0.0,
                twin.frustration_score - (_FRUSTRATION_DECAY_PER_MIN * minutes_idle),
            )
    except Exception:
        pass
    return twin


async def update_from_response(
    student_id: str,
    response_text: str,
    was_correct: Optional[bool],
    zpd_zone: str,
    track: Optional[str] = None,
    block_count_delta: int = 0,
) -> CognitiveTwinState:
    """
    Update Cognitive Twin after a student interaction.

    Args:
        response_text:   The student's answer/message text.
        was_correct:     For quiz answers — True/False/None.
        zpd_zone:        ZPD zone detected by pedagogy agent.
        track:           Current track being studied.
        block_count_delta: How many new blocks were delivered.
    """
    twin = await get_twin(student_id)
    now = datetime.now(timezone.utc)

    # Track interaction velocity (rolling window, last 10 timestamps)
    twin.interaction_timestamps.append(now.isoformat())
    if len(twin.interaction_timestamps) > 10:
        twin.interaction_timestamps = twin.interaction_timestamps[-10:]
    twin.interaction_velocity = _calc_velocity(twin.interaction_timestamps)

    # Update engagement from response length
    response_len = len(response_text.strip())
    if response_len > 120:
        twin.engagement_level = min(1.0, twin.engagement_level + 0.08)
    elif response_len < 20:
        twin.engagement_level = max(0.0, twin.engagement_level - 0.05)

    # ZPD zone
    twin.zpd_zone = zpd_zone

    # Frustration accumulation / success streak
    if zpd_zone == ZPDZone.FRUSTRATED.value:
        twin.frustration_score   = min(1.0, twin.frustration_score + 0.15)
        twin.consecutive_struggles += 1
        twin.consecutive_successes = 0
    elif zpd_zone == ZPDZone.BORED.value:
        twin.frustration_score   = max(0.0, twin.frustration_score - 0.10)
        twin.consecutive_successes += 1
        twin.consecutive_struggles = 0
    else:
        twin.frustration_score = max(0.0, twin.frustration_score - 0.05)
        twin.consecutive_successes += 1
        twin.consecutive_struggles = max(0, twin.consecutive_struggles - 1)

    # Quiz-specific feedback
    if was_correct is True:
        twin.working_memory_load = max(0.0, twin.working_memory_load - 0.05)
        twin.consecutive_successes += 1
        twin.consecutive_struggles = max(0, twin.consecutive_struggles - 1)
    elif was_correct is False:
        twin.working_memory_load = min(1.0, twin.working_memory_load + 0.08)
        twin.consecutive_struggles += 1

    # Working memory load from block delivery
    if block_count_delta > 0:
        load_increase = block_count_delta * 0.06
        twin.working_memory_load = min(1.0, twin.working_memory_load + load_increase)
        twin.session_block_count += block_count_delta

    if track:
        twin.current_track = track

    twin.last_interaction_iso = now.isoformat()
    await save_twin(twin)
    return twin


def _calc_velocity(timestamps_iso: list[str]) -> float:
    """
    Calculate interaction velocity in interactions-per-minute
    using the last 5 minutes of interaction timestamps.
    """
    if len(timestamps_iso) < 2:
        return 0.0
    try:
        now = datetime.now(timezone.utc)
        five_min_ago = now - timedelta(minutes=5)
        recent = [
            datetime.fromisoformat(ts)
            for ts in timestamps_iso
            if datetime.fromisoformat(ts) >= five_min_ago
        ]
        if len(recent) < 2:
            return 0.0
        span_minutes = (max(recent) - min(recent)).total_seconds() / 60.0
        if span_minutes < 0.1:
            return float(len(recent))
        return round(len(recent) / span_minutes, 2)
    except Exception:
        return 0.0


def recommend_intervention(twin: CognitiveTwinState) -> str:
    """
    Returns a terse recommendation string for ManagerAgent routing.
    SCAFFOLD | BREAK | ELEVATE | CONTINUE
    """
    if twin.needs_break():
        return "BREAK"
    if twin.is_frustrated():
        return "SCAFFOLD"
    if twin.should_elevate():
        return "ELEVATE"
    return "CONTINUE"
