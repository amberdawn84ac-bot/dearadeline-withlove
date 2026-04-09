# Integrated Book Recommendations + Reading-to-Credit Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3-4 recommended books to the learning plan response, and auto-award credits when a student finishes a book with a reflection.

**Architecture:** The learning plan endpoint calls a new `get_gap_weighted_recommendations()` function that reuses the existing `bookshelf_search.search_books_by_embedding` with credit-gap weighting applied to scores. A new `reading_credit.py` service handles the three ledger writes (evidence, credit, standards) when a reading session is marked finished with a reflection.

**Tech Stack:** Python/FastAPI (backend), React/Next.js (frontend), asyncpg (DB), pgvector (embeddings), OpenAI text-embedding-3-small

**Spec:** `docs/superpowers/specs/2026-04-08-integrated-book-recommendations-design.md`

---

## File Structure

### New Files
- `adeline-brain/app/services/reading_credit.py` — `award_reading_credit()` function: idempotency check + three ledger writes
- `adeline-brain/tests/test_reading_credit.py` — Tests for credit calculation and ledger logic
- `adeline-ui/src/components/dashboard/RecommendedBooks.tsx` — Book card grid for dashboard

### Modified Files
- `adeline-brain/app/api/learning_plan.py` — Add `recommended_books` to response model and endpoint
- `adeline-brain/app/api/books.py` — Extract `get_gap_weighted_recommendations()` function
- `adeline-brain/app/api/reading_session.py` — Call `award_reading_credit()` on finish+reflection
- `adeline-ui/src/lib/brain-client.ts` — Add `BookRecommendation` type to `LearningPlanResponse`
- `adeline-ui/src/app/(routes)/dashboard/page.tsx` — Render `RecommendedBooks` section

---

## Task 1: Create `reading_credit.py` — Credit Calculation + Ledger Writes

**Files:**
- Create: `adeline-brain/app/services/reading_credit.py`
- Create: `adeline-brain/tests/test_reading_credit.py`

### Step 1: Write failing tests for credit calculation

- [ ] **Step 1a: Write test file**

```python
# adeline-brain/tests/test_reading_credit.py
"""Tests for reading_credit service — credit calculation and ledger writes."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.reading_credit import (
    calculate_reading_credit,
    TRACK_TO_GRADUATION_BUCKET,
    get_reading_standards,
)


class TestCreditCalculation:
    """Test the credit formula: hours/120 * lexile_multiplier."""

    def test_grade_level_book_10_hours(self):
        # 10 hours at grade level: (10/120) * 1.0 = 0.0833
        credit = calculate_reading_credit(
            reading_minutes=600,
            book_lexile=800,
            grade_level="8",
        )
        assert round(credit, 4) == 0.0833

    def test_above_grade_level_book(self):
        # 12 hours above grade level: (12/120) * 1.2 = 0.12
        credit = calculate_reading_credit(
            reading_minutes=720,
            book_lexile=1000,
            grade_level="8",  # grade 8 max is 900
        )
        assert round(credit, 2) == 0.12

    def test_below_grade_level_book(self):
        # 12 hours below grade level: (12/120) * 0.8 = 0.08
        credit = calculate_reading_credit(
            reading_minutes=720,
            book_lexile=600,
            grade_level="8",  # grade 8 min is 800
        )
        assert round(credit, 2) == 0.08

    def test_zero_reading_time(self):
        credit = calculate_reading_credit(
            reading_minutes=0,
            book_lexile=800,
            grade_level="8",
        )
        assert credit == 0.0

    def test_kindergarten_grade_level(self):
        credit = calculate_reading_credit(
            reading_minutes=120,  # 2 hours
            book_lexile=300,
            grade_level="K",
        )
        # (2/120) * 1.0 = 0.0167
        assert round(credit, 4) == 0.0167


class TestTrackToBucket:
    """Test track-to-graduation-bucket mapping."""

    def test_english_literature_maps_to_english_core(self):
        assert TRACK_TO_GRADUATION_BUCKET["ENGLISH_LITERATURE"] == "ENGLISH_CORE"

    def test_truth_history_maps_to_social_studies(self):
        assert TRACK_TO_GRADUATION_BUCKET["TRUTH_HISTORY"] == "SOCIAL_STUDIES"

    def test_creation_science_maps_to_science_core(self):
        assert TRACK_TO_GRADUATION_BUCKET["CREATION_SCIENCE"] == "SCIENCE_CORE"

    def test_applied_mathematics_maps_to_math_core(self):
        assert TRACK_TO_GRADUATION_BUCKET["APPLIED_MATHEMATICS"] == "MATH_CORE"

    def test_creative_economy_maps_to_fine_arts(self):
        assert TRACK_TO_GRADUATION_BUCKET["CREATIVE_ECONOMY"] == "FINE_ARTS"

    def test_discipleship_maps_to_electives(self):
        assert TRACK_TO_GRADUATION_BUCKET["DISCIPLESHIP"] == "ELECTIVES"


class TestReadingStandards:
    """Test K-8 reading standards mapping."""

    def test_literature_track_uses_rl_prefix(self):
        standards = get_reading_standards("ENGLISH_LITERATURE", 5)
        assert any(s["code"].startswith("RL.5") for s in standards)

    def test_informational_track_uses_ri_prefix(self):
        standards = get_reading_standards("TRUTH_HISTORY", 5)
        assert any(s["code"].startswith("RI.5") for s in standards)

    def test_returns_empty_for_high_school(self):
        standards = get_reading_standards("ENGLISH_LITERATURE", 9)
        assert standards == []

    def test_returns_1_to_2_standards(self):
        standards = get_reading_standards("ENGLISH_LITERATURE", 3)
        assert 1 <= len(standards) <= 2
```

