"""
Data Stream Protocol — Vercel AI SDK compatible stream encoding.

Implements the line-prefixed protocol consumed by useChat / useCompletion
from @ai-sdk/react. Each line is self-describing:

  0:"text"                    → text-delta (UTF-8 chunk)
  2:[{...}]                   → data message (structured JSON annotation)
  9:{"toolCallId":...}        → tool-call-streaming-start
  c:{"toolCallId":...}        → tool-call (complete args)
  a:{"toolCallId":...}        → tool-result
  d:{"finishReason":"stop"}   → finish-message
  e:{"finishReason":...}      → finish-step

Annotation types used by GenUI progressive rendering:

  genui_skeleton   — Component placeholder (type + null props) emitted early
  genui_props      — Delta patch for a previously emitted skeleton
  genui_complete   — All props resolved, component fully renderable
  remediation      — Backend-initiated remediation component injection
  status           — Human-readable status text for the progress bar

Usage from lesson_stream.py / conversation.py:

    from app.api.stream_protocol import DataStreamWriter

    writer = DataStreamWriter()
    yield writer.text("Searching knowledge archive...")
    yield writer.annotation("status", {"message": "Activating Historian Agent..."})
    yield writer.genui_skeleton("quiz-1", "QuizCard")
    yield writer.genui_props("quiz-1", {"question": "...", "options": [...]})
    yield writer.tool_call("tc-1", "render_quiz_widget", {...})
    yield writer.tool_result("tc-1", {...})
    yield writer.finish("stop")
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DataStreamWriter:
    """Encodes structured events into Vercel AI SDK Data Stream Protocol lines."""

    _text_counter: int = field(default=0, init=False)

    # ── Core protocol lines ───────────────────────────────────────────────────

    @staticmethod
    def text(delta: str) -> str:
        """0: — text-delta chunk."""
        return f'0:{json.dumps(delta)}\n'

    @staticmethod
    def annotation(kind: str, payload: dict[str, Any]) -> str:
        """2: — data annotation (array of objects)."""
        obj = {"type": kind, **payload}
        return f'2:{json.dumps([obj])}\n'

    @staticmethod
    def tool_call(
        tool_call_id: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> str:
        """c: — tool-call (complete)."""
        return f'c:{json.dumps({"toolCallId": tool_call_id, "toolName": tool_name, "args": args})}\n'

    @staticmethod
    def tool_result(
        tool_call_id: str,
        result: Any,
    ) -> str:
        """a: — tool-result."""
        return f'a:{json.dumps({"toolCallId": tool_call_id, "result": result})}\n'

    @staticmethod
    def finish(reason: str = "stop") -> str:
        """d: — finish-message."""
        return f'd:{json.dumps({"finishReason": reason})}\n'

    @staticmethod
    def step_finish(reason: str = "stop") -> str:
        """e: — finish-step."""
        return f'e:{json.dumps({"finishReason": reason})}\n'

    # ── GenUI progressive rendering helpers ───────────────────────────────────

    @staticmethod
    def genui_skeleton(
        component_id: str,
        component_type: str,
        *,
        initial_hints: dict[str, Any] | None = None,
    ) -> str:
        """
        Emit a skeleton payload for a GenUI component.

        The frontend immediately renders a loading placeholder for this
        component type. ``initial_hints`` may carry partial data (e.g. a
        title string) so the skeleton is more informative than a blank card.
        """
        payload: dict[str, Any] = {
            "componentId": component_id,
            "componentType": component_type,
            "props": None,
            "state": "skeleton",
        }
        if initial_hints:
            payload["hints"] = initial_hints
        return DataStreamWriter.annotation("genui_skeleton", payload)

    @staticmethod
    def genui_props(
        component_id: str,
        props: dict[str, Any],
        *,
        partial: bool = True,
    ) -> str:
        """
        Emit a props delta for a previously emitted skeleton.

        When ``partial=True`` (default), the frontend merges these props into
        the component's existing local state.  When ``partial=False``, the
        props replace the full prop object and the component is marked complete.
        """
        payload: dict[str, Any] = {
            "componentId": component_id,
            "props": props,
            "state": "partial" if partial else "complete",
        }
        return DataStreamWriter.annotation("genui_props", payload)

    @staticmethod
    def genui_complete(
        component_id: str,
        component_type: str,
        props: dict[str, Any],
        *,
        callbacks: list[str] | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> str:
        """
        Emit a fully-resolved GenUI component in one shot.

        Use this instead of skeleton+props when the full payload is available
        immediately (e.g. canonical cache hit).
        """
        payload: dict[str, Any] = {
            "componentId": component_id,
            "componentType": component_type,
            "props": props,
            "state": "complete",
        }
        if callbacks:
            payload["callbacks"] = callbacks
        if initial_state:
            payload["initialState"] = initial_state
        return DataStreamWriter.annotation("genui_complete", payload)

    # ── Remediation helpers ───────────────────────────────────────────────────

    @staticmethod
    def remediation(
        source_component_id: str,
        remedial_component_type: str,
        remedial_props: dict[str, Any],
        *,
        reason: str = "student_needs_remediation",
        remedial_id: str | None = None,
    ) -> str:
        """
        Inject a remediation component into the stream.

        Sent when the orchestrator detects the student is struggling.  The
        frontend renders the remedial component inline (e.g. an
        InteractiveConceptMap or Flashcard) without a page reload.
        """
        payload: dict[str, Any] = {
            "remedialId": remedial_id or f"remedial-{uuid.uuid4().hex[:8]}",
            "sourceComponentId": source_component_id,
            "componentType": remedial_component_type,
            "props": remedial_props,
            "reason": reason,
        }
        return DataStreamWriter.annotation("remediation", payload)

    @staticmethod
    def remediation_tool_call(
        source_component_id: str,
        student_event: str,
        student_state: dict[str, Any],
    ) -> str:
        """
        Emit a tool-call that the frontend's onToolCall intercepts.

        The frontend pipes the student's interaction data back to the
        orchestrator, which decides whether to stream a remediation component.
        """
        tc_id = f"remediate-{uuid.uuid4().hex[:8]}"
        return DataStreamWriter.tool_call(
            tool_call_id=tc_id,
            tool_name="student_needs_remediation",
            args={
                "sourceComponentId": source_component_id,
                "event": student_event,
                "studentState": student_state,
            },
        )

    # ── Status / progress helpers ─────────────────────────────────────────────

    @staticmethod
    def status(message: str) -> str:
        """Emit a human-readable status annotation for the progress bar."""
        return DataStreamWriter.annotation("status", {"message": message})
