# Bookshelf v1 Design Specification

> **Status:** Approved
> **Date:** 2026-04-04
> **Scope:** Text-based discovery, EPUB reader, progress tracking. Reading coach (comprehension Q&A, word accuracy tracking, voice) deferred to v2.

---

## Overview

Adeline's Bookshelf is a curated + AI-recommended digital library that grows nightly via automated seed scripts. Students browse books by reading level and interests, read EPUB files in an embedded reader, track progress, and optionally reflect on completed books. Discovery is powered by pgvector semantic search on student profile (reading level + interests) matched against indexed book descriptions and assigned curriculum tracks.

**Goal:** Give students access to thousands of public-domain books, personalized to their reading level and learning interests, with progress tracking that feeds into future reading coach and transcript credit systems.

---

## Architecture

### Three Layers

**1. Discovery Engine (Backend)**
- pgvector semantic search on book descriptions
- Ranks by: cosine similarity to student profile (reading level + interests) + book reading level
- Returns top 12 recommendations per query
- Filters: track, lexile_min, lexile_max, status (all/reading/finished/wishlist)

**2. Reader (Frontend)**
- EPUB.js embedded reader with standard controls (prev/next chapter, TOC, bookmarks)
- Progress auto-saved every 5 minutes or on chapter change
- Sidebar shows: current progress %, book metadata, reading time, track badge
- Reflection modal on completion (optional text input)

**3. Shelf (Frontend)**
- Four visual shelf sections: "Currently Reading," "Finished," "Want to Read," "Discover"
- Book cards show: title, author, track badge, reading level badge, progress bar (if reading)
- Drag-and-drop move books between shelves (or status buttons)
- Search/filter by title, author, track

---

## Data Model

### `books` Table

```sql
CREATE TABLE books (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  source_url TEXT NOT NULL, -- Direct link to EPUB file
  cover_url TEXT, -- Optional cover image URL
  lexile_level INTEGER, -- e.g., 600L, 800L
  grade_band TEXT, -- e.g., "3-4", "5-6", "7-8", "9-10", "11-12"
  description TEXT,
  track TEXT NOT NULL, -- CREATION_SCIENCE, TRUTH_HISTORY, ENGLISH_LITERATURE, etc.
  source_library TEXT, -- "Standard Ebooks", "Project Gutenberg"
  embedding vector(1536), -- OpenAI embedding of title + author + description
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),

  INDEX ON track,
  INDEX ON lexile_level,
  INDEX ON source_library
);
```

### `reading_session` Table

```sql
CREATE TABLE reading_session (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL REFERENCES "User"(id),
  book_id UUID NOT NULL REFERENCES books(id),
  status TEXT NOT NULL, -- 'reading', 'finished', 'wishlist'
  started_at TIMESTAMP DEFAULT now(),
  completed_at TIMESTAMP,
  pages_read INTEGER DEFAULT 0,
  total_pages INTEGER,
  current_location TEXT, -- EPUB CFI (Canonical Fragment Identifier) for resume point
  student_reflection TEXT, -- Optional note/rating from student
  reading_minutes INTEGER DEFAULT 0, -- Total time spent reading
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),

  UNIQUE(student_id, book_id), -- Prevent duplicate sessions
  INDEX ON student_id,
  INDEX ON book_id,
  INDEX ON status
);
```

---

## Backend Endpoints

All endpoints require `Authorization: Bearer {user_id}` header.

### Book Discovery

**GET `/api/books`** — List books with filters

Query params:
- `track` (optional): Filter by curriculum track
- `lexile_min`, `lexile_max` (optional): Filter by reading level range
- `source_library` (optional): "Standard Ebooks" | "Project Gutenberg"
- `limit` (default 50): Pagination limit
- `offset` (default 0): Pagination offset

Response:
```json
{
  "books": [
    {
      "id": "uuid",
      "title": "The Wonderful Wizard of Oz",
      "author": "L. Frank Baum",
      "lexile_level": 740,
      "grade_band": "3-5",
      "track": "ENGLISH_LITERATURE",
      "cover_url": "...",
      "source_library": "Standard Ebooks"
    }
  ],
  "total": 1250
}
```

**GET `/api/books/recommendations`** — AI-recommended books for student

Uses student profile (reading level + interests from onboarding) to search pgvector. Returns top 12 books ranked by relevance.

Query params:
- `limit` (default 12): Number of recommendations

Response:
```json
{
  "recommendations": [
    {
      "id": "uuid",
      "title": "...",
      "author": "...",
      "lexile_level": 650,
      "grade_band": "4-6",
      "track": "CREATION_SCIENCE",
      "cover_url": "...",
      "relevance_score": 0.92
    }
  ]
}
```

**GET `/api/books/{bookId}`** — Full book metadata + EPUB download URL

Response:
```json
{
  "id": "uuid",
  "title": "...",
  "author": "...",
  "description": "...",
  "lexile_level": 740,
  "grade_band": "3-5",
  "track": "ENGLISH_LITERATURE",
  "cover_url": "...",
  "source_url": "https://standardebooks.org/files/...",
  "source_library": "Standard Ebooks",
  "total_pages": 320
}
```

