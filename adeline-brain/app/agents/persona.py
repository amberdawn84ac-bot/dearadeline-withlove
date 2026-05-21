"""
Adeline Persona — Versioned persona constants and the top-level system prompt.

GRADE_DESC, TRACK_PERSONA, and ADELINE_VOICE live in orchestrator.py as the
authoritative, detail-rich versions used by all specialist agents.
This module re-exports those canonical names so new agents can import from
a single location, and adds ADELINE_SYSTEM_PROMPT — the educational concierge
framing used for top-level route instructions.

Usage:
    from app.agents.persona import GRADE_DESC, TRACK_PERSONA, ADELINE_VOICE, ADELINE_SYSTEM_PROMPT
"""

from app.agents.orchestrator import _GRADE_DESC as GRADE_DESC  # type: ignore[attr-defined]
from app.agents.orchestrator import _TRACK_PERSONA as TRACK_PERSONA  # type: ignore[attr-defined]
from app.agents.orchestrator import _ADELINE_VOICE as ADELINE_VOICE  # type: ignore[attr-defined]

# ── Top-level system prompt (educational concierge framing) ──────────────────
# Used for the /chat route and any new LLM entry points that need the
# full Adeline identity without a track-specific persona appended.

ADELINE_SYSTEM_PROMPT = """You are Adeline — an educational concierge operating from a Biblical worldview.

Your goal is to adapt source material to the learner's specific grade level and personal interests.
Do not give direct answers. Use Socratic questioning to guide the student to discovery.
You must output structured JSON payloads that render as interactive components.
Teach discernment: prompt students to evaluate claims against primary sources.
You never invent facts. You never skip the hard parts. You trust the student."""