- [ ] **Step 1b: Run tests to verify they fail**

Run: `cd adeline-brain && python -m pytest tests/test_reading_credit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.reading_credit'`

### Step 2: Implement `reading_credit.py`

- [ ] **Step 2a: Create the service file**

```python
# adeline-brain/app/services/reading_credit.py
"""
Reading Credit Service — awards credits when a student finishes a book with a reflection.

Three ledger writes:
1. EvidenceLedgerEntry — the reading + reflection as portfolio evidence
2. CreditLedgerEntry — credit hours toward graduation bucket
3. StandardsLedgerEntry — K-8 reading standards (skipped for 9-12)

Credit formula: (reading_minutes / 60) / 120 * lexile_multiplier
  - 120 hours of reading = 1.0 credit
  - lexile_multiplier: 1.2 (above grade), 1.0 (at grade), 0.8 (below grade)
"""
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Grade-level lexile ranges (same as books.py)
GRADE_TO_LEXILE = {
    "K": (250, 350), "1": (300, 400), "2": (400, 500),
    "3": (500, 600), "4": (600, 700), "5": (650, 750),
    "6": (700, 800), "7": (750, 850), "8": (800, 900),
    "9": (850, 950), "10": (900, 1000), "11": (950, 1050),
    "12": (1000, 1100),
}

# Track → graduation bucket (from spec)
TRACK_TO_GRADUATION_BUCKET = {
    "ENGLISH_LITERATURE": "ENGLISH_CORE",
    "TRUTH_HISTORY": "SOCIAL_STUDIES",
    "JUSTICE_CHANGEMAKING": "SOCIAL_STUDIES",
    "GOVERNMENT_ECONOMICS": "SOCIAL_STUDIES",
    "CREATION_SCIENCE": "SCIENCE_CORE",
    "HOMESTEADING": "SCIENCE_CORE",
    "HEALTH_NATUROPATHY": "SCIENCE_CORE",
    "APPLIED_MATHEMATICS": "MATH_CORE",
    "DISCIPLESHIP": "ELECTIVES",
    "CREATIVE_ECONOMY": "FINE_ARTS",
}

# Literature tracks use RL (Reading Literature) standards; others use RI (Reading Informational)
LITERATURE_TRACKS = {"ENGLISH_LITERATURE", "DISCIPLESHIP"}


def _parse_grade(grade_level: str) -> int:
    """Parse grade string to int. 'K' → 0, '5' → 5, '11th' → 11."""
    if not grade_level:
        return 0
    grade_level = grade_level.strip().upper()
    if grade_level.startswith("K"):
        return 0
    import re
    match = re.match(r'(\d+)', grade_level)
    return int(match.group(1)) if match else 0


def calculate_reading_credit(
    reading_minutes: int,
    book_lexile: int,
    grade_level: str,
) -> float:
    """
    Calculate credit earned from reading a book.

    Formula: (reading_hours / 120) * lexile_multiplier
    - 120 hours = 1.0 credit
    - Multiplier: 1.2 above grade, 1.0 at grade, 0.8 below grade
    """
    if reading_minutes <= 0:
        return 0.0

    hours = reading_minutes / 60.0
    base_credit = hours / 120.0

    # Get lexile range for grade
    grade_key = grade_level.strip().upper()
    if grade_key.startswith("K"):
        grade_key = "K"
    else:
        import re
        match = re.match(r'(\d+)', grade_key)
        grade_key = match.group(1) if match else "8"

    lexile_min, lexile_max = GRADE_TO_LEXILE.get(grade_key, (250, 1200))

    if book_lexile > lexile_max:
        multiplier = 1.2
    elif book_lexile < lexile_min:
        multiplier = 0.8
    else:
        multiplier = 1.0

    return base_credit * multiplier


def get_reading_standards(track: str, grade_num: int) -> list[dict]:
    """
    Get K-8 reading standards for a completed book.

    Returns 1-2 standards based on track type:
    - Literature tracks → RL.{grade}.2 (theme), RL.{grade}.10 (comprehension)
    - Informational tracks → RI.{grade}.2 (central idea), RI.{grade}.10 (comprehension)

    Returns empty list for grades 9+.
    """
    if grade_num > 8 or grade_num < 0:
        return []

    grade = max(grade_num, 1)  # Standards start at grade 1
    prefix = "RL" if track in LITERATURE_TRACKS else "RI"

    return [
        {
            "code": f"{prefix}.{grade}.2",
            "framework": "READING",
            "subject": "ELA" if track in LITERATURE_TRACKS else track,
            "description": f"Determine central idea/theme of grade {grade} text",
        },
        {
            "code": f"{prefix}.{grade}.10",
            "framework": "READING",
            "subject": "ELA" if track in LITERATURE_TRACKS else track,
            "description": f"Read and comprehend grade {grade} level text independently",
        },
    ]


def _lexile_mastery_score(book_lexile: int, grade_level: str) -> float:
    """Calculate mastery score (0.0-1.0) based on how book lexile compares to grade level."""
    grade_key = grade_level.strip().upper()
    if grade_key.startswith("K"):
        grade_key = "K"
    else:
        import re
        match = re.match(r'(\d+)', grade_key)
        grade_key = match.group(1) if match else "8"

    lexile_min, lexile_max = GRADE_TO_LEXILE.get(grade_key, (250, 1200))
    midpoint = (lexile_min + lexile_max) / 2

    if book_lexile >= lexile_max:
        return min(1.0, 0.8 + (book_lexile - lexile_max) / 500)
    elif book_lexile >= lexile_min:
        return 0.6 + 0.2 * ((book_lexile - lexile_min) / max(lexile_max - lexile_min, 1))
    else:
        return max(0.2, 0.6 - (lexile_min - book_lexile) / 500)


async def award_reading_credit(
    session_id: str,
    student_id: str,
    book_id: str,
    book_title: str,
    book_track: str,
    book_lexile: int,
    reading_minutes: int,
    student_reflection: str,
    grade_level: str,
    completed_at: datetime | None = None,
) -> dict:
    """
    Award credit for a completed book with reflection.

    Writes to three ledger tables:
    1. EvidenceLedgerEntry — portfolio evidence (reading + reflection)
    2. CreditLedgerEntry — credit hours toward graduation bucket
    3. StandardsLedgerEntry — K-8 reading standards (skipped for 9-12)

    Returns dict with credit_awarded and standards_count.
    Idempotent: checks if credit already awarded for this session.
    """
    from app.config import get_db_conn

    conn = await get_db_conn()
    try:
        # Idempotency check
        existing = await conn.fetchval(
            'SELECT COUNT(*) FROM "CreditLedgerEntry" WHERE "sourceId" = $1 AND source = \'reading\'',
            session_id,
        )
        if existing and existing > 0:
            logger.info(f"[ReadingCredit] Credit already awarded for session {session_id}")
            return {"credit_awarded": 0.0, "standards_count": 0, "already_awarded": True}

        # Calculate credit
        credit = calculate_reading_credit(reading_minutes, book_lexile, grade_level)
        bucket = TRACK_TO_GRADUATION_BUCKET.get(book_track, "ELECTIVES")
        mastery_score = _lexile_mastery_score(book_lexile, grade_level)
        activity_date = completed_at or datetime.now(timezone.utc)
        hours = reading_minutes / 60.0

        # 1. EvidenceLedgerEntry
        await conn.execute(
            """
            INSERT INTO "EvidenceLedgerEntry" (
                id, "studentId", "artifactType", title, "masteryScore",
                hours, "activityDate", "evaluatorNotes", bucket,
                "proposedCourse", "isApproved", "createdAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
            """,
            str(uuid.uuid4()), student_id, "reading", book_title,
            mastery_score, hours, activity_date, student_reflection,
            bucket, f"{book_title} by reading", True,
        )

        # 2. CreditLedgerEntry
        await conn.execute(
            """
            INSERT INTO "CreditLedgerEntry" (
                id, "studentId", bucket, "hoursEarned", source, "sourceId", "createdAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """,
            str(uuid.uuid4()), student_id, bucket, credit, "reading", session_id,
        )

        # 3. StandardsLedgerEntry (K-8 only)
        grade_num = _parse_grade(grade_level)
        standards = get_reading_standards(book_track, grade_num)
        for standard in standards:
            await conn.execute(
                """
                INSERT INTO "StandardsLedgerEntry" (
                    id, "studentId", framework, subject, code,
                    confidence, "lessonId", "addressedAt", "createdAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                str(uuid.uuid4()), student_id, standard["framework"],
                standard["subject"], standard["code"],
                mastery_score, session_id,
            )

        logger.info(
            f"[ReadingCredit] Awarded {credit:.4f} credits ({bucket}) + "
            f"{len(standards)} standards for session {session_id}"
        )

        return {
            "credit_awarded": credit,
            "bucket": bucket,
            "standards_count": len(standards),
            "already_awarded": False,
        }

    except Exception as e:
        logger.error(f"[ReadingCredit] Failed to award credit for session {session_id}: {e}")
        raise
    finally:
        await conn.close()
```

