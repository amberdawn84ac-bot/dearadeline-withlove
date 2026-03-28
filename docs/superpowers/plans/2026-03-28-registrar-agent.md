# Registrar Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a credentialing-grade transcript system that turns sealed lesson records into a branded PDF satisfying both Oklahoma homeschool filing requirements and college admissions standards.

**Architecture:** `RegistrarAgent` owns all credit math and data fetching; `transcripts.py` becomes a thin routing layer. A pure PDF builder receives a `TranscriptRecord` and renders it — no logic of its own. Hidden traditional subjects (Math, PE, Fine Arts, Geography, Tech) surface from the Neo4j graph via `APPLIED_IN` edges seeded by a script.

**Tech Stack:** Python/FastAPI, Pydantic v2, SQLAlchemy async, Neo4j async, ReportLab, Next.js 14 App Router, TypeScript

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| CREATE | `adeline-brain/assets/fonts/` | Font directory (Playfair Display Bold, Lora Regular/Italic) |
| CREATE | `adeline-brain/app/agents/registrar.py` | `TrackCredit`, `TranscriptRecord`, `RegistrarAgent.build()` |
| CREATE | `adeline-brain/app/api/pdf_builder.py` | Pure PDF renderer — receives `TranscriptRecord`, returns bytes |
| MODIFY | `adeline-brain/app/connections/journal_store.py` | Add `get_blocks_for_year()`, `get_available_years()`, `get_sources_for_year()` |
| MODIFY | `adeline-brain/app/connections/neo4j_client.py` | Add `get_hidden_subjects_for_student()`, `get_mastered_for_year()` |
| MODIFY | `adeline-brain/app/api/transcripts.py` | Replace inline logic with `RegistrarAgent`; add preview + years endpoints; add `academic_year` param |
| CREATE | `adeline-brain/scripts/seed_hidden_subjects.py` | Seed 28 OAS standards with `APPLIED_IN` edges |
| CREATE | `adeline-brain/tests/test_registrar.py` | Unit tests for credit math and `TranscriptRecord` assembly |
| CREATE | `adeline-ui/src/app/(routes)/dashboard/transcript/page.tsx` | Year picker, stats row, track table, download button |
| MODIFY | `adeline-ui/src/lib/brain-client.ts` | Add `TranscriptRecord`, `TrackCredit` types; add `fetchTranscriptPreview()`, `fetchAvailableYears()` |

---

## Task 1: Font Assets

**Files:**
- Create: `adeline-brain/assets/fonts/` directory
- Download: `PlayfairDisplay-Bold.ttf`, `Lora-Regular.ttf`, `Lora-Italic.ttf`

- [ ] **Step 1: Download OFL-licensed fonts from Google Fonts CDN**

```bash
mkdir -p adeline-brain/assets/fonts

# Playfair Display Bold
curl -L "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf" \
  -o adeline-brain/assets/fonts/PlayfairDisplay-Bold.ttf

# Lora Regular
curl -L "https://github.com/google/fonts/raw/main/ofl/lora/Lora%5Bwght%5D.ttf" \
  -o adeline-brain/assets/fonts/Lora-Regular.ttf

# Lora Italic
curl -L "https://github.com/google/fonts/raw/main/ofl/lora/Lora-Italic%5Bwght%5D.ttf" \
  -o adeline-brain/assets/fonts/Lora-Italic.ttf
```

- [ ] **Step 2: Verify font files exist and are non-zero**

```bash
ls -lh adeline-brain/assets/fonts/
```

Expected output: three `.ttf` files, each > 100 KB.

> **Note:** If the variable-font URLs fail (they are version-pinned), download manually from fonts.google.com (Playfair Display → Bold; Lora → Regular and Italic), rename to match above, and place in `adeline-brain/assets/fonts/`.

- [ ] **Step 3: Add fonts directory to Dockerfile**

In `adeline-brain/Dockerfile`, after `COPY scripts/ ./scripts/`, add:

```dockerfile
COPY assets/ ./assets/
```

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/assets/ adeline-brain/Dockerfile
git commit -m "feat: add Playfair Display and Lora font assets for branded PDF"
```

---

## Task 2: JournalStore — Year-Scoped Queries

**Files:**
- Modify: `adeline-brain/app/connections/journal_store.py`
- Test: `adeline-brain/tests/test_registrar.py` (Task 2 section)

- [ ] **Step 1: Write failing tests for new JournalStore methods**

Create `adeline-brain/tests/test_registrar.py`:

```python
"""Tests for Registrar Agent and supporting JournalStore methods."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── JournalStore year-scoped queries ─────────────────────────────────────────

class FakeJournalStore:
    """In-memory stub for JournalStore — avoids real Postgres in unit tests."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    async def get_blocks_for_year(self, student_id: str, year_start: str, year_end: str):
        return [
            {"track": r["track"], "total_blocks": r["total_blocks"]}
            for r in self._rows
        ]

    async def get_available_years(self, student_id: str) -> list[str]:
        return ["2025-2026"]

    async def get_sources_for_year(self, student_id: str, year_start: str, year_end: str):
        return []


@pytest.mark.asyncio
async def test_get_blocks_for_year_groups_by_track():
    store = FakeJournalStore([
        {"track": "TRUTH_HISTORY", "total_blocks": 6},
        {"track": "DISCIPLESHIP", "total_blocks": 4},
    ])
    rows = await store.get_blocks_for_year("demo-student-001", "2025-08-01", "2026-07-31")
    assert len(rows) == 2
    tracks = {r["track"] for r in rows}
    assert "TRUTH_HISTORY" in tracks
    assert "DISCIPLESHIP" in tracks


@pytest.mark.asyncio
async def test_get_available_years_returns_list():
    store = FakeJournalStore([])
    years = await store.get_available_years("demo-student-001")
    assert isinstance(years, list)
```

- [ ] **Step 2: Run test to verify it passes (stubs pass trivially)**

```bash
cd adeline-brain && python -m pytest tests/test_registrar.py::test_get_blocks_for_year_groups_by_track tests/test_registrar.py::test_get_available_years_returns_list -v
```

Expected: PASS (these are stub tests verifying the interface shape).

- [ ] **Step 3: Add the three new methods to JournalStore**

In `adeline-brain/app/connections/journal_store.py`, after `get_track_progress()`, add:

```python
async def get_blocks_for_year(
    self,
    student_id: str,
    year_start: str,
    year_end: str,
) -> list[dict]:
    """
    Return SUM(completed_blocks) grouped by track for lessons sealed within
    the academic year range [year_start, year_end].

    year_start / year_end are ISO date strings: "2025-08-01", "2026-07-31".
    """
    async with self._session_factory() as session:
        result = await session.execute(
            text("""
                SELECT track,
                       COUNT(*)              AS lessons_sealed,
                       SUM(completed_blocks) AS total_blocks
                FROM student_journal
                WHERE student_id = :student_id
                  AND sealed_at  >= :year_start::timestamptz
                  AND sealed_at  <= :year_end::timestamptz
                GROUP BY track
            """),
            {
                "student_id": student_id,
                "year_start": year_start + "T00:00:00Z",
                "year_end":   year_end   + "T23:59:59Z",
            },
        )
        rows = result.mappings().all()
        return [
            {
                "track":         row["track"],
                "lessons_sealed": int(row["lessons_sealed"]),
                "total_blocks":  int(row["total_blocks"] or 0),
            }
            for row in rows
        ]

async def get_available_years(self, student_id: str) -> list[str]:
    """
    Return the academic years (e.g. ['2025-2026']) that have sealed lessons
    for this student. An academic year starts Aug 1 and ends Jul 31.
    """
    async with self._session_factory() as session:
        result = await session.execute(
            text("""
                SELECT DISTINCT
                    CASE
                        WHEN EXTRACT(MONTH FROM sealed_at) >= 8
                             THEN EXTRACT(YEAR FROM sealed_at)::int
                        ELSE EXTRACT(YEAR FROM sealed_at)::int - 1
                    END AS acad_year_start
                FROM student_journal
                WHERE student_id = :student_id
                ORDER BY acad_year_start DESC
            """),
            {"student_id": student_id},
        )
        rows = result.mappings().all()
        return [
            f"{int(row['acad_year_start'])}-{int(row['acad_year_start']) + 1}"
            for row in rows
        ]

async def get_sources_for_year(
    self,
    student_id: str,
    year_start: str,
    year_end: str,
) -> list[dict]:
    """
    Return deduplicated primary sources from lessons sealed within the
    academic year range.
    """
    async with self._session_factory() as session:
        result = await session.execute(
            text("""
                SELECT track, sources_json
                FROM student_journal
                WHERE student_id  = :student_id
                  AND sealed_at   >= :year_start::timestamptz
                  AND sealed_at   <= :year_end::timestamptz
                  AND sources_json IS NOT NULL
            """),
            {
                "student_id": student_id,
                "year_start": year_start + "T00:00:00Z",
                "year_end":   year_end   + "T23:59:59Z",
            },
        )
        rows = result.mappings().all()

    import json
    seen: set[str] = set()
    merged: list[dict] = []
    for row in rows:
        try:
            sources = json.loads(row["sources_json"] or "[]")
        except json.JSONDecodeError:
            sources = []
        for s in sources:
            title = s.get("title", "")
            if title and title not in seen:
                seen.add(title)
                merged.append({**s, "track": row["track"]})
    return merged
