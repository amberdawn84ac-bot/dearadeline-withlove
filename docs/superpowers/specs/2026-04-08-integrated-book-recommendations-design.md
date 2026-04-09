# Integrated Book Recommendations + Reading-to-Credit Pipeline

**Date:** 2026-04-08
**Status:** Approved

## Problem

The learning plan suggests lessons but never books. The reading nook is a separate page with no connection to the learning plan. Finishing a book doesn't earn credits. K-8 students have no reading standards tracking. The result: reading feels disconnected from the student's academic progress.

## Solution

Three changes:
1. Learning plan endpoint returns 3-4 recommended books inline, weighted by credit gaps
2. Dashboard shows a "Recommended Reading" section alongside lesson suggestions
3. Finishing a book + writing a reflection automatically earns credits and maps to standards

## 1. Learning Plan — "Recommended Reading" Section

### Backend

`GET /learning-plan/{student_id}` gains a new response field:

```
recommended_books: BookRecommendation[] (3-4 items)
```

Each `BookRecommendation` contains: `id`, `title`, `author`, `track`, `lexile_level`, `grade_band`, `cover_url`, `relevance_score`.

**Recommendation algorithm:**

1. Calculate adaptive lexile range from reading history (existing `_calculate_adaptive_reading_level` logic in `books.py`), falling back to grade-level defaults
2. Query pgvector for books matching student interests + lexile range (existing `bookshelf_search.search_books_by_embedding`)
3. Apply credit-gap weighting:
   - For 9-12 students: boost books whose track maps to the largest credit gap bucket
   - For K-8 students: boost books whose track matches the weakest mastery track
4. Return top 3-4 results

The weighting is a score multiplier, not a hard filter. A student interested in science will still see science books even if their ENGLISH_CORE gap is larger — but English books get a boost.

**New function in `books.py`:**

```python
async def get_gap_weighted_recommendations(
    student_id: str,
    grade_level: str,
    interests: list[str],
    credit_gaps: list[dict],  # [{bucket, gap}]
    weakest_track: str | None,
    limit: int = 4,
) -> list[dict]:
```

This function is called internally by `learning_plan.py` — not exposed as a separate endpoint.

### Frontend

Dashboard `page.tsx` renders a new section between lesson suggestions and portfolio projects:

```
┌─────────────────────────────────────────────────┐
│  📚 Recommended Reading                         │
│                                                   │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐        │
│  │cover │  │cover │  │cover │  │cover │        │
│  │      │  │      │  │      │  │      │        │
│  ├──────┤  ├──────┤  ├──────┤  ├──────┤        │
│  │Title │  │Title │  │Title │  │Title │        │
│  │Author│  │Author│  │Author│  │Author│        │
│  │ 800L │  │ 650L │  │ 900L │  │ 750L │        │
│  │TRACK │  │TRACK │  │TRACK │  │TRACK │        │
│  └──────┘  └──────┘  └──────┘  └──────┘        │
└─────────────────────────────────────────────────┘
```

Each card shows: cover image (or placeholder), title, author, lexile level, track badge. Clicking navigates to `/dashboard/reading-nook/{bookId}`.

**New component:** `adeline-ui/src/components/dashboard/RecommendedBooks.tsx`

## 2. Reading-to-Credit Pipeline

### Trigger

When `PATCH /api/reading-session/{id}` receives `status: "finished"` AND `student_reflection` is non-empty (not null, not whitespace), call `award_reading_credit()`.

If the student marks the book finished without a reflection, the session is saved but no credit is awarded. The UI should prompt: "Write a reflection to earn credit for this book."

If the student later adds a reflection via another PATCH, credit is awarded at that point (idempotent — check if credit was already awarded for this session).

### Credit Calculation (9-12)

```
base = reading_minutes / 120    # 2 hours reading = 1.0 base
lexile_multiplier =
    1.2 if book.lexile_level > grade_max
    1.0 if grade_min <= book.lexile_level <= grade_max
    0.8 if book.lexile_level < grade_min
credit = min(base * lexile_multiplier, 0.5)   # cap at 0.5 per book
```

Where `grade_min` and `grade_max` come from the existing `GRADE_TO_LEXILE` mapping.