- [ ] **Step 2b: Run tests**

Run: `cd adeline-brain && python -m pytest tests/test_reading_credit.py -v`
Expected: All tests PASS (the pure function tests and mapping tests should pass; the async `award_reading_credit` is tested via the integration in Task 3)

- [ ] **Step 2c: Commit**

```bash
git add adeline-brain/app/services/reading_credit.py adeline-brain/tests/test_reading_credit.py
git commit -m "feat: Add reading_credit service — credit calculation + ledger writes"
```

---

## Task 2: Add `recommended_books` to Learning Plan

**Files:**
- Modify: `adeline-brain/app/api/books.py` — add `get_gap_weighted_recommendations()`
- Modify: `adeline-brain/app/api/learning_plan.py:71-133` — add `BookRecommendation` model and `recommended_books` field
- Modify: `adeline-brain/app/api/learning_plan.py:626-871` — call recommendations in endpoint

### Step 1: Add `get_gap_weighted_recommendations()` to books.py

- [ ] **Step 1a: Add the function at the end of books.py (before the last blank line)**

Add this function after the `get_book` endpoint (after line 596) in `adeline-brain/app/api/books.py`:

```python
# ── Gap-Weighted Recommendations (called by learning_plan.py) ──────────────

async def get_gap_weighted_recommendations(
    student_id: str,
    grade_level: str,
    interests: list,
    credit_gaps: list,
    weakest_track: str | None,
    is_high_school: bool,
    limit: int = 4,
) -> list:
    """
    Get book recommendations weighted by credit gaps (9-12) or weakest track (K-8).

    Called internally by learning_plan.py — not an API endpoint.

    Args:
        student_id: Student UUID
        grade_level: Grade level string (e.g., "5", "K", "11")
        interests: Student interest list from onboarding
        credit_gaps: List of CreditGap dicts with 'bucket' and 'remaining' keys
        weakest_track: Track name with lowest mastery (for K-8 boosting)
        is_high_school: True for 9-12, False for K-8
        limit: Number of books to return (default 4)

    Returns:
        List of book dicts with id, title, author, track, lexile_level, grade_band, cover_url, relevance_score
    """
    from app.connections.bookshelf_search import bookshelf_search

    # Build embedding query from interests
    query_text = _format_embedding_query(grade_level, interests)

    try:
        embedding = await _embed(query_text)
    except Exception as e:
        logger.warning(f"[Books/GapWeighted] Embedding failed: {e}")
        return []

    # Get adaptive lexile range
    try:
        lexile_min, lexile_max, _ = await _calculate_adaptive_reading_level(student_id, grade_level)
    except Exception:
        lexile_min, lexile_max = _get_lexile_range(grade_level)

    # Fetch more books than needed so we can re-rank
    raw_books = await bookshelf_search.search_books_by_embedding(
        embedding=embedding,
        lexile_min=int(lexile_min),
        lexile_max=int(lexile_max),
        limit=limit * 3,
    )

    if not raw_books:
        return []

    # Build gap-weight map: track → boost multiplier
    # Reverse mapping: bucket → tracks
    from app.api.learning_plan import TRACK_TO_BUCKET
    bucket_to_tracks = {}
    for track, bucket in TRACK_TO_BUCKET.items():
        buckets = bucket if isinstance(bucket, list) else [bucket]
        for b in buckets:
            bucket_to_tracks.setdefault(b, []).append(track)

    gap_boost = {}
    if is_high_school and credit_gaps:
        for gap in credit_gaps:
            if gap.get("remaining", 0) > 0:
                tracks_for_bucket = bucket_to_tracks.get(gap["bucket"], [])
                boost = 1.0 + (gap["remaining"] / 10.0)  # e.g., 3.0 remaining → 1.3x boost
                for t in tracks_for_bucket:
                    gap_boost[t] = max(gap_boost.get(t, 1.0), boost)
    elif weakest_track:
        gap_boost[weakest_track] = 1.3  # 30% boost for weakest track (K-8)

    # Re-rank with gap weighting
    for book in raw_books:
        boost = gap_boost.get(book["track"], 1.0)
        book["relevance_score"] = book.get("relevance_score", 0.0) * boost

    raw_books.sort(key=lambda b: b["relevance_score"], reverse=True)

    # Deduplicate by track — max 2 per track for variety
    final = []
    track_counts = {}
    for book in raw_books:
        tc = track_counts.get(book["track"], 0)
        if tc < 2:
            final.append(book)
            track_counts[book["track"]] = tc + 1
        if len(final) >= limit:
            break

    return final
```