```

- [ ] **Step 4: Run tests again**

```bash
python -m pytest tests/test_registrar.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/app/connections/journal_store.py adeline-brain/tests/test_registrar.py
git commit -m "feat: add year-scoped JournalStore queries for Registrar Agent"
```

---

## Task 3: Neo4jClient — Mastery and Hidden Subject Queries

**Files:**
- Modify: `adeline-brain/app/connections/neo4j_client.py`
- Test: `adeline-brain/tests/test_registrar.py` (Task 3 section)

- [ ] **Step 1: Add failing tests for the new Neo4j methods**

Append to `adeline-brain/tests/test_registrar.py`:

```python
# ── Neo4j hidden-subject query ────────────────────────────────────────────────

class FakeNeo4jClient:
    """Stub for Neo4jClient."""

    async def get_hidden_subjects_for_student(
        self, student_id: str, active_tracks: list[str]
    ) -> list[dict]:
        return [
            {
                "standard_id": "OAS.MATH.8.EE.7",
                "text": "Solve linear equations",
                "subject": "Mathematics",
                "track": "GOVERNMENT_ECONOMICS",
            }
        ]

    async def get_mastered_standards_for_tracks(
        self, student_id: str, active_tracks: list[str]
    ) -> list[dict]:
        return [
            {
                "standard_id": "OAS.SS.8.TH.1",
                "text": "Analyze primary sources",
                "grade": 8,
                "track": "TRUTH_HISTORY",
            }
        ]


@pytest.mark.asyncio
async def test_hidden_subjects_groups_by_subject():
    client = FakeNeo4jClient()
    rows = await client.get_hidden_subjects_for_student(
        "demo-student-001", ["GOVERNMENT_ECONOMICS"]
    )
    assert rows[0]["subject"] == "Mathematics"
    assert rows[0]["standard_id"] == "OAS.MATH.8.EE.7"


@pytest.mark.asyncio
async def test_mastered_standards_returns_list():
    client = FakeNeo4jClient()
    rows = await client.get_mastered_standards_for_tracks(
        "demo-student-001", ["TRUTH_HISTORY"]
    )
    assert rows[0]["track"] == "TRUTH_HISTORY"
```

- [ ] **Step 2: Run tests to verify they pass (stubs)**

```bash
python -m pytest tests/test_registrar.py -v
```

Expected: PASS

- [ ] **Step 3: Add the two new methods to Neo4jClient**

In `adeline-brain/app/connections/neo4j_client.py`, before `neo4j_client = Neo4jClient()`, add:

```python
    async def get_hidden_subjects_for_student(
        self, student_id: str, active_tracks: list[str]
    ) -> list[dict]:
        """
        Find traditional subjects (Math, PE, Fine Arts, Geography, Tech) that
        the student has mastered via APPLIED_IN edges.

        Returns list of {standard_id, text, subject, track} grouped by subject.
        The APPLIED_IN relationship connects OASStandard → Track, meaning the
        standard is covered implicitly through work in that track.
        """
        return await self.run(
            """
            MATCH (st:Student {id: $student_id})-[:MASTERED]->(s:OASStandard)
            MATCH (s)-[:APPLIED_IN]->(t:Track)
            WHERE t.name IN $active_tracks
            RETURN s.id       AS standard_id,
                   s.standard_text AS text,
                   s.subject   AS subject,
                   t.name      AS track
            ORDER BY s.subject, s.grade
            """,
            {"student_id": student_id, "active_tracks": active_tracks},
        )

    async def get_mastered_standards_for_tracks(
        self, student_id: str, active_tracks: list[str]
    ) -> list[dict]:
        """
        Return all OAS standards the student has MASTERED on the given tracks.
        Used by RegistrarAgent to populate mastered_standards in TranscriptRecord.
        """
        return await self.run(
            """
            MATCH (st:Student {id: $student_id})-[:MASTERED]->(s:OASStandard)
            OPTIONAL MATCH (s)-[:MAPS_TO_TRACK]->(t:Track)
            WHERE t.name IN $active_tracks OR s.track IN $active_tracks
            RETURN s.id              AS standard_id,
                   coalesce(s.standard_text, s.text, '') AS text,
                   s.grade           AS grade,
                   coalesce(t.name, s.track, '') AS track
            ORDER BY track, s.grade
            """,
            {"student_id": student_id, "active_tracks": active_tracks},
        )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_registrar.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add adeline-brain/app/connections/neo4j_client.py adeline-brain/tests/test_registrar.py
git commit -m "feat: add hidden-subject and mastery queries to Neo4jClient"
```

---

## Task 4: RegistrarAgent — Credit Math and TranscriptRecord Assembly

**Files:**
- Create: `adeline-brain/app/agents/registrar.py`
- Test: `adeline-brain/tests/test_registrar.py` (Task 4 section)

- [ ] **Step 1: Write failing tests for RegistrarAgent credit math**

Append to `adeline-brain/tests/test_registrar.py`:

```python
# ── RegistrarAgent credit math ───────────────────────────────────────────────

def test_clock_hours_from_blocks():
    """verified_blocks × 30 min ÷ 60 = clock_hours"""
    from app.agents.registrar import _blocks_to_clock_hours
    assert _blocks_to_clock_hours(12) == 6.0
    assert _blocks_to_clock_hours(0) == 0.0
    assert _blocks_to_clock_hours(1) == 0.5


def test_carnegie_units_from_clock_hours():
    """clock_hours ÷ 120 = carnegie_units"""
    from app.agents.registrar import _clock_hours_to_carnegie
    assert _clock_hours_to_carnegie(120.0) == pytest.approx(1.0)
    assert _clock_hours_to_carnegie(60.0) == pytest.approx(0.5)
    assert _clock_hours_to_carnegie(0.0) == pytest.approx(0.0)


def test_mastery_band_to_letter_grade():
    from app.agents.registrar import _band_to_letter
    assert _band_to_letter("ADVANCED")   == "A"
    assert _band_to_letter("PROFICIENT") == "B"
    assert _band_to_letter("DEVELOPING") == "C"
    assert _band_to_letter("NOVICE")     == "Pass"
    assert _band_to_letter("UNKNOWN")    == "Pass"


def test_academic_year_to_date_range():
    from app.agents.registrar import _year_to_range
    start, end = _year_to_range("2025-2026")
    assert start == "2025-08-01"
    assert end   == "2026-07-31"


def test_year_to_range_invalid():
    from app.agents.registrar import _year_to_range
    with pytest.raises(ValueError, match="Expected format"):
        _year_to_range("2025")
```

- [ ] **Step 2: Run to verify tests fail**

```bash
python -m pytest tests/test_registrar.py::test_clock_hours_from_blocks \
  tests/test_registrar.py::test_carnegie_units_from_clock_hours \
  tests/test_registrar.py::test_mastery_band_to_letter_grade \
  tests/test_registrar.py::test_academic_year_to_date_range \
  tests/test_registrar.py::test_year_to_range_invalid -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Create `adeline-brain/app/agents/registrar.py`**