### Reading Sessions (Shelf & Progress)

**POST `/api/reading-session`** — Start reading a book

Body:
```json
{
  "book_id": "uuid",
  "status": "reading" // or "wishlist" to add to wishlist
}
```

Response: 201 Created
```json
{
  "id": "uuid",
  "student_id": "uuid",
  "book_id": "uuid",
  "status": "reading",
  "started_at": "2026-04-04T10:30:00Z",
  "current_location": ""
}
```

**PATCH `/api/reading-session/{sessionId}`** — Update progress or mark complete

Body (any combination):
```json
{
  "status": "finished",
  "current_location": "epubcfi(/6/4[chap01]!/4/2/16,/1:0,/1:100)",
  "pages_read": 120,
  "reading_minutes": 45,
  "student_reflection": "I loved how the main character overcame her fears!"
}
```

Response: 200 OK with updated session object.

**GET `/api/reading-session`** — Get student's shelf (all sessions)

Query params:
- `status` (optional): "reading" | "finished" | "wishlist" | "all" (default)

Response:
```json
{
  "reading": [
    {
      "id": "uuid",
      "book_id": "uuid",
      "book": {
        "title": "...",
        "author": "...",
        "lexile_level": 740,
        "track": "ENGLISH_LITERATURE",
        "cover_url": "..."
      },
      "started_at": "2026-04-01T08:00:00Z",
      "pages_read": 50,
      "total_pages": 320,
      "current_location": "epubcfi(...)",
      "reading_minutes": 120
    }
  ],
  "finished": [
    {
      "id": "uuid",
      "book_id": "uuid",
      "book": { ... },
      "completed_at": "2026-04-03T15:30:00Z",
      "student_reflection": "Loved it!",
      "total_pages": 280,
      "reading_minutes": 340
    }
  ],
  "wishlist": [ ... ]
}
```

---

## Frontend Structure

### Pages

**`/reading-nook`** — Main bookshelf dashboard
- Four shelf sections (Reading / Finished / Wishlist / Discover)
- Search & filter bar (by title, author, track, reading level)
- Book cards in a responsive grid (4 cols on desktop, 2 on tablet, 1 on mobile)
- Each card shows: title, author, track badge, reading level, progress bar (if reading)
- Click card to open reader

**`/reading-nook/[bookId]`** — EPUB reader view
- EPUB.js viewer (left ~80% of screen)
- Sidebar (right ~20%): book info, TOC, bookmarks, progress
- Controls: previous/next chapter, full TOC modal, bookmark toggle
- Auto-saves progress every 5 minutes
- "Finish Reading" button at end of book → triggers reflection modal

**`/reading-nook/discover`** (optional separate page)
- Shows AI recommendations in a larger grid
- "Add to Reading List" button per book

### Components

**`BookCard.tsx`**
- Displays: title, author, track badge (colored), reading level badge, cover image (if available)
- Shows progress bar if status is "reading" (pages_read / total_pages)
- Hover: slightly enlarges, shows "Open Reader" button
- Props: `book`, `session` (optional, if reading), `onClick: (bookId) => void`

**`Bookshelf.tsx`**
- Contains four `ShelfSection` components (Reading, Finished, Wishlist, Discover)
- Each section renders grid of `BookCard`s
- Handles drag-and-drop (or simple status buttons: Move to Finished, Add to Wishlist, etc.)
- Props: `sessions` (all reading_session records for student), `recommendations` (top 12 books)

**`EPUBReader.tsx`**
- Wraps EPUB.js viewer
- Sidebar with: book title, author, track badge, progress %, reading time, TOC button, bookmark toggle
- Controls: prev/next chapter, progress slider (seek to location), close button
- Auto-saves on chapter change or every 5 minutes
- On last page, shows "Finish Reading" button → `onComplete` callback

**`ReflectionModal.tsx`**
- Text input for optional reflection ("What was your favorite part?", "Rate this book")
- "Save & Close" button → calls PATCH `/api/reading-session` with reflection + status="finished"
- "Skip" button → marks finished without reflection
- On success, redirects back to `/reading-nook`

---

## Nightly Seed Script

**`scripts/seed_bookshelf.py`**

Logic:
1. Query Standard Ebooks API: fetch new books added in last 24h
2. Query Project Gutenberg API: fetch popular public domain books (limit to 100/run to avoid API limits)
3. For each book:
   - Extract title, author, description, cover URL
   - Determine reading level:
     - If Lexile available from source, use it
     - Otherwise, estimate via word count + average word length heuristic
     - Grade band: convert Lexile to grade band (e.g., 600-750L = "3-5")
   - Call Claude: "Analyze this book description and assign the most relevant curriculum track from our 10-track system. Only pick one. Return JSON: {track: 'TRACK_NAME'}"
   - Generate embedding: call OpenAI embedding API on `title + ' ' + author + ' ' + description`
   - INSERT or UPDATE book in Postgres (upsert on source_url to avoid duplicates)