- [ ] **Step 1b: Commit**

```bash
git add adeline-brain/app/api/books.py
git commit -m "feat: Add get_gap_weighted_recommendations() for learning plan"
```

### Step 2: Add `recommended_books` to learning plan response

- [ ] **Step 2a: Add BookRecommendation model to learning_plan.py**

Add after the `ProjectSuggestion` model (after line 96) in `adeline-brain/app/api/learning_plan.py`:

```python
class BookRecommendation(BaseModel):
    id: str
    title: str
    author: str
    track: str
    lexile_level: int
    grade_band: Optional[str] = None
    cover_url: Optional[str] = None
    relevance_score: float = 0.0
```

- [ ] **Step 2b: Add `recommended_books` field to `LearningPlanResponse`**

In `LearningPlanResponse` (around line 122), add after the `projects` field:

```python
    recommended_books: list[BookRecommendation] = []  # Gap-weighted book suggestions
```

- [ ] **Step 2c: Call recommendations in the endpoint**

In `get_learning_plan()`, add after the projects fetch (after line 851) and before the final `return`:

```python
    # 13. Fetch gap-weighted book recommendations
    recommended_books: list[BookRecommendation] = []
    try:
        from app.api.books import get_gap_weighted_recommendations
        gap_dicts = [{"bucket": g.bucket, "remaining": g.remaining} for g in credit_gaps]
        raw_books = await get_gap_weighted_recommendations(
            student_id=student_id,
            grade_level=grade_level,
            interests=interests,
            credit_gaps=gap_dicts,
            weakest_track=weakest_track,
            is_high_school=graduation_progress.is_high_school,
            limit=4,
        )
        recommended_books = [
            BookRecommendation(
                id=b["id"],
                title=b["title"],
                author=b["author"],
                track=b.get("track", ""),
                lexile_level=b.get("lexile_level", 0),
                grade_band=b.get("grade_band"),
                cover_url=b.get("cover_url"),
                relevance_score=b.get("relevance_score", 0.0),
            )
            for b in raw_books
        ]
    except Exception as e:
        logger.warning(f"[LearningPlan] Failed to get book recommendations: {e}")
```

