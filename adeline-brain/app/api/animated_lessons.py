"""
Animated Sketchnote Lessons API — /lesson/animated + /lesson/narrate

POST /lesson/animated — Generate a full AnimatedSketchnoteLesson JSON via Gemini.
POST /lesson/narrate  — Synthesize scene narration audio with pyttsx3 (offline TTS).
GET  /lesson/narrate/{filename} — Serve a generated narration audio file.

The Witness Protocol is bypassed for animated lessons (same treatment as NARRATED_SLIDE).
The RegistrarAgent is NOT called here — credit is awarded when the student seals the lesson
via POST /journal/seal.

Gemini is used (not Claude) for cost efficiency.
"""
import asyncio
import json
import logging
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.schemas.api_models import (
    AnimatedLessonRequest,
    AnimatedSketchnoteLessonData,
    NarrateRequest,
)
from app.prompts.animated_sketchnote import (
    ANIMATED_SKETCHNOTE_SYSTEM_PROMPT,
    ANIMATED_SKETCHNOTE_USER_PROMPT,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["animated-lessons"])

# ── Audio output directory ────────────────────────────────────────────────────

NARRATION_DIR = Path(tempfile.gettempdir()) / "adeline_narration"
NARRATION_DIR.mkdir(parents=True, exist_ok=True)


# ── Gemini client (lazy init) ─────────────────────────────────────────────────

def _get_gemini_model():
    """Return a configured Gemini GenerativeModel. Lazy-imported to avoid import errors
    when google-generativeai is not yet installed in dev."""
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai is not installed. "
            "Run: pip install google-generativeai"
        ) from exc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        },
        system_instruction=ANIMATED_SKETCHNOTE_SYSTEM_PROMPT,
    )


# ── pyttsx3 TTS (synchronous — run in executor) ───────────────────────────────

def _synthesize_blocking(text: str, output_path: str, rate: int = 160) -> None:
    """Blocking pyttsx3 call — always run via asyncio.run_in_executor."""
    try:
        import pyttsx3  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pyttsx3 is not installed. Run: pip install pyttsx3  "
            "(Linux also requires: apt-get install espeak espeak-data)"
        ) from exc

    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    # Prefer a female voice if available
    voices = engine.getProperty("voices")
    for voice in voices:
        if "female" in voice.name.lower() or "zira" in voice.id.lower():
            engine.setProperty("voice", voice.id)
            break
    engine.save_to_file(text, output_path)
    engine.runAndWait()
    engine.stop()


async def _synthesize_narration(text: str, rate: int = 160) -> str:
    """Generate narration audio and return the local file path."""
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = str(NARRATION_DIR / filename)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _synthesize_blocking, text, output_path, rate)
    return filename


# ── POST /lesson/animated ─────────────────────────────────────────────────────

@router.post("/lesson/animated", response_model=AnimatedSketchnoteLessonData)
async def generate_animated_lesson(body: AnimatedLessonRequest):
    """
    Generate a complete AnimatedSketchnoteLesson via Gemini, then synthesize
    narration audio for each scene with pyttsx3.

    The response is a fully-populated AnimatedSketchnoteLessonData object
    with narrationAudioUrl filled on each scene.
    """
    logger.info(
        f"[/lesson/animated] topic={body.topic!r} "
        f"duration={body.duration_seconds}s ages={body.target_ages}"
    )

    user_prompt = ANIMATED_SKETCHNOTE_USER_PROMPT.format(
        topic=body.topic,
        focus=body.focus or "General introduction appropriate for the age group.",
        duration_seconds=body.duration_seconds,
        target_ages=body.target_ages,
    )

    # ── Call Gemini ───────────────────────────────────────────────────────────
    try:
        model = _get_gemini_model()
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model.generate_content(user_prompt),
        )
        raw_text = response.text.strip()
    except Exception as exc:
        logger.error(f"[/lesson/animated] Gemini call failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Gemini generation failed: {exc}")

    # ── Parse JSON ────────────────────────────────────────────────────────────
    try:
        # Strip accidental markdown code fences if Gemini adds them
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error(f"[/lesson/animated] JSON parse failed: {exc}\nRaw: {raw_text[:500]}")
        raise HTTPException(status_code=502, detail="Gemini returned invalid JSON.")

    try:
        lesson = AnimatedSketchnoteLessonData(**raw)
    except Exception as exc:
        logger.error(f"[/lesson/animated] Schema validation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Lesson schema mismatch: {exc}")

    # ── Synthesize narration audio per scene ──────────────────────────────────
    narration_tasks = [
        _synthesize_narration(scene.narration)
        for scene in lesson.scenes
        if scene.narration
    ]
    try:
        audio_filenames = await asyncio.gather(*narration_tasks, return_exceptions=True)
        for scene, result in zip(lesson.scenes, audio_filenames):
            if isinstance(result, Exception):
                logger.warning(f"[/lesson/animated] TTS failed for scene {scene.sceneNumber}: {result}")
            else:
                scene.narrationAudioUrl = f"/lesson/narrate/{result}"
    except Exception as exc:
        logger.warning(f"[/lesson/animated] TTS batch failed (non-fatal): {exc}")

    return lesson


# ── POST /lesson/narrate ──────────────────────────────────────────────────────

@router.post("/lesson/narrate")
async def narrate_text(body: NarrateRequest):
    """
    Synthesize a single narration text block with pyttsx3.
    Returns a JSON object with the audio URL path.

    Use this for on-demand re-narration of individual scenes.
    """
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty.")

    try:
        filename = await _synthesize_narration(body.text, rate=body.voice_rate)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"audioUrl": f"/lesson/narrate/{filename}"}


# ── GET /lesson/narrate/{filename} ───────────────────────────────────────────

@router.get("/lesson/narrate/{filename}")
async def serve_narration(filename: str):
    """Serve a generated narration audio file by filename."""
    # Sanitise filename to prevent path traversal
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    path = NARRATION_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")

    return FileResponse(str(path), media_type="audio/mpeg")