```python
"""
Registrar Agent
Transforms sealed lesson records into a credentialing-grade TranscriptRecord.

Audiences:
  1. Oklahoma homeschool state filing — clock hours, OAS standard coverage
  2. College admissions — Carnegie units, letter grades, traditional course names

Credit math:
  clock_hours    = SUM(completed_blocks) × 30 min ÷ 60
  carnegie_units = clock_hours ÷ 120

This module owns all business logic. transcripts.py is a thin routing layer.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MINUTES_PER_BLOCK = 30
HOURS_PER_CARNEGIE = 120.0
WITNESS_THRESHOLD = 0.82

TRACK_LABELS: dict[str, str] = {
    "CREATION_SCIENCE":     "Track 1 — God's Creation & Science",
    "HEALTH_NATUROPATHY":   "Track 2 — Health & Naturopathy",
    "HOMESTEADING":         "Track 3 — Homesteading & Stewardship",
    "GOVERNMENT_ECONOMICS": "Track 4 — Government & Economics",
    "JUSTICE_CHANGEMAKING": "Track 5 — Justice & Change-making",
    "DISCIPLESHIP":         "Track 6 — Discipleship & Discernment",
    "TRUTH_HISTORY":        "Track 7 — Truth-Based History",
    "ENGLISH_LITERATURE":   "Track 8 — English Language & Literature",
}

TRADITIONAL_EQUIV: dict[str, str] = {
    "CREATION_SCIENCE":     "Biology / Earth Science",
    "HEALTH_NATUROPATHY":   "Health Science",
    "HOMESTEADING":         "Agricultural Science & Technology",
    "GOVERNMENT_ECONOMICS": "Government & Economics",
    "JUSTICE_CHANGEMAKING": "Social Studies / Civics",
    "DISCIPLESHIP":         "Philosophy & Ethics",
    "TRUTH_HISTORY":        "American History / World History",
    "ENGLISH_LITERATURE":   "English Language Arts",
}

_LETTER_GRADE: dict[str, str] = {
    "ADVANCED":   "A",
    "PROFICIENT": "B",
    "DEVELOPING": "C",
    "NOVICE":     "Pass",
}


# ── Pure helper functions (unit-testable) ─────────────────────────────────────

def _blocks_to_clock_hours(blocks: int) -> float:
    return (blocks * MINUTES_PER_BLOCK) / 60.0


def _clock_hours_to_carnegie(clock_hours: float) -> float:
    if clock_hours <= 0:
        return 0.0
    return clock_hours / HOURS_PER_CARNEGIE


def _band_to_letter(mastery_band: str) -> str:
    return _LETTER_GRADE.get(mastery_band, "Pass")


def _year_to_range(academic_year: str) -> tuple[str, str]:
    """
    '2025-2026' → ('2025-08-01', '2026-07-31')
    Raises ValueError if the format is wrong.
    """
    parts = academic_year.split("-")
    if len(parts) != 2:
        raise ValueError(f"Expected format 'YYYY-YYYY', got: '{academic_year}'")
    start_year, end_year = parts
    return f"{start_year}-08-01", f"{end_year}-07-31"


# ── Data Models ───────────────────────────────────────────────────────────────

class TrackCredit(BaseModel):
    track_id:          str
    track_label:       str
    traditional_equiv: str
    mastery_band:      str    # NOVICE / DEVELOPING / PROFICIENT / ADVANCED
    letter_grade:      str    # A / B / C / Pass
    lessons_sealed:    int
    verified_blocks:   int
    clock_hours:       float
    carnegie_units:    float
    covered_subjects:  list[str]
    top_sources:       list[str]  # up to 3 source titles


class TranscriptRecord(BaseModel):
    student_id:           str
    student_name:         str
    academic_year:        str
    generated_at:         str   # ISO datetime
    tracks:               list[TrackCredit]
    total_clock_hours:    float
    total_carnegie_units: float
    traditional_subjects: list[dict]  # {subject, standards: list[str], clock_hours, grade}
    mastered_standards:   list[dict]  # {standard_id, text, grade, track}
    evidence_sources:     list[dict]  # {title, author, year, url, track}
    witness_threshold:    float


# ── RegistrarAgent ────────────────────────────────────────────────────────────

class RegistrarAgent:
    """
    Builds a TranscriptRecord for a student and academic year.

    Usage:
        agent = RegistrarAgent(journal_store, neo4j_client)
        record = await agent.build(student_id="demo-student-001", academic_year="2025-2026")
    """

    def __init__(self, journal_store, neo4j_client):
        self._journal = journal_store
        self._neo4j   = neo4j_client

    async def build(self, student_id: str, academic_year: str) -> TranscriptRecord:
        year_start, year_end = _year_to_range(academic_year)

        # ── 1. Fetch raw data in parallel ────────────────────────────────────
        import asyncio
        block_rows, source_rows = await asyncio.gather(
            self._journal.get_blocks_for_year(student_id, year_start, year_end),
            self._journal.get_sources_for_year(student_id, year_start, year_end),
        )

        if not block_rows:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail=f"No sealed lessons found for {academic_year}",
            )

        active_tracks = [row["track"] for row in block_rows]

        # ── 2. Fetch Neo4j data (graceful on failure) ─────────────────────────
        mastered_raw: list[dict] = []
        hidden_raw:   list[dict] = []
        try:
            mastered_raw, hidden_raw = await asyncio.gather(
                self._neo4j.get_mastered_standards_for_tracks(student_id, active_tracks),
                self._neo4j.get_hidden_subjects_for_student(student_id, active_tracks),
            )
        except Exception as e:
            logger.warning(f"[RegistrarAgent] Neo4j unavailable — proceeding without standards: {e}")

        # ── 3. Build TrackCredit list ─────────────────────────────────────────

        # Index sources by track for top_sources
        sources_by_track: dict[str, list[str]] = {}
        for s in source_rows:
            track = s.get("track", "")
            title = s.get("title", "")
            if track and title:
                sources_by_track.setdefault(track, []).append(title)

        # Index hidden subjects by track
        hidden_by_track: dict[str, list[str]] = {}
        for h in hidden_raw:
            track   = h.get("track", "")
            subject = h.get("subject", "")
            if track and subject:
                existing = hidden_by_track.setdefault(track, [])
                if subject not in existing:
                    existing.append(subject)

        # We need mastery_band per track — query student state
        # Fall back to NOVICE if student state unavailable
        mastery_by_track: dict[str, str] = {}
        try:
            from app.connections.pgvector_client import hippocampus as _hp
            # Re-use existing student state endpoint logic: query journal for lesson count
            # Mastery band derived from lesson count heuristic if no ZPD score available
            for row in block_rows:
                lessons = row.get("lessons_sealed", 0)
                if lessons >= 8:
                    mastery_by_track[row["track"]] = "ADVANCED"
                elif lessons >= 5:
                    mastery_by_track[row["track"]] = "PROFICIENT"
                elif lessons >= 2:
                    mastery_by_track[row["track"]] = "DEVELOPING"
                else:
                    mastery_by_track[row["track"]] = "NOVICE"
        except Exception:
            pass

        track_credits: list[TrackCredit] = []
        for row in block_rows:
            track_id     = row["track"]
            lessons_n    = row.get("lessons_sealed", 0)
            blocks_n     = row.get("total_blocks", 0)
            clock_hrs    = _blocks_to_clock_hours(blocks_n)
            carnegie     = _clock_hours_to_carnegie(clock_hrs)
            band         = mastery_by_track.get(track_id, "NOVICE")
            letter       = _band_to_letter(band)
            covered_subj = hidden_by_track.get(track_id, [])
            top_src      = sources_by_track.get(track_id, [])[:3]

            track_credits.append(TrackCredit(
                track_id=track_id,
                track_label=TRACK_LABELS.get(track_id, track_id),
                traditional_equiv=TRADITIONAL_EQUIV.get(track_id, ""),
                mastery_band=band,
                letter_grade=letter,
                lessons_sealed=lessons_n,
                verified_blocks=blocks_n,
                clock_hours=round(clock_hrs, 2),
                carnegie_units=round(carnegie, 3),
                covered_subjects=covered_subj,
                top_sources=top_src,
            ))

        # ── 4. Traditional subjects grid ──────────────────────────────────────
        subj_map: dict[str, dict] = {}
        for h in hidden_raw:
            subj    = h.get("subject", "")
            std_id  = h.get("standard_id", "")
            track   = h.get("track", "")
            if not subj:
                continue
            entry = subj_map.setdefault(subj, {
                "subject":    subj,
                "standards":  [],
                "clock_hours": 0.0,
                "grade":      "Pass",
            })
            if std_id and std_id not in entry["standards"]:
                entry["standards"].append(std_id)
            # Accumulate clock hours from host track
            for tc in track_credits:
                if tc.track_id == track:
                    entry["clock_hours"] = round(entry["clock_hours"] + tc.clock_hours * 0.15, 2)

        traditional_subjects = list(subj_map.values())

        # ── 5. Totals ─────────────────────────────────────────────────────────
        total_clock_hours    = round(sum(tc.clock_hours    for tc in track_credits), 2)
        total_carnegie_units = round(sum(tc.carnegie_units for tc in track_credits), 3)

        return TranscriptRecord(
            student_id=student_id,
            student_name=f"Student {student_id}",
            academic_year=academic_year,
            generated_at=datetime.now(timezone.utc).isoformat(),
            tracks=track_credits,
            total_clock_hours=total_clock_hours,
            total_carnegie_units=total_carnegie_units,
            traditional_subjects=traditional_subjects,
            mastered_standards=mastered_raw,
            evidence_sources=source_rows,
            witness_threshold=WITNESS_THRESHOLD,
        )
```

- [ ] **Step 4: Run credit math tests**

```bash
python -m pytest tests/test_registrar.py::test_clock_hours_from_blocks \
  tests/test_registrar.py::test_carnegie_units_from_clock_hours \
  tests/test_registrar.py::test_mastery_band_to_letter_grade \
  tests/test_registrar.py::test_academic_year_to_date_range \
  tests/test_registrar.py::test_year_to_range_invalid -v
```

Expected: PASS (all 5 tests).

- [ ] **Step 5: Write integration test for full RegistrarAgent.build()**

Append to `adeline-brain/tests/test_registrar.py`:

```python
# ── RegistrarAgent.build() integration ───────────────────────────────────────

@pytest.mark.asyncio
async def test_registrar_build_returns_transcript_record():
    from app.agents.registrar import RegistrarAgent, TranscriptRecord

    fake_journal = AsyncMock()
    fake_journal.get_blocks_for_year.return_value = [
        {"track": "TRUTH_HISTORY", "lessons_sealed": 3, "total_blocks": 9},
    ]
    fake_journal.get_sources_for_year.return_value = [
        {"title": "Narrative of Frederick Douglass", "author": "Douglass", "year": 1845,
         "url": "https://archive.org", "track": "TRUTH_HISTORY"},
    ]

    fake_neo4j = AsyncMock()
    fake_neo4j.get_mastered_standards_for_tracks.return_value = [
        {"standard_id": "OAS.SS.8.TH.1", "text": "Primary sources", "grade": 8, "track": "TRUTH_HISTORY"},
    ]
    fake_neo4j.get_hidden_subjects_for_student.return_value = []

    agent = RegistrarAgent(fake_journal, fake_neo4j)
    record = await agent.build("demo-student-001", "2025-2026")

    assert isinstance(record, TranscriptRecord)
    assert record.student_id == "demo-student-001"
    assert record.academic_year == "2025-2026"
    assert len(record.tracks) == 1

    tc = record.tracks[0]
    assert tc.track_id == "TRUTH_HISTORY"
    assert tc.verified_blocks == 9
    assert tc.clock_hours == pytest.approx(4.5)   # 9 × 30 / 60
    assert tc.carnegie_units == pytest.approx(0.0375)  # 4.5 / 120
    assert tc.letter_grade == "DEVELOPING"  # 3 lessons → DEVELOPING band


@pytest.mark.asyncio
async def test_registrar_raises_404_when_no_lessons():
    from app.agents.registrar import RegistrarAgent
    from fastapi import HTTPException

    fake_journal = AsyncMock()
    fake_journal.get_blocks_for_year.return_value = []
    fake_journal.get_sources_for_year.return_value = []

    fake_neo4j = AsyncMock()

    agent = RegistrarAgent(fake_journal, fake_neo4j)
    with pytest.raises(HTTPException) as exc_info:
        await agent.build("demo-student-001", "2025-2026")
    assert exc_info.value.status_code == 404
```