- [ ] **Step 2d: Add `recommended_books` to the return statement**

In the `LearningPlanResponse(...)` constructor at the end of the function, add:

```python
        recommended_books=recommended_books,
```

- [ ] **Step 2e: Commit**

```bash
git add adeline-brain/app/api/learning_plan.py
git commit -m "feat: Add recommended_books to learning plan response"
```

---

## Task 3: Wire Reading Session → Credit Award

**Files:**
- Modify: `adeline-brain/app/api/reading_session.py:228-382` — call `award_reading_credit()` after update

### Step 1: Add credit award trigger to reading session PATCH

- [ ] **Step 1a: Add the credit award call**

In `update_reading_session()` in `reading_session.py`, after the successful update (after line 362, before the `logger.info` on line 364), add:

```python
        # Award reading credit if finished with reflection
        if (
            result["status"] == "finished"
            and result["studentReflection"]
            and result["studentReflection"].strip()
        ):
            try:
                from app.services.reading_credit import award_reading_credit
                # Fetch book metadata for credit calculation
                book_row = await conn.fetchrow(
                    'SELECT title, track, lexile_level FROM "Book" WHERE id = $1',
                    result["bookId"],
                )
                if book_row:
                    # Get student grade level
                    student_row = await conn.fetchrow(
                        'SELECT "gradeLevel" FROM "User" WHERE id = $1',
                        student_id,
                    )
                    grade_level = student_row["gradeLevel"] if student_row else "8"

                    credit_result = await award_reading_credit(
                        session_id=session_id,
                        student_id=student_id,
                        book_id=result["bookId"],
                        book_title=book_row["title"],
                        book_track=book_row["track"] or "ELECTIVES",
                        book_lexile=book_row["lexile_level"] or 0,
                        reading_minutes=result["readingMinutes"] or 0,
                        student_reflection=result["studentReflection"],
                        grade_level=grade_level,
                        completed_at=result["completedAt"],
                    )
                    logger.info(
                        f"[ReadingSession] Credit awarded: {credit_result}"
                    )
            except Exception as e:
                # Don't fail the session update if credit award fails
                logger.error(f"[ReadingSession] Credit award failed: {e}")
```

