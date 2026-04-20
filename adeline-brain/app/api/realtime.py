"""
Real-Time WebSocket API

Two channel types:
  /ws/monitor/{student_id}   — Parent/teacher read-only monitoring feed
  /ws/session/{session_id}   — Active lesson session (bidirectional)

Events emitted to connected clients:
  cognitive_update   — Cognitive Twin state changed
  block_generated    — New lesson block ready
  agent_thinking     — Agent processing in progress (streaming status)
  zpd_shift          — Student ZPD zone changed
  safety_flag        — Content safety issue detected (parent-visible)
  session_start      — Session opened
  session_end        — Session closed
  twin_snapshot      — Full twin state snapshot (on connect)

Connection management:
  ConnectionManager  — Tracks active WebSocket connections per channel
  Automatically cleans up on disconnect.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from app.agents.cognitive_twin import get_twin, recommend_intervention

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])


# ── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """
    Manages active WebSocket connections.
    Supports multiple connections per channel (e.g. parent + teacher watching same student).
    """

    def __init__(self) -> None:
        # channel_key → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, channel_key: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[channel_key].append(ws)
        logger.info(f"[WS] Connected: channel={channel_key} total={len(self._connections[channel_key])}")

    def disconnect(self, channel_key: str, ws: WebSocket) -> None:
        conns = self._connections.get(channel_key, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(channel_key, None)
        logger.info(f"[WS] Disconnected: channel={channel_key} remaining={len(conns)}")

    async def emit(self, channel_key: str, event_type: str, payload: dict) -> None:
        """Broadcast an event to all connections on a channel."""
        conns = list(self._connections.get(channel_key, []))
        if not conns:
            return

        message = json.dumps({
            "event": event_type,
            "payload": payload,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        dead: list[WebSocket] = []
        for ws in conns:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
            except Exception as e:
                logger.debug(f"[WS] Send failed on {channel_key}: {e}")
                dead.append(ws)

        for ws in dead:
            self.disconnect(channel_key, ws)

    async def emit_to_student_channels(self, student_id: str, event_type: str, payload: dict) -> None:
        """Emit to both monitor and all session channels for a student."""
        await self.emit(f"monitor:{student_id}", event_type, payload)

    def monitor_channel(self, student_id: str) -> str:
        return f"monitor:{student_id}"

    def session_channel(self, session_id: str) -> str:
        return f"session:{session_id}"

    def active_monitor_count(self, student_id: str) -> int:
        return len(self._connections.get(f"monitor:{student_id}", []))


# Global singleton — shared across all routes
connection_manager = ConnectionManager()


def make_emitter(student_id: str):
    """
    Returns an async emit function scoped to a student's monitor channel.
    Inject this into ManagerAgent.generate() for real-time streaming.
    """
    async def _emit(event_type: str, payload: dict) -> None:
        await connection_manager.emit_to_student_channels(student_id, event_type, payload)
    return _emit


# ── Monitor channel (parent/teacher — read-only) ─────────────────────────────

@router.websocket("/ws/monitor/{student_id}")
async def monitor_ws(ws: WebSocket, student_id: str):
    """
    Parent/teacher monitoring channel for a specific student.
    Read-only: events flow from server to client.
    Emits a twin_snapshot immediately on connect.
    """
    channel = connection_manager.monitor_channel(student_id)
    await connection_manager.connect(channel, ws)

    try:
        # Send current twin snapshot on connect
        twin = await get_twin(student_id)
        await ws.send_text(json.dumps({
            "event": "twin_snapshot",
            "payload": {
                **twin.to_dict(),
                "intervention": recommend_intervention(twin),
                "active_monitors": connection_manager.active_monitor_count(student_id),
            },
            "ts": datetime.now(timezone.utc).isoformat(),
        }))

        # Keep alive — parent side is read-only, so just wait for disconnect
        while True:
            try:
                # Accept pings from client to keep connection alive
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                if data == "ping":
                    await ws.send_text(json.dumps({
                        "event": "pong",
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }))
            except asyncio.TimeoutError:
                # Send keepalive ping to client
                try:
                    await ws.send_text(json.dumps({
                        "event": "keepalive",
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }))
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info(f"[WS] Monitor disconnected: student={student_id}")
    except Exception as e:
        logger.error(f"[WS] Monitor error for {student_id}: {e}")
    finally:
        connection_manager.disconnect(channel, ws)


# ── Session channel (active lesson — bidirectional) ───────────────────────────

@router.websocket("/ws/session/{session_id}")
async def session_ws(
    ws: WebSocket,
    session_id: str,
    student_id: Optional[str] = Query(None),
):
    """
    Active lesson session WebSocket.
    Bidirectional: client sends interaction events, server sends cognitive updates.

    Client → Server messages:
      { "type": "response", "text": "...", "was_correct": true/false/null, "track": "..." }
      { "type": "ping" }

    Server → Client messages:
      cognitive_update, block_generated, agent_thinking, zpd_shift, safety_flag
    """
    channel = connection_manager.session_channel(session_id)
    await connection_manager.connect(channel, ws)

    try:
        await ws.send_text(json.dumps({
            "event": "session_start",
            "payload": {"session_id": session_id, "student_id": student_id},
            "ts": datetime.now(timezone.utc).isoformat(),
        }))

        if student_id:
            twin = await get_twin(student_id)
            await ws.send_text(json.dumps({
                "event": "twin_snapshot",
                "payload": {
                    **twin.to_dict(),
                    "intervention": recommend_intervention(twin),
                },
                "ts": datetime.now(timezone.utc).isoformat(),
            }))

        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await ws.send_text(json.dumps({"event": "pong", "ts": datetime.now(timezone.utc).isoformat()}))

            elif msg_type == "response" and student_id:
                from app.agents.manager_agent import manager_agent

                result = await manager_agent.handle_student_response(
                    student_id=student_id,
                    response_text=msg.get("text", ""),
                    was_correct=msg.get("was_correct"),
                    track=msg.get("track", ""),
                    emit=make_emitter(student_id),
                )

                await ws.send_text(json.dumps({
                    "event": "interaction_processed",
                    "payload": result,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }))

                # Mirror cognitive state to parent monitor
                if student_id:
                    await connection_manager.emit(
                        connection_manager.monitor_channel(student_id),
                        "cognitive_update",
                        result.get("twin", {}),
                    )

    except WebSocketDisconnect:
        logger.info(f"[WS] Session disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"[WS] Session error for {session_id}: {e}")
    finally:
        connection_manager.disconnect(channel, ws)
        if student_id:
            await connection_manager.emit(
                connection_manager.monitor_channel(student_id),
                "session_end",
                {"session_id": session_id, "student_id": student_id},
            )


# ── Snapshot REST endpoint (for initial page load, no WS needed) ─────────────

@router.get("/monitor/{student_id}/snapshot")
async def get_monitor_snapshot(student_id: str):
    """
    Returns the current Cognitive Twin state as JSON.
    Used by CognitiveDashboard on initial load before WS connects.
    """
    twin = await get_twin(student_id)
    return {
        **twin.to_dict(),
        "intervention": recommend_intervention(twin),
        "active_monitors": connection_manager.active_monitor_count(student_id),
    }