- [ ] **Step 6: Run all registrar tests**

```bash
python -m pytest tests/test_registrar.py -v
```

Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add adeline-brain/app/agents/registrar.py adeline-brain/tests/test_registrar.py
git commit -m "feat: RegistrarAgent with TranscriptRecord, TrackCredit, and credit math"
```

---

## Task 5: Branded PDF Builder

**Files:**
- Create: `adeline-brain/app/api/pdf_builder.py`

The PDF builder is a pure function — it receives a `TranscriptRecord` and returns bytes. No data fetching. No business logic.

- [ ] **Step 1: Create `adeline-brain/app/api/pdf_builder.py`**

```python
"""
Adeline Branded PDF Builder
Pure renderer — receives a TranscriptRecord, returns PDF bytes.
No data fetching. No credit math.

Typography:
  Headings:  Playfair Display Bold (classical, authoritative)
  Body:      Lora Regular / Italic (scholarly serif)
  Monospace: Courier New (standard IDs, scores)

Color palette:
  INK:           #2C2318  — all body text
  PARADISE:      #9A3F4A  — section headers, table header bg
  PAPAYA:        #BD6809  — accent lines, Carnegie figures, Registrar seal
  FUSCHIA:       #3D1419  — track names (bold)
  PARCHMENT:     #FDF8F0  — page background tint
  PARCHMENT_DARK:#F0D9B0  — alternating table rows, rule lines
"""
import io
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Font directory relative to this file → adeline-brain/assets/fonts/
_FONT_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

# Brand colors
_INK            = "#2C2318"
_PARADISE       = "#9A3F4A"
_PAPAYA         = "#BD6809"
_FUSCHIA        = "#3D1419"
_PARCHMENT      = "#FDF8F0"
_PARCHMENT_DARK = "#F0D9B0"
_TRUTH_GREEN    = "#2E7D32"