**Important:** This block must be INSIDE the `async with _get_conn() as conn:` block so the `conn` is available for the book/student queries. The `award_reading_credit` function uses its own connection internally.

- [ ] **Step 1b: Commit**

```bash
git add adeline-brain/app/api/reading_session.py
git commit -m "feat: Award reading credit on book completion with reflection"
```

---

## Task 4: Frontend — Add `RecommendedBooks` Component

**Files:**
- Create: `adeline-ui/src/components/dashboard/RecommendedBooks.tsx`

### Step 1: Create the component

- [ ] **Step 1a: Write RecommendedBooks.tsx**

```tsx
// adeline-ui/src/components/dashboard/RecommendedBooks.tsx
'use client';

import { BookOpen } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface BookRecommendation {
  id: string;
  title: string;
  author: string;
  track: string;
  lexile_level: number;
  grade_band?: string;
  cover_url?: string;
  relevance_score: number;
}

interface RecommendedBooksProps {
  books: BookRecommendation[];
}

export function RecommendedBooks({ books }: RecommendedBooksProps) {
  const router = useRouter();

  if (!books || books.length === 0) return null;

  return (
    <>
      <div className="flex items-center gap-2 mt-8 mb-4">
        <BookOpen className="w-4 h-4 text-[#BD6809]" />
        <p className="text-sm font-bold text-[#2F4731]">
          Recommended Reading
        </p>
        <span className="text-xs text-[#2F4731]/50">
          — Books matched to your learning plan
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {books.map(book => (
          <button
            key={book.id}
            onClick={() => router.push(`/dashboard/reading-nook/${book.id}`)}
            className="text-left p-4 rounded-xl border-2 border-[#E7DAC3] hover:border-[#BD6809] hover:shadow-lg transition-all bg-white group"
          >
            {/* Cover */}
            <div className="w-full aspect-[2/3] rounded-lg mb-3 overflow-hidden bg-[#F5F0E8] flex items-center justify-center">
              {book.cover_url ? (
                <img
                  src={book.cover_url}
                  alt={book.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <BookOpen className="w-8 h-8 text-[#2F4731]/20" />
              )}
            </div>

            {/* Title + Author */}
            <h4 className="text-sm font-bold text-[#2F4731] group-hover:text-[#BD6809] transition-colors line-clamp-2 leading-tight">
              {book.title}
            </h4>
            <p className="text-xs text-[#2F4731]/50 mt-0.5 line-clamp-1">
              {book.author}
            </p>

            {/* Badges */}
            <div className="flex flex-wrap gap-1 mt-2">
              <span className="inline-block px-2 py-0.5 text-[10px] font-bold rounded-full bg-[#2F4731]/10 text-[#2F4731]">
                {book.track.replace(/_/g, ' ')}
              </span>
              <span className="inline-block px-2 py-0.5 text-[10px] rounded-full border border-[#E7DAC3] text-[#2F4731]/50">
                {book.lexile_level}L
              </span>
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
```