### Track-to-Bucket Mapping

| Book Track | Graduation Bucket |
|---|---|
| ENGLISH_LITERATURE | ENGLISH_CORE |
| TRUTH_HISTORY | SOCIAL_STUDIES |
| JUSTICE_CHANGEMAKING | SOCIAL_STUDIES |
| GOVERNMENT_ECONOMICS | SOCIAL_STUDIES |
| CREATION_SCIENCE | SCIENCE_CORE |
| HOMESTEADING | SCIENCE_CORE |
| HEALTH_NATUROPATHY | SCIENCE_CORE |
| APPLIED_MATHEMATICS | MATH_CORE |
| DISCIPLESHIP | ELECTIVES |
| CREATIVE_ECONOMY | FINE_ARTS |

### Ledger Writes

`award_reading_credit()` performs three writes in a single function:

**1. EvidenceLedgerEntry:**
- `artifactType`: `"reading"`
- `title`: book title
- `masteryScore`: lexile-relative score (0.0-1.0 based on how book lexile compares to grade level)
- `hours`: `reading_minutes / 60`
- `activityDate`: reading session `completedAt`
- `evaluatorNotes`: student reflection text
- `bucket`: mapped from track (table above)
- `proposedCourse`: book title + author
- `isApproved`: `true` (auto-approved — reflection is the evidence)

**2. CreditLedgerEntry:**
- `bucket`: same mapping
- `hoursEarned`: calculated credit value (formula above)
- `source`: `"reading"`
- `sourceId`: reading session ID

**3. StandardsLedgerEntry (K-8 only):**
- `framework`: `"READING"`
- `subject`: mapped from book track
- `code`: grade-appropriate reading standard (e.g., `"RI.5.2"` for informational text, `"RL.5.2"` for literature)
- `confidence`: lexile-relative score (same as masteryScore)
- `lessonId`: reading session ID (repurposing field as source reference)

### K-8 Standards Mapping

Books map to reading standards based on grade level and book type:

- ENGLISH_LITERATURE, DISCIPLESHIP → `RL.{grade}.{standard}` (Reading Literature)
- All other tracks → `RI.{grade}.{standard}` (Reading Informational)

Standards selected:
- `.2` — Determine central idea/theme (always applicable to completed book)
- `.10` — Read and comprehend grade-level text (applicable based on lexile match)

This is intentionally conservative — 1-2 standards per book rather than overclaiming.

### Idempotency

To prevent double-awarding, `award_reading_credit()` checks:

```sql
SELECT COUNT(*) FROM "CreditLedgerEntry"
WHERE "sourceId" = $1 AND source = 'reading'
```

If count > 0, skip all writes and return early.

## 3. Files Changed

### Backend — Modified

| File | Change |
|---|---|
| `app/api/learning_plan.py` | Add `recommended_books` to response; call `get_gap_weighted_recommendations()` |
| `app/api/reading_session.py` | Call `award_reading_credit()` on finish + reflection |
| `app/api/books.py` | Extract and expose `get_gap_weighted_recommendations()` function |

### Backend — New

| File | Purpose |
|---|---|
| `app/services/reading_credit.py` | `award_reading_credit()` — all three ledger writes + idempotency check |

### Frontend — Modified

| File | Change |
|---|---|
| `adeline-ui/src/app/(routes)/dashboard/page.tsx` | Render `RecommendedBooks` section from learning plan data |
| `adeline-ui/src/lib/brain-client.ts` | Update `LearningPlanResponse` type to include `recommended_books` |

### Frontend — New

| File | Purpose |
|---|---|
| `adeline-ui/src/components/dashboard/RecommendedBooks.tsx` | Book card grid component (cover, title, author, lexile, track badge) |

### Schema

No new tables. Uses existing `EvidenceLedgerEntry`, `CreditLedgerEntry`, `StandardsLedgerEntry`.

## 4. What This Does NOT Include

- No changes to the EPUB reader itself
- No changes to the reflection modal (it already collects text)
- No new API endpoints (learning plan and reading session endpoints are modified, not added)
- No changes to the bookshelf browsing page (reading nook remains as-is for independent browsing)
- No parent approval flow (reflection = auto-approved evidence per portfolio philosophy)