4. Log: X new books added, Y updated, Z skipped (duplicates)

**Frequency:** Nightly at 02:00 UTC (off-peak)

**Error handling:**
- If API rate limit hit, skip remaining books and log warning
- If embedding fails, skip book (log error)
- If Claude fails, default to ENGLISH_LITERATURE track + log warning

---

## Student Workflow

1. **Login** → `/dashboard` → Click "Reading Nook" in nav
2. **Discover** → Browse "Discover" shelf (AI recommendations based on profile)
3. **Add to Reading List** → Click book card → "Add to Reading List" button → book appears in "Want to Read" shelf
4. **Start Reading** → Click book from "Want to Read" → "Start Reading" button → POST `/api/reading-session` → reader opens
5. **Read** → EPUB.js renders book → student can navigate chapters, use TOC
6. **Progress auto-saves** → every 5 minutes and on chapter change
7. **Finish** → Reach end of book → "Mark as Complete" button → optional reflection modal
8. **Reflection** (optional) → Write "What did you think?" → PATCH session with reflection + status="finished"
9. **Shelf updated** → Book moves from "Currently Reading" → "Finished"
10. **Next visit** → Recommendations refresh based on completed books

---

## Integration with Future Features

### Reading Coach v2 (Text-based comprehension)
- Comprehension Q&A pauses at chapter breaks
- Student attempts to answer, coach gives hints/scaffolds
- Accuracy scores feed into `reading_session.comprehension_score`

### Reading Coach v3 (Voice)
- Web Speech API or enterprise ASR captures student reading aloud
- Word-level accuracy (WCPM, phoneme analysis) logged to `reading_word` table
- Accent/dialect support via fine-tuned ASR model

### Transcript Credit System
- When `reading_session.status = 'finished'`, RegistrarAgent checks:
  - Did student read for 20+ minutes?
  - If v2 launches: did comprehension score ≥ 80%?
- If yes, emit xAPI statement + CASE credit: +0.125 ELA credit per book (4 books = 0.5 credit)

### Parent Dashboard v2
- Parent sees "Reading Progress" widget: books completed this month, average reading time, trends
- Notifications: "Student finished a book — see reflection"

---

## Error Handling

| Scenario | Response |
|----------|----------|
| Book not found (404) | `{ "error": "Book no longer available", "code": "BOOK_NOT_FOUND" }` |
| EPUB file returns 404 | Show error in reader: "Unable to load this book. Please try again later." + Back button |
| Duplicate session attempt | Existing session returned (409 Conflict) with `session_id` |
| Student offline while reading | Save progress to IndexedDB, sync on reconnect via PATCH |
| Reflection modal submitted while offline | Persist locally, sync on reconnect |
| pgvector search timeout | Return generic top 12 books (non-personalized fallback) |

---

## Testing Strategy

### Unit Tests
- **Seed script:**
  - Mock Standard Ebooks API, verify book extraction
  - Mock Claude track assignment, verify valid track returned
  - Mock OpenAI embedding, verify embedding shape (1536)
  - Verify duplicate detection (same source_url)

- **Lexile estimation heuristic:**
  - Test word count → grade band mapping (e.g., 10k words → grade 2-3)

- **pgvector ranking:**
  - Student with interests ["Science", "Animals"] should rank biology/nature books higher than history books
  - Student with reading level 700L should rank books 650-750L highest

### Integration Tests
- Full workflow: POST reading-session → GET EPUB file → PATCH progress → PATCH complete with reflection → verify session marked finished
- Shelf view: POST 3 sessions (reading/finished/wishlist) → GET `/api/reading-session` → verify correct grouping
- Recommendations: Student with profile (grade 5, interests ["Science", "Animals"]) → GET recommendations → verify top 3 are science/nature + grade 4-6

### Manual E2E
- Login as student → navigate to Reading Nook → search for book by title → click result → reader opens → read a chapter → close reader → verify progress saved → open same book → verify resume at saved location → mark complete → write reflection → verify book moves to "Finished" shelf

---

## Success Criteria

✅ Students can browse 1000+ books by reading level, track, and interests
✅ AI recommendations are relevant (top 3 matches student profile)
✅ EPUB reader opens, renders books correctly, and handles navigation
✅ Reading progress persists across sessions (resume at correct page)
✅ Optional reflection captures student voice
✅ Nightly seed adds new books daily without duplicating
✅ Shelf views show books in correct status (Reading / Finished / Wishlist)
✅ All endpoints return 401 if Authorization header missing
✅ Reader gracefully handles EPUB file 404s
✅ Full E2E workflow (discover → read → reflect → shelf update) works end-to-end

---

## Known Gaps & Deferred to v2

- Reading coach (comprehension Q&A, word accuracy tracking)
- Voice support (Web Speech API)
- Parent uploads (books only from automated seed)
- Advanced analytics (reading time trends, difficulty progression)
- Bookmarks/notes within reader
- Sharing/discussion features