- [ ] **Step 1b: Commit**

```bash
git add adeline-ui/src/components/dashboard/RecommendedBooks.tsx
git commit -m "feat: Add RecommendedBooks dashboard component"
```

---

## Task 5: Frontend — Wire Dashboard + Update Types

**Files:**
- Modify: `adeline-ui/src/lib/brain-client.ts:765-775` — add `BookRecommendation` type and `recommended_books` field
- Modify: `adeline-ui/src/app/(routes)/dashboard/page.tsx` — render `RecommendedBooks`

### Step 1: Update brain-client types

- [ ] **Step 1a: Add `BookRecommendation` interface**

In `adeline-ui/src/lib/brain-client.ts`, add after the `ProjectSuggestion` interface (after line 763):

```typescript
export interface BookRecommendation {
  id: string;
  title: string;
  author: string;
  track: string;
  lexile_level: number;
  grade_band?: string;
  cover_url?: string;
  relevance_score: number;
}
```

- [ ] **Step 1b: Add `recommended_books` to `LearningPlanResponse`**

In the `LearningPlanResponse` interface (around line 765), add after `projects`:

```typescript
  recommended_books: BookRecommendation[];
```

### Step 2: Wire into dashboard page

- [ ] **Step 2a: Add import and state**

In `adeline-ui/src/app/(routes)/dashboard/page.tsx`:

Add to the import from `brain-client` (line 12):
```typescript
import type { LessonResponse, Track, LessonSuggestion, ProjectSuggestion, LearningPlanResponse, BookRecommendation } from '@/lib/brain-client';
```

Add import for the component:
```typescript
import { RecommendedBooks } from '@/components/dashboard/RecommendedBooks';
```

Add state variable after the existing state declarations (around line 42):
```typescript
const [recommendedBooks, setRecommendedBooks] = useState<BookRecommendation[]>([]);
```

- [ ] **Step 2b: Set recommended books in fetchSuggestions**

In the `fetchSuggestions` callback, after `setWeeklyCredits(plan.credits_this_week || 0);` (line 58), add:

```typescript
      setRecommendedBooks(plan.recommended_books || []);
```

- [ ] **Step 2c: Render RecommendedBooks between lessons and projects**

In the JSX, after the lessons grid closing `</div>` (after line 232) and before the projects section `{projects.length > 0 && (` (line 235), add:

```tsx
                {/* Recommended Reading */}
                <RecommendedBooks books={recommendedBooks} />
```

- [ ] **Step 2d: Commit**

```bash
git add adeline-ui/src/lib/brain-client.ts adeline-ui/src/app/(routes)/dashboard/page.tsx
git commit -m "feat: Wire recommended books into dashboard learning plan"
```

---

## Task 6: Commit Bug Fixes from Earlier Session

**Files:**
- Modified earlier: `adeline-brain/app/main.py`, `adeline-brain/app/api/books.py`, `adeline-brain/app/api/registrar_reports.py`, `adeline-brain/prisma/schema.prisma`

### Step 1: Stage and commit all bug fixes

- [ ] **Step 1a: Commit the remaining bug fixes**

```bash
git add adeline-brain/app/main.py adeline-brain/app/api/books.py adeline-brain/app/api/registrar_reports.py adeline-brain/prisma/schema.prisma adeline-brain/prisma/migrations/20260409_add_reading_recommendations_log/
git commit -m "fix: Restore bookshelf router, add Prisma relations, fix SQL param and missing UUID"
```

---

## Task 7: Final Integration Test

### Step 1: Verify the full flow locally

- [ ] **Step 1a: Run all backend tests**

```bash
cd adeline-brain && python -m pytest tests/ -v --tb=short
```

- [ ] **Step 1b: Verify learning plan returns recommended_books**

```bash
cd adeline-brain && python -c "
import asyncio, json
from app.api.learning_plan import get_learning_plan

async def test():
    # This will fail without a running DB, but verifies imports work
    try:
        from app.services.reading_credit import calculate_reading_credit, TRACK_TO_GRADUATION_BUCKET
        print('reading_credit imports OK')
        print(f'Credit for 10h at grade level: {calculate_reading_credit(600, 800, \"8\"):.4f}')
        print(f'Buckets: {list(TRACK_TO_GRADUATION_BUCKET.keys())}')
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(test())
"
```

- [ ] **Step 1c: Verify frontend builds**

```bash
cd adeline-ui && npx next build 2>&1 | tail -20
```

- [ ] **Step 1d: Commit any fixes needed**

If build errors surface, fix and commit.