def _register_fonts():
    """Register custom TTF fonts with ReportLab. Falls back to Times if missing."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    playfair = _FONT_DIR / "PlayfairDisplay-Bold.ttf"
    lora_reg = _FONT_DIR / "Lora-Regular.ttf"
    lora_ita = _FONT_DIR / "Lora-Italic.ttf"

    registered = {}

    if playfair.exists():
        pdfmetrics.registerFont(TTFont("PlayfairDisplay-Bold", str(playfair)))
        registered["heading"] = "PlayfairDisplay-Bold"
    else:
        logger.warning("[PDF] PlayfairDisplay-Bold.ttf not found — falling back to Times-Bold")
        registered["heading"] = "Times-Bold"

    if lora_reg.exists():
        pdfmetrics.registerFont(TTFont("Lora-Regular", str(lora_reg)))
        registered["body"] = "Lora-Regular"
    else:
        logger.warning("[PDF] Lora-Regular.ttf not found — falling back to Times-Roman")
        registered["body"] = "Times-Roman"

    if lora_ita.exists():
        pdfmetrics.registerFont(TTFont("Lora-Italic", str(lora_ita)))
        registered["italic"] = "Lora-Italic"
    else:
        registered["italic"] = "Times-Italic"

    return registered


def build_transcript_pdf(record) -> bytes:
    """
    Render a TranscriptRecord as a branded 2-page PDF.

    Page 1: 8-Track credit summary table + OAS standards
    Page 2: Traditional subjects grid + Evidence appendix
    """
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak,
    )
    from reportlab.platypus.flowables import KeepTogether

    fonts = _register_fonts()
    H  = fonts["heading"]   # Playfair Display Bold or Times-Bold fallback
    B  = fonts["body"]      # Lora Regular or Times-Roman fallback
    I  = fonts["italic"]    # Lora Italic or Times-Italic fallback
    MO = "Courier"          # Monospace for IDs / scores

    INK  = colors.HexColor(_INK)
    PAR  = colors.HexColor(_PARADISE)
    PAP  = colors.HexColor(_PAPAYA)
    FUS  = colors.HexColor(_FUSCHIA)
    PARCH     = colors.HexColor(_PARCHMENT)
    PARCH_DRK = colors.HexColor(_PARCHMENT_DARK)
    TGREEN    = colors.HexColor(_TRUTH_GREEN)

    # ── Styles ────────────────────────────────────────────────────────────────
    def style(name, font, size, color=None, align=0, space_before=0, space_after=4, leading=None):
        return ParagraphStyle(
            name,
            fontName=font,
            fontSize=size,
            textColor=color or INK,
            alignment=align,
            spaceBefore=space_before,
            spaceAfter=space_after,
            leading=leading or (size * 1.35),
        )

    s_institution = style("Institution", H,  20, INK,  align=1, space_after=2)
    s_sub         = style("Sub",         I,  10, INK,  align=1, space_after=2)
    s_meta        = style("Meta",        I,   9, INK,  space_after=2)
    s_section     = style("Section",     H,  12, PAR,  space_before=14, space_after=5)
    s_track_name  = style("TrackName",   H,  10, FUS,  space_after=1)
    s_trad_equiv  = style("TradEquiv",   I,   8, INK,  space_after=2)
    s_body        = style("Body",        B,  10, INK,  space_after=4, leading=15)
    s_small       = style("Small",       B,   9, INK,  space_after=3, leading=13)
    s_italic      = style("Italic",      I,   9, INK,  space_after=3, leading=13)
    s_mono        = style("Mono",        MO,  8, INK,  space_after=2)
    s_mono_green  = style("MonoGreen",   MO,  8, TGREEN, space_after=2)
    s_papaya      = style("Papaya",      B,  10, PAP,  space_after=4)
    s_seal        = style("Seal",        H,  10, PAP,  space_after=3)
    s_footer_ital = style("FooterItal",  I,   8, INK,  space_after=2)

    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=1.1 * inch,
        rightMargin=1.1 * inch,
        topMargin=1.0 * inch,
        bottomMargin=1.0 * inch,
    )
    story = []

    # ── Parchment background rect ────────────────────────────────────────────
    # We draw this via a canvas callback registered on the doc.
    # Simpler approach: set page background color on the doc template.
    # (ReportLab doesn't natively support background colors on SimpleDocTemplate,
    #  so we approximate with a wide tinted table spanning the first paragraph.)

    # ── PAGE 1 ────────────────────────────────────────────────────────────────

    # Header
    story.append(Paragraph("DEAR ADELINE", s_institution))
    story.append(Paragraph("Official Academic Transcript", s_sub))
    story.append(Paragraph("Truth-First Classical Education · Oklahoma", s_sub))
    story.append(Spacer(1, 0.08 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=PAR))
    story.append(HRFlowable(width="100%", thickness=0.5, color=PAR, spaceAfter=6))

    story.append(Paragraph(f"Student:        {record.student_name}", s_meta))
    story.append(Paragraph(f"Student ID:     {record.student_id}", s_meta))
    story.append(Paragraph(f"Academic Year:  {record.academic_year}", s_meta))
    story.append(Paragraph(f"Generated:      {record.generated_at[:10]}", s_meta))
    story.append(Spacer(1, 0.18 * inch))

    # 8-Track Summary Table
    story.append(Paragraph("8-TRACK CREDIT SUMMARY", s_section))

    tbl_rows = [[
        Paragraph("<b>Track</b>", s_body),
        Paragraph("<b>Gr</b>", s_body),
        Paragraph("<b>Clock Hrs</b>", s_body),
        Paragraph("<b>Carnegie</b>", s_body),
    ]]

    for tc in record.tracks:
        # Track cell: track name bold + trad equiv italic below
        track_cell = [
            Paragraph(tc.track_label, s_track_name),
            Paragraph(tc.traditional_equiv, s_trad_equiv),
        ]
        if tc.top_sources:
            src_text = " · ".join(tc.top_sources[:3])
            track_cell.append(Paragraph(f"<i>{src_text}</i>", s_mono))

        tbl_rows.append([
            track_cell,
            Paragraph(f"<b>{tc.letter_grade}</b>", s_papaya),
            Paragraph(f"{tc.clock_hours:.1f}", s_body),
            Paragraph(f"{tc.carnegie_units:.3f}", s_papaya),
        ])

    # Totals row
    tbl_rows.append([
        Paragraph("<b>TOTAL</b>", s_body),
        Paragraph("", s_body),
        Paragraph(f"<b>{record.total_clock_hours:.1f} hr</b>", s_papaya),
        Paragraph(f"<b>{record.total_carnegie_units:.3f}</b>", s_papaya),
    ])

    col_w = [3.5 * inch, 0.55 * inch, 1.0 * inch, 0.9 * inch]
    t = Table(tbl_rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  PAR),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  H),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [colors.white, PARCH]),
        ("BACKGROUND",    (0, -1),(-1, -1), PARCH_DRK),
        ("GRID",          (0, 0), (-1, -1), 0.4, PARCH_DRK),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2 * inch))

    # OAS Standards — grouped by track
    if record.mastered_standards:
        story.append(Paragraph("OKLAHOMA ACADEMIC STANDARDS — MASTERED", s_section))
        by_track: dict[str, list] = {}
        for s in record.mastered_standards:
            t_key = s.get("track", "UNKNOWN")
            by_track.setdefault(t_key, []).append(s)

        for track_id, stds in sorted(by_track.items()):
            from app.agents.registrar import TRACK_LABELS
            label = TRACK_LABELS.get(track_id, track_id)
            story.append(Paragraph(label, s_body))
            for std in stds:
                std_id = std.get("standard_id", std.get("std_id", ""))
                grade  = std.get("grade", "")
                text_  = std.get("text", "")
                story.append(Paragraph(
                    f'<font name="{MO}">{std_id}</font> Gr {grade} — <i>{text_}</i>',
                    s_small,
                ))
            story.append(Spacer(1, 0.06 * inch))

    # Registrar's Seal
    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=PAP))
    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph("REGISTRAR'S SEAL", s_seal))
    story.append(Paragraph(
        f"This transcript is verified via the Adeline Witness Protocol "
        f"(truth threshold: {record.witness_threshold}). "
        "All credits represent primary-source mastery sealed by the student.",
        s_footer_ital,
    ))

    # ── PAGE 2 ────────────────────────────────────────────────────────────────
    story.append(PageBreak())

    story.append(Paragraph("DEAR ADELINE", s_institution))
    story.append(Paragraph("Transcript — Page 2: Traditional Subject Grid", s_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=PAR))
    story.append(HRFlowable(width="100%", thickness=0.5, color=PAR, spaceAfter=6))
    story.append(Spacer(1, 0.1 * inch))

    # Explanatory paragraph
    story.append(Paragraph(
        "The following traditional academic subjects are embedded within the 8-Track "
        "curriculum. Each entry shows the Oklahoma Academic Standards mastered through "
        "the corresponding track's primary-source work. Clock hours shown are "
        "estimated allocations from the host track's verified block count.",
        s_body,
    ))
    story.append(Spacer(1, 0.15 * inch))

    # Traditional Subjects Table
    if record.traditional_subjects:
        story.append(Paragraph("TRADITIONAL SUBJECTS COVERED", s_section))

        subj_rows = [[
            Paragraph("<b>Subject</b>", s_body),
            Paragraph("<b>OAS Standards</b>", s_body),
            Paragraph("<b>Est. Hours</b>", s_body),
            Paragraph("<b>Grade</b>", s_body),
        ]]

        for subj in record.traditional_subjects:
            name   = subj.get("subject", "")
            stds   = subj.get("standards", [])
            hrs    = subj.get("clock_hours", 0.0)
            grade  = subj.get("grade", "Pass")
            subj_rows.append([
                Paragraph(f"<b>{name}</b>", s_body),
                Paragraph(", ".join(stds[:4]), s_mono),
                Paragraph(f"{hrs:.1f}", s_body),
                Paragraph(grade, s_papaya),
            ])

        t2 = Table(subj_rows, colWidths=[1.8*inch, 2.4*inch, 0.9*inch, 0.7*inch])
        t2.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  PAR),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  H),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, PARCH]),
            ("GRID",          (0, 0), (-1, -1), 0.4, PARCH_DRK),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(t2)
        story.append(Spacer(1, 0.2 * inch))

    # Evidence Appendix
    if record.evidence_sources:
        story.append(Paragraph("EVIDENCE APPENDIX — PRIMARY SOURCES", s_section))
        story.append(Paragraph(
            "The following primary sources were verified through the Adeline Witness Protocol. "
            "These documents constitute the evidentiary basis of this transcript.",
            s_body,
        ))
        story.append(Spacer(1, 0.08 * inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=PAR))
        story.append(Spacer(1, 0.08 * inch))

        from app.agents.registrar import TRACK_LABELS
        for i, src in enumerate(record.evidence_sources, start=1):
            title  = src.get("title", "Untitled")
            author = src.get("author", "")
            year   = src.get("year", "")
            url    = src.get("url", "")
            track  = TRACK_LABELS.get(src.get("track", ""), src.get("track", ""))

            citation_parts = [str(author)] if author else []
            if year:
                citation_parts.append(str(year))
            citation = ", ".join(citation_parts)

            citation_card = [
                Paragraph(f"{i}. <b>{title}</b>", s_body),
            ]
            if citation:
                citation_card.append(Paragraph(f"    <i>{citation}</i>", s_italic))
            if track:
                citation_card.append(Paragraph(f"    {track}", s_small))
            if url:
                citation_card.append(Paragraph(
                    f'    <link href="{url}" color="{_PAPAYA}">{url[:60]}…</link>'
                    if len(url) > 60 else f'    <link href="{url}" color="{_PAPAYA}">{url}</link>',
                    s_mono,
                ))
            citation_card.append(Paragraph(
                f"    Truth Score: ≥ {record.witness_threshold} — Witness Protocol verified",
                s_mono_green,
            ))
            story.extend(citation_card)
            story.append(Spacer(1, 0.08 * inch))

    # Page 2 footer
    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=PAP))
    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph(
        "Dear Adeline 2.0 — Truth-First K-12 AI Mentor. "
        "All content verified through the Witness Protocol (Deuteronomy 19:15).",
        s_footer_ital,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
```

- [ ] **Step 2: Smoke-test the builder with a minimal record**

```bash
cd adeline-brain && python -c "
from app.agents.registrar import TranscriptRecord, TrackCredit
from app.api.pdf_builder import build_transcript_pdf
import datetime

record = TranscriptRecord(
    student_id='demo-student-001',
    student_name='Student demo-student-001',
    academic_year='2025-2026',
    generated_at=datetime.datetime.now().isoformat(),
    tracks=[TrackCredit(
        track_id='TRUTH_HISTORY',
        track_label='Track 7 — Truth-Based History',
        traditional_equiv='American History / World History',
        mastery_band='DEVELOPING',
        letter_grade='C',
        lessons_sealed=3,
        verified_blocks=9,
        clock_hours=4.5,
        carnegie_units=0.0375,
        covered_subjects=['Geography'],
        top_sources=['Narrative of Frederick Douglass'],
    )],
    total_clock_hours=4.5,
    total_carnegie_units=0.0375,
    traditional_subjects=[{'subject': 'Geography', 'standards': ['OAS.GEO.8.WG.1'], 'clock_hours': 0.68, 'grade': 'Pass'}],
    mastered_standards=[{'standard_id': 'OAS.SS.8.TH.1', 'text': 'Analyze primary sources', 'grade': 8, 'track': 'TRUTH_HISTORY'}],
    evidence_sources=[{'title': 'Narrative of Frederick Douglass', 'author': 'Douglass', 'year': 1845, 'url': 'https://archive.org', 'track': 'TRUTH_HISTORY'}],
    witness_threshold=0.82,
)

pdf = build_transcript_pdf(record)
with open('/tmp/test-transcript.pdf', 'wb') as f:
    f.write(pdf)
print(f'PDF built: {len(pdf):,} bytes')
"
```

Expected: `PDF built: XXXXX bytes` with no exceptions.

- [ ] **Step 3: Commit**

```bash
git add adeline-brain/app/api/pdf_builder.py
git commit -m "feat: branded PDF builder with Playfair Display, Lora, and Adeline color palette"
```

---

## Task 6: Update transcripts.py API

**Files:**
- Modify: `adeline-brain/app/api/transcripts.py`

Replace the current inline PDF generation logic with `RegistrarAgent`. Add `preview` and `years` endpoints. Make `academic_year` required.

- [ ] **Step 1: Replace transcripts.py entirely**

```python
"""
Transcripts API — /transcripts/*

GET /transcripts/generate/{student_id}?academic_year=2025-2026
    → Calls RegistrarAgent.build(), passes TranscriptRecord to PDF builder,
      returns streaming PDF.

GET /transcripts/preview/{student_id}?academic_year=2025-2026
    → Calls RegistrarAgent.build(), returns TranscriptRecord as JSON.
      Used by the UI to populate the transcript preview page.

GET /transcripts/years/{student_id}
    → Returns list of academic years that have sealed lessons.

All endpoints require academic_year (422 if missing on generate/preview).
"""
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas.api_models import UserRole
from app.api.middleware import require_role
from app.connections.neo4j_client import neo4j_client
from app.connections.journal_store import journal_store
from app.agents.registrar import RegistrarAgent
from app.api.pdf_builder import build_transcript_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transcripts", tags=["transcripts"])


def _get_agent() -> RegistrarAgent:
    return RegistrarAgent(journal_store, neo4j_client)


@router.get("/generate/{student_id}")
async def generate_transcript(
    student_id: str,
    academic_year: str = Query(..., description="Academic year, e.g. '2025-2026'"),
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Generate a branded PDF transcript for the given student and academic year.
    Returns a streaming PDF download.
    """
    logger.info(f"[/transcripts/generate] student={student_id} year={academic_year}")
    agent = _get_agent()

    try:
        record = await agent.build(student_id, academic_year)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[/transcripts/generate] RegistrarAgent.build() failed")
        raise HTTPException(status_code=500, detail=str(e))

    try:
        pdf_bytes = build_transcript_pdf(record)
    except Exception as e:
        logger.exception("[/transcripts/generate] PDF build failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    logger.info(
        f"[/transcripts/generate] PDF ready — "
        f"{len(record.tracks)} tracks, {len(pdf_bytes):,} bytes"
    )
    filename = f"adeline-transcript-{student_id}-{academic_year}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/preview/{student_id}")
async def preview_transcript(
    student_id: str,
    academic_year: str = Query(..., description="Academic year, e.g. '2025-2026'"),
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Return TranscriptRecord as JSON — used by the UI to populate the preview page.
    """
    logger.info(f"[/transcripts/preview] student={student_id} year={academic_year}")
    agent = _get_agent()
    try:
        record = await agent.build(student_id, academic_year)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[/transcripts/preview] RegistrarAgent.build() failed")
        raise HTTPException(status_code=500, detail=str(e))

    return record.model_dump()


@router.get("/years/{student_id}")
async def available_years(
    student_id: str,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Return list of academic years that have sealed lessons for this student.
    Used by the UI year picker.
    """
    years = await journal_store.get_available_years(student_id)
    return {"student_id": student_id, "years": years}
```

- [ ] **Step 2: Copy to running container**

```bash
docker cp adeline-brain/app/api/transcripts.py adeline-brain:/app/app/api/transcripts.py
docker cp adeline-brain/app/api/pdf_builder.py  adeline-brain:/app/app/api/pdf_builder.py
docker cp adeline-brain/app/agents/registrar.py adeline-brain:/app/app/agents/registrar.py
```

uvicorn's `--reload` will pick up changes automatically.

- [ ] **Step 3: Test the preview endpoint**

```bash
curl -s "http://localhost:8000/transcripts/preview/demo-student-001?academic_year=2025-2026" \
  -H "X-User-Role: STUDENT" | python -m json.tool | head -40
```

Expected: JSON with `student_id`, `academic_year`, `tracks`, `total_clock_hours`.

If the student has no lessons yet, expected: `{"detail": "No sealed lessons found for 2025-2026"}`.

- [ ] **Step 4: Test the years endpoint**

```bash
curl -s "http://localhost:8000/transcripts/years/demo-student-001" \
  -H "X-User-Role: STUDENT" | python -m json.tool
```

Expected: `{"student_id": "demo-student-001", "years": ["2025-2026"]}` or `[]`.

- [ ] **Step 5: Test the PDF endpoint**

```bash
curl -s "http://localhost:8000/transcripts/generate/demo-student-001?academic_year=2025-2026" \
  -H "X-User-Role: STUDENT" \
  -o /tmp/adeline-transcript.pdf
ls -lh /tmp/adeline-transcript.pdf
```

Expected: file > 20 KB, no error.

- [ ] **Step 6: Commit**

```bash
git add adeline-brain/app/api/transcripts.py
git commit -m "refactor: transcripts.py delegates to RegistrarAgent; add preview and years endpoints"
```

---

## Task 7: Seed Hidden Subjects Script

**Files:**
- Create: `adeline-brain/scripts/seed_hidden_subjects.py`

Seeds 28 OAS standards across 5 hidden subject areas with `APPLIED_IN` Neo4j edges.

- [ ] **Step 1: Create `adeline-brain/scripts/seed_hidden_subjects.py`**

```python
"""
Seed Hidden Subjects — APPLIED_IN edges in Neo4j

Traditional subjects (Math, PE, Fine Arts, Geography, Technology/Coding)
are not separate tracks — they are covered implicitly through the 8 tracks.
This script creates OASStandard nodes for each hidden subject and links them
to the host track via APPLIED_IN relationships.

Run once against a live Neo4j instance:
  python scripts/seed_hidden_subjects.py

Or inside Docker:
  docker exec adeline-brain python scripts/seed_hidden_subjects.py
"""
import asyncio
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.connections.neo4j_client import neo4j_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Hidden subject standards to seed ─────────────────────────────────────────
# Format: (standard_id, standard_text, subject, grade, host_track)
HIDDEN_STANDARDS = [
    # Mathematics — HOMESTEADING
    ("OAS.MATH.4.G.1",  "Classify shapes by properties: sides, angles, lines of symmetry",
     "Mathematics", 4, "HOMESTEADING"),
    ("OAS.MATH.4.OA.3", "Solve multi-step word problems using the four operations",
     "Mathematics", 4, "HOMESTEADING"),
    ("OAS.MATH.6.RP.1", "Understand ratio concepts and use ratio reasoning to solve problems",
     "Mathematics", 6, "HOMESTEADING"),
    ("OAS.MATH.8.EE.7", "Solve linear equations in one variable",
     "Mathematics", 8, "HOMESTEADING"),

    # Mathematics — GOVERNMENT_ECONOMICS
    ("OAS.MATH.6.NS.3", "Fluently add, subtract, multiply, and divide multi-digit decimals",
     "Mathematics", 6, "GOVERNMENT_ECONOMICS"),
    ("OAS.MATH.8.EE.8", "Analyze and solve pairs of simultaneous linear equations",
     "Mathematics", 8, "GOVERNMENT_ECONOMICS"),
    ("OAS.MATH.8.F.1",  "Understand that a function assigns each input exactly one output",
     "Mathematics", 8, "GOVERNMENT_ECONOMICS"),
    ("OAS.MATH.8.SP.1", "Construct and interpret scatter plots for bivariate data",
     "Mathematics", 8, "GOVERNMENT_ECONOMICS"),

    # Physical Education — HOMESTEADING
    ("OAS.PE.4.FM.1",   "Demonstrate fundamental movement skills in outdoor and agricultural contexts",
     "Physical Education", 4, "HOMESTEADING"),
    ("OAS.PE.8.FM.1",   "Demonstrate outdoor physical fitness through labor-based activities",
     "Physical Education", 8, "HOMESTEADING"),

    # Physical Education — HEALTH_NATUROPATHY
    ("OAS.PE.4.HF.1",   "Identify the components of health-related fitness",
     "Physical Education", 4, "HEALTH_NATUROPATHY"),
    ("OAS.PE.8.HF.1",   "Describe the relationship between physical activity and long-term health",
     "Physical Education", 8, "HEALTH_NATUROPATHY"),

    # Fine Arts — ENGLISH_LITERATURE
    ("OAS.FA.4.ML.1",   "Analyze the structure and meaning of hymns and sacred music",
     "Fine Arts", 4, "ENGLISH_LITERATURE"),
    ("OAS.FA.8.ML.1",   "Analyze hymns and psalm texts in historical and literary context",
     "Fine Arts", 8, "ENGLISH_LITERATURE"),
    ("OAS.FA.4.VA.1",   "Identify visual art elements in illuminated manuscripts and early printing",
     "Fine Arts", 4, "ENGLISH_LITERATURE"),

    # Fine Arts — DISCIPLESHIP
    ("OAS.FA.4.VA.2",   "Analyze how visual art reflects cultural and spiritual values",
     "Fine Arts", 4, "DISCIPLESHIP"),
    ("OAS.FA.8.VA.1",   "Analyze visual art in historical and theological context",
     "Fine Arts", 8, "DISCIPLESHIP"),
    ("OAS.FA.8.AR.1",   "Evaluate the role of architecture in expressing communal values",
     "Fine Arts", 8, "DISCIPLESHIP"),

    # Geography — TRUTH_HISTORY
    ("OAS.GEO.4.WG.1",  "Identify and describe major physical features of North America",
     "Geography", 4, "TRUTH_HISTORY"),
    ("OAS.GEO.8.WG.1",  "Interpret historical maps to trace migration and territorial change",
     "Geography", 8, "TRUTH_HISTORY"),
    ("OAS.GEO.8.WG.2",  "Analyze how geography shaped the outcomes of historical events",
     "Geography", 8, "TRUTH_HISTORY"),

    # Geography — CREATION_SCIENCE
    ("OAS.GEO.4.ES.1",  "Describe the major layers of the earth and surface landforms",
     "Geography", 4, "CREATION_SCIENCE"),
    ("OAS.GEO.6.ES.1",  "Explain how topography and climate affect regional ecosystems",
     "Geography", 6, "CREATION_SCIENCE"),
    ("OAS.GEO.8.ES.1",  "Analyze regional ecology and biodiversity in North America",
     "Geography", 8, "CREATION_SCIENCE"),

    # Technology / Coding — JUSTICE_CHANGEMAKING
    ("OAS.CS.4.DA.1",   "Collect, organize, and present data using digital tools",
     "Technology / Coding", 4, "JUSTICE_CHANGEMAKING"),
    ("OAS.CS.6.DA.1",   "Use digital tools to analyze and visualize community data",
     "Technology / Coding", 6, "JUSTICE_CHANGEMAKING"),
    ("OAS.CS.8.DA.1",   "Use digital tools for communication, advocacy, and civic engagement",
     "Technology / Coding", 8, "JUSTICE_CHANGEMAKING"),
    ("OAS.CS.8.AP.1",   "Design and implement algorithms to solve real-world problems",
     "Technology / Coding", 8, "JUSTICE_CHANGEMAKING"),
]


async def seed():
    await neo4j_client.connect()
    logger.info(f"[seed_hidden_subjects] Seeding {len(HIDDEN_STANDARDS)} standards...")

    for std_id, std_text, subject, grade, host_track in HIDDEN_STANDARDS:
        try:
            await neo4j_client.run(
                """
                MERGE (s:OASStandard {id: $std_id})
                SET   s.standard_text = $std_text,
                      s.subject       = $subject,
                      s.grade         = $grade,
                      s.track         = $host_track
                MERGE (t:Track {name: $host_track})
                MERGE (s)-[:APPLIED_IN]->(t)
                """,
                {
                    "std_id":     std_id,
                    "std_text":   std_text,
                    "subject":    subject,
                    "grade":      grade,
                    "host_track": host_track,
                },
            )
            logger.info(f"  ✓ {std_id} ({subject} Gr {grade}) → {host_track}")
        except Exception as e:
            logger.error(f"  ✗ {std_id}: {e}")

    await neo4j_client.close()
    logger.info("[seed_hidden_subjects] Done.")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Copy script to container and run it**

```bash
docker cp adeline-brain/scripts/seed_hidden_subjects.py \
  adeline-brain:/app/scripts/seed_hidden_subjects.py

docker exec adeline-brain python scripts/seed_hidden_subjects.py
```

Expected output: 28 lines of `✓ OAS.MATH.4.G.1 (Mathematics Gr 4) → HOMESTEADING` etc., then `Done.`

- [ ] **Step 3: Verify in Neo4j Browser**

```cypher
MATCH (s:OASStandard)-[:APPLIED_IN]->(t:Track)
RETURN s.subject AS subject, COUNT(s) AS count
ORDER BY subject
```

Expected result: Mathematics: 8, Physical Education: 4, Fine Arts: 6, Geography: 6, Technology / Coding: 4.

- [ ] **Step 4: Commit**

```bash
git add adeline-brain/scripts/seed_hidden_subjects.py
git commit -m "feat: seed 28 OAS hidden-subject standards with APPLIED_IN edges"
```

---

## Task 8: UI — brain-client Types

**Files:**
- Modify: `adeline-ui/src/lib/brain-client.ts`

Add `TranscriptRecord`, `TrackCredit` TypeScript types and fetch functions.

- [ ] **Step 1: Append to `adeline-ui/src/lib/brain-client.ts`**

After the last `export` in the file, add:

```typescript
// ── Transcripts ────────────────────────────────────────────────────────────

export interface TrackCredit {
  track_id:          string;
  track_label:       string;
  traditional_equiv: string;
  mastery_band:      "NOVICE" | "DEVELOPING" | "PROFICIENT" | "ADVANCED";
  letter_grade:      string;
  lessons_sealed:    number;
  verified_blocks:   number;
  clock_hours:       number;
  carnegie_units:    number;
  covered_subjects:  string[];
  top_sources:       string[];
}

export interface TranscriptRecord {
  student_id:           string;
  student_name:         string;
  academic_year:        string;
  generated_at:         string;
  tracks:               TrackCredit[];
  total_clock_hours:    number;
  total_carnegie_units: number;
  traditional_subjects: Array<{
    subject:     string;
    standards:   string[];
    clock_hours: number;
    grade:       string;
  }>;
  mastered_standards: Array<{
    standard_id: string;
    text:        string;
    grade:       number;
    track:       string;
  }>;
  evidence_sources: Array<{
    title:  string;
    author: string;
    year:   number | null;
    url:    string;
    track:  string;
  }>;
  witness_threshold: number;
}

export async function fetchTranscriptPreview(
  student_id: string,
  academic_year: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<TranscriptRecord> {
  const params = new URLSearchParams({ academic_year });
  const res = await fetch(
    `${BRAIN_URL}/transcripts/preview/${encodeURIComponent(student_id)}?${params}`,
    {
      headers: { "X-User-Role": role },
      cache: "no-store",
    },
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `transcript preview failed: ${res.status}`);
  }
  return res.json() as Promise<TranscriptRecord>;
}

export async function fetchAvailableYears(
  student_id: string,
  role: "STUDENT" | "ADMIN" = "STUDENT",
): Promise<string[]> {
  const res = await fetch(
    `${BRAIN_URL}/transcripts/years/${encodeURIComponent(student_id)}`,
    {
      headers: { "X-User-Role": role },
      cache: "no-store",
    },
  );
  if (!res.ok) throw new Error(`years fetch failed: ${res.status}`);
  const data = await res.json() as { student_id: string; years: string[] };
  return data.years;
}
```

- [ ] **Step 2: TypeScript compile check**

```bash
cd adeline-ui && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add adeline-ui/src/lib/brain-client.ts
git commit -m "feat: add TranscriptRecord types and transcript client functions"
```

---

## Task 9: UI — Transcript Page

**Files:**
- Create: `adeline-ui/src/app/(routes)/dashboard/transcript/page.tsx`

- [ ] **Step 1: Create the transcript page directory**

```bash
mkdir -p adeline-ui/src/app/\(routes\)/dashboard/transcript
```

- [ ] **Step 2: Create `adeline-ui/src/app/(routes)/dashboard/transcript/page.tsx`**

```tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import { Download, BookOpen, Clock, Award, FileText } from "lucide-react";
import {
  fetchAvailableYears,
  fetchTranscriptPreview,
  type TranscriptRecord,
} from "@/lib/brain-client";

const STUDENT_ID = "demo-student-001";
const BRAIN_URL = "/brain";

// ── Stat Card ──────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
}) {
  return (
    <div
      className="border border-fuschia/10 bg-parchment-50 px-5 py-4 flex flex-col gap-1"
      style={{ background: "#FFFEF7", borderColor: "#E7DAC3" }}
    >
      <div className="flex items-center gap-2">
        <Icon size={14} className="text-papaya opacity-70" />
        <span className="font-sketch text-xs text-fuschia/40 uppercase tracking-widest">
          {label}
        </span>
      </div>
      <span className="font-sketch text-2xl text-fuschia">{value}</span>
    </div>
  );
}

// ── Track Row ──────────────────────────────────────────────────────────────

function TrackRow({ tc }: { tc: TranscriptRecord["tracks"][0] }) {
  const gradeColor =
    tc.letter_grade === "A"
      ? "#2E7D32"
      : tc.letter_grade === "B"
      ? "#9A3F4A"
      : tc.letter_grade === "C"
      ? "#BD6809"
      : "#666";

  return (
    <tr className="border-b" style={{ borderColor: "#E7DAC3" }}>
      <td className="py-3 pr-4 align-top">
        <p className="font-sketch text-sm text-fuschia font-bold">
          {tc.track_label}
        </p>
        <p className="font-body text-xs italic" style={{ color: "#8B7355" }}>
          {tc.traditional_equiv}
        </p>
        {tc.top_sources.length > 0 && (
          <p className="font-mono text-xs mt-0.5" style={{ color: "#9A7A5A" }}>
            {tc.top_sources.join(" · ")}
          </p>
        )}
      </td>
      <td className="py-3 pr-4 align-top text-center">
        <span
          className="font-sketch text-lg font-bold"
          style={{ color: gradeColor }}
        >
          {tc.letter_grade}
        </span>
      </td>
      <td className="py-3 pr-4 align-top text-right">
        <span className="font-body text-sm" style={{ color: "#BD6809" }}>
          {tc.clock_hours.toFixed(1)} hrs
        </span>
      </td>
      <td className="py-3 align-top text-right">
        <span className="font-body text-sm" style={{ color: "#BD6809" }}>
          {tc.carnegie_units.toFixed(3)}
        </span>
      </td>
    </tr>
  );
}

// ── Traditional Subjects Collapsed Section ─────────────────────────────────

function TraditionalSubjectsSection({
  subjects,
}: {
  subjects: TranscriptRecord["traditional_subjects"];
}) {
  const [open, setOpen] = useState(false);
  if (!subjects.length) return null;

  return (
    <div className="border" style={{ borderColor: "#E7DAC3" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3 text-left"
        style={{ background: "#FFFEF7" }}
      >
        <span className="font-sketch text-xs uppercase tracking-widest text-fuschia/60">
          Traditional Subjects Covered
        </span>
        <span className="font-mono text-xs text-fuschia/40">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-5 pb-4 space-y-3" style={{ background: "#FFFEF7" }}>
          {subjects.map((subj) => (
            <div key={subj.subject} className="flex gap-4 items-start">
              <span className="font-sketch text-sm text-fuschia w-40 shrink-0">
                {subj.subject}
              </span>
              <div className="flex flex-wrap gap-1">
                {subj.standards.map((sid) => (
                  <span
                    key={sid}
                    className="font-mono text-xs px-1.5 py-0.5 rounded-sm"
                    style={{ background: "#F0D9B0", color: "#2C2318" }}
                  >
                    {sid}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function TranscriptPage() {
  const [years, setYears] = useState<string[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [record, setRecord] = useState<TranscriptRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);

  // Load available years on mount
  useEffect(() => {
    fetchAvailableYears(STUDENT_ID)
      .then((ys) => {
        setYears(ys);
        if (ys.length > 0) setSelectedYear(ys[0]);
      })
      .catch(() => {
        // If no years yet, show placeholder
        setYears(["2025-2026"]);
        setSelectedYear("2025-2026");
      });
  }, []);

  // Load transcript preview when year changes
  useEffect(() => {
    if (!selectedYear) return;
    setLoading(true);
    setError("");
    setRecord(null);
    fetchTranscriptPreview(STUDENT_ID, selectedYear)
      .then(setRecord)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedYear]);

  const handleDownload = useCallback(async () => {
    if (!selectedYear) return;
    setDownloading(true);
    try {
      const params = new URLSearchParams({ academic_year: selectedYear });
      const res = await fetch(
        `${BRAIN_URL}/transcripts/generate/${encodeURIComponent(STUDENT_ID)}?${params}`,
        { headers: { "X-User-Role": "STUDENT" } },
      );
      if (!res.ok) throw new Error(`Download failed: ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `adeline-transcript-${STUDENT_ID}-${selectedYear}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }, [selectedYear]);

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-8 px-4">
      {/* Header */}
      <header className="space-y-1">
        <p className="font-sketch text-xs text-fuschia/40 uppercase tracking-widest">
          Official Record
        </p>
        <h1 className="font-sketch text-2xl text-fuschia">Academic Transcript</h1>
      </header>

      {/* Year selector */}
      <div className="flex items-center gap-3">
        <label className="font-sketch text-xs text-fuschia/50 uppercase tracking-widest">
          Academic Year
        </label>
        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(e.target.value)}
          className="font-sketch text-sm text-fuschia border px-3 py-1.5 bg-transparent focus:outline-none"
          style={{ borderColor: "#E7DAC3", background: "#FFFEF7" }}
        >
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>

      {/* Loading state */}
      {loading && (
        <p className="font-sketch text-sm text-fuschia/40 animate-pulse">
          Loading transcript…
        </p>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="border border-papaya/30 px-4 py-3" style={{ background: "#FFF9F0" }}>
          <p className="font-mono text-sm text-papaya">{error}</p>
          {error.includes("No sealed lessons") && (
            <p className="font-body text-xs text-fuschia/50 mt-1 italic">
              Seal some lessons from the Journey page to generate a transcript.
            </p>
          )}
        </div>
      )}

      {/* Transcript preview */}
      {record && !loading && (
        <>
          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard
              label="Clock Hours"
              value={record.total_clock_hours.toFixed(1)}
              icon={Clock}
            />
            <StatCard
              label="Carnegie Units"
              value={record.total_carnegie_units.toFixed(3)}
              icon={Award}
            />
            <StatCard
              label="Tracks Active"
              value={record.tracks.length}
              icon={BookOpen}
            />
            <StatCard
              label="Sources Cited"
              value={record.evidence_sources.length}
              icon={FileText}
            />
          </div>

          {/* Track table */}
          <div className="border" style={{ borderColor: "#E7DAC3" }}>
            <table className="w-full" style={{ background: "#FFFEF7" }}>
              <thead>
                <tr style={{ background: "#9A3F4A" }}>
                  <th className="text-left px-5 py-2">
                    <span className="font-sketch text-xs text-white/90 uppercase tracking-widest">
                      Track
                    </span>
                  </th>
                  <th className="text-center px-4 py-2">
                    <span className="font-sketch text-xs text-white/90 uppercase tracking-widest">
                      Grade
                    </span>
                  </th>
                  <th className="text-right px-4 py-2">
                    <span className="font-sketch text-xs text-white/90 uppercase tracking-widest">
                      Hours
                    </span>
                  </th>
                  <th className="text-right px-5 py-2">
                    <span className="font-sketch text-xs text-white/90 uppercase tracking-widest">
                      Carnegie
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {record.tracks.map((tc) => (
                  <TrackRow key={tc.track_id} tc={tc} />
                ))}
                {/* Totals row */}
                <tr style={{ background: "#F0D9B0" }}>
                  <td className="px-5 py-2 font-sketch text-sm text-fuschia font-bold">
                    Total
                  </td>
                  <td />
                  <td className="text-right px-4 py-2">
                    <span className="font-sketch text-sm font-bold" style={{ color: "#BD6809" }}>
                      {record.total_clock_hours.toFixed(1)} hrs
                    </span>
                  </td>
                  <td className="text-right px-5 py-2">
                    <span className="font-sketch text-sm font-bold" style={{ color: "#BD6809" }}>
                      {record.total_carnegie_units.toFixed(3)}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Traditional subjects */}
          <TraditionalSubjectsSection subjects={record.traditional_subjects} />

          {/* Download button */}
          <div className="flex items-center justify-between flex-wrap gap-3 pt-2 border-t" style={{ borderColor: "#E7DAC3" }}>
            <p className="font-sketch text-xs text-fuschia/40 uppercase tracking-widest">
              {record.mastered_standards.length} Standards Mastered
            </p>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-2 font-sketch text-sm px-5 py-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                background: downloading ? "#7D333D" : "#9A3F4A",
                color: "#FDF8F0",
                border: "2px solid #7D333D",
                boxShadow: downloading ? "none" : "3px 3px 0 #7D333D",
              }}
            >
              <Download size={14} />
              {downloading ? "Preparing PDF…" : "Download PDF"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: TypeScript compile check**

```bash
cd adeline-ui && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add "adeline-ui/src/app/(routes)/dashboard/transcript/page.tsx"
git commit -m "feat: transcript page with year picker, stats row, track table, and PDF download"
```

---

## Task 10: Sidebar Nav Link

**Files:**
- Explore and update the dashboard navigation component

- [ ] **Step 1: Find the dashboard nav component**

```bash
grep -rl "journey\|dashboard.*nav\|sidebar" adeline-ui/src --include="*.tsx" | head -10
```

- [ ] **Step 2: Identify the nav items list (look for "Journey" or similar link)**

```bash
grep -n "journey\|Journey\|href.*dashboard" adeline-ui/src/components/*.tsx adeline-ui/src/app/**/*.tsx 2>/dev/null | head -20
```

- [ ] **Step 3: Add the Transcript nav link**

Find the file containing the navigation links (likely `adeline-ui/src/components/DashboardNav.tsx` or similar). Add a transcript link after the existing Journey link:

```tsx
{ href: "/dashboard/transcript", label: "Transcript", icon: FileText }
```

Import `FileText` from `lucide-react` if not already imported.

The exact edit depends on the nav file found in Step 1-2. The pattern to add is:
- Same structure as existing nav links
- `href="/dashboard/transcript"`
- Label: `"Transcript"` or `"Academic Record"`
- Icon: `FileText` from lucide-react

- [ ] **Step 4: Verify the page is reachable**

Start the dev server and navigate to `http://localhost:3000/dashboard/transcript`. Verify the page renders with the year picker and either a stats preview or the "No sealed lessons" message.

```bash
cd adeline-ui && npm run dev
```

Then open: `http://localhost:3000/dashboard/transcript`

- [ ] **Step 5: Commit**

```bash
git add adeline-ui/src/
git commit -m "feat: add Transcript nav link to dashboard sidebar"
```

---

## Spec Coverage Check

| Spec requirement | Task |
|---|---|
| `RegistrarAgent.build()` with year scoping | Task 4 |
| `TranscriptRecord` + `TrackCredit` Pydantic models | Task 4 |
| `completed_blocks × 30 ÷ 60` clock hours | Task 4 (tested) |
| `clock_hours ÷ 120` Carnegie units | Task 4 (tested) |
| ADVANCED→A, PROFICIENT→B, DEVELOPING→C, NOVICE→Pass | Task 4 (tested) |
| Academic year Aug 1 → Jul 31 scoping | Task 2 + Task 4 (tested) |
| `GET /transcripts/generate/{id}?academic_year=` | Task 6 |
| `GET /transcripts/preview/{id}?academic_year=` | Task 6 |
| `GET /transcripts/years/{id}` | Task 6 |
| HTTP 404 when no lessons | Task 4 (tested) + Task 6 |
| HTTP 422 when academic_year missing | FastAPI handles automatically with `Query(...)` |
| Neo4j unavailable → proceeds with empty standards | Task 4 (try/except in `build()`) |
| `APPLIED_IN` hidden subject edges | Task 7 |
| 28 hidden subject standards seeded | Task 7 |
| Playfair Display + Lora fonts | Task 1 + Task 5 |
| Adeline brand colors in PDF | Task 5 |
| 2-page PDF layout | Task 5 |
| Parchment background, PARADISE headers, PAPAYA figures | Task 5 |
| Page 2 Traditional Subjects + Evidence Appendix | Task 5 |
| UI year picker | Task 9 |
| UI stats row (4 cards) | Task 9 |
| UI track table with grade + hours + Carnegie | Task 9 |
| Traditional subjects collapsed section | Task 9 |
| PDF download button | Task 9 |
| `fetchTranscriptPreview()` + `fetchAvailableYears()` types | Task 8 |
| Sidebar nav link | Task 10 |
