# Registrar Agent — Design Spec
**Date:** 2026-03-28
**Project:** Dear Adeline 2.0
**Status:** Approved — ready for implementation

---

## Overview

The Registrar Agent transforms a student's sealed lesson record into a credentialing-grade transcript that satisfies two audiences simultaneously:

1. **Homeschool state filing** — Oklahoma clock hours, OAS standard coverage, academic year scoping
2. **College admissions** — Carnegie units, letter grades, traditional course equivalents

The system already has the raw data (sealed lessons in Postgres, mastered OAS standards in Neo4j, evidence sources in journal store). The Registrar Agent is the intelligence layer that turns that raw data into a structured `TranscriptRecord`, which is then either returned as JSON or rendered as a PDF.

---

## Architecture

### New / changed files

```
adeline-brain/
  app/
    agents/
      registrar.py              ← NEW — RegistrarAgent + TranscriptRecord data model
    api/
      transcripts.py            ← UPDATED — calls agent, adds JSON preview endpoint, adds academic_year param
  scripts/
    seed_hidden_subjects.py     ← NEW — seeds Math/PE/Fine Arts/Geography/Tech OAS standards with APPLIED_IN edges

adeline-ui/
  src/app/(routes)/dashboard/
    transcript/
      page.tsx                  ← NEW — year picker + stats preview + PDF download button
```

### Design principle

`registrar.py` owns all business logic. `transcripts.py` is a thin routing layer. The PDF builder is a pure renderer — it receives a `TranscriptRecord` and produces bytes, with no credit math or data fetching of its own.

---

## Data Model

### `TrackCredit`

```python
class TrackCredit(BaseModel):
    track_id:           str          # "TRUTH_HISTORY"
    track_label:        str          # "Track 7 — Truth-Based History"
    traditional_equiv:  str          # "American History / World History"
    mastery_band:       MasteryBand  # NOVICE / DEVELOPING / PROFICIENT / ADVANCED
    letter_grade:       str          # "A", "B", "C", or "Pass"
    lessons_sealed:     int
    verified_blocks:    int          # SUM(completed_blocks) for this track in the year
    clock_hours:        float        # verified_blocks × 30 min ÷ 60
    carnegie_units:     float        # clock_hours ÷ 120
    covered_subjects:   list[str]    # ["Mathematics — Geometry", "Technical Writing"]
    top_sources:        list[str]    # up to 3 primary source titles
```

### `TranscriptRecord`

```python
class TranscriptRecord(BaseModel):
    student_id:              str
    student_name:            str          # "Student [id]" until auth; replaced by real name post-auth
    academic_year:           str          # "2025-2026"
    generated_at:            str          # ISO datetime
    tracks:                  list[TrackCredit]
    total_clock_hours:       float
    total_carnegie_units:    float
    traditional_subjects:    list[dict]   # {subject, standards: list[str], clock_hours, grade}
    mastered_standards:      list[dict]   # {standard_id, text, grade, track}
    evidence_sources:        list[dict]   # {title, author, year, url, track}
    witness_threshold:       float        # 0.82
```

### Traditional course equivalents (all 8 Tracks)

| Track | Traditional Equivalent |
|---|---|
| CREATION_SCIENCE | Biology / Earth Science |
| HEALTH_NATUROPATHY | Health Science |
| HOMESTEADING | Agricultural Science & Technology |
| GOVERNMENT_ECONOMICS | Government & Economics |
| JUSTICE_CHANGEMAKING | Social Studies / Civics |
| DISCIPLESHIP | Philosophy & Ethics |
| TRUTH_HISTORY | American History / World History |
| ENGLISH_LITERATURE | English Language Arts |

### Grade mapping

| MasteryBand | Letter Grade |
|---|---|
| ADVANCED | A |
| PROFICIENT | B |
| DEVELOPING | C |
| NOVICE | Pass |

---

## Credit Calculation

**Clock hours:**
`completed_blocks` is stored per sealed lesson in `student_journal.completed_blocks`.
The agent runs: `SELECT track, SUM(completed_blocks) FROM student_journal WHERE student_id = ? AND sealed_at BETWEEN ? AND ? GROUP BY track`
Clock hours per track = `SUM(completed_blocks) × 30 ÷ 60`

**Carnegie units:**
`carnegie_units = clock_hours ÷ 120`
(1 Carnegie unit = 120 clock hours = 1 full-year course)

**Academic year date range:**
"2025-2026" → Aug 1, 2025 00:00 UTC through Jul 31, 2026 23:59 UTC

---

## Hidden Subject Detection

Traditional subjects (Math, PE, Fine Arts, Geography, Technology/Coding) are not separate tracks — they are covered implicitly through the 8-Track work. The graph makes this explicit via a new relationship type:

```cypher
(OASStandard)-[:APPLIED_IN]->(Track)
```

Examples:
- `(OAS.MATH.4.G.1 "Classify shapes by properties")` -[:APPLIED_IN]-> `(HOMESTEADING)`
- `(OAS.MATH.8.EE.7 "Solve linear equations")` -[:APPLIED_IN]-> `(GOVERNMENT_ECONOMICS)`
- `(OAS.PE.8.FM.1 "Demonstrate outdoor physical fitness")` -[:APPLIED_IN]-> `(HOMESTEADING)`
- `(OAS.FA.8.VA.1 "Analyze visual art in historical context")` -[:APPLIED_IN]-> `(DISCIPLESHIP)`
- `(OAS.GEO.8.WG.1 "Interpret historical maps")` -[:APPLIED_IN]-> `(TRUTH_HISTORY)`
- `(OAS.CS.8.DA.1 "Use digital tools for communication")` -[:APPLIED_IN]-> `(JUSTICE_CHANGEMAKING)`

**Registrar Agent query for hidden subjects:**

```cypher
MATCH (st:Student {id: $student_id})-[:MASTERED]->(s:OASStandard)
MATCH (s)-[:APPLIED_IN]->(t:Track)
WHERE t.name IN $active_tracks
RETURN s.id AS standard_id, s.standard_text AS text,
       s.subject AS subject, t.name AS track
ORDER BY s.subject, s.grade
```

The agent groups results by `subject` to produce the `traditional_subjects` list.

**`seed_hidden_subjects.py`** seeds ~30 OAS standards across 5 hidden subject areas with `APPLIED_IN` edges:

| Hidden Subject | Host Tracks | Standards to Seed |
|---|---|---|
| Mathematics | HOMESTEADING, GOVERNMENT_ECONOMICS | 8 (Grades 4, 6, 8: geometry, ratios, algebra, financial math) |
| Physical Education | HOMESTEADING, HEALTH_NATUROPATHY | 4 (Grades 4, 8: outdoor fitness, labor, nutrition activity) |
| Fine Arts | ENGLISH_LITERATURE, DISCIPLESHIP | 6 (Grades 4, 8: hymn analysis, architecture, illuminated texts) |
| Geography | TRUTH_HISTORY, CREATION_SCIENCE | 6 (Grades 4, 8: historical maps, topography, regional ecology) |
| Technology / Coding | JUSTICE_CHANGEMAKING | 4 (Grades 6, 8: digital literacy, logic, communication tools) |

**Font dependency:** `adeline-brain/assets/fonts/` must contain `PlayfairDisplay-Bold.ttf`, `Lora-Regular.ttf`, and `Lora-Italic.ttf` before the PDF builder runs. The implementation step includes downloading these OFL-licensed fonts.

---

## API Endpoints

### Existing (updated)
```
GET /transcripts/generate/{student_id}?academic_year=2025-2026
```
- Calls `RegistrarAgent.build(student_id, academic_year)`
- Passes `TranscriptRecord` to PDF builder
- Returns streaming PDF
- `academic_year` is required; returns HTTP 422 if missing

### New
```
GET /transcripts/preview/{student_id}?academic_year=2025-2026
```
- Calls `RegistrarAgent.build(student_id, academic_year)`
- Returns `TranscriptRecord` as JSON
- Used by the UI to populate the preview page
- `academic_year` is required

---

## PDF Design

The transcript must not look like a generic ReportLab document. It should feel continuous with the Adeline UI — parchment, ink, Papaya/Paradise/Fuschia brand colors.

**Typography:**
- Embed the Playfair Display TTF (or EB Garamond) for headings — classical, authoritative, distinctive
- Body text: Lora or Crimson Text — readable serif that reads as "scholarly" not "generated"
- Monospace accents (standard IDs, scores): Courier New
- All font files stored in `adeline-brain/assets/fonts/` and registered with ReportLab at build time

**Color palette (from adeline-core):**
- INK: `#2C2318` — all body text
- PARADISE: `#9A3F4A` — section headers, table header backgrounds
- PAPAYA: `#BD6809` — accent lines, the Registrar's Seal label, Carnegie unit figures
- FUSCHIA: `#3D1419` — track names (bold)
- PARCHMENT: `#FDF8F0` — page background tint (set via canvas background rect)
- PARCHMENT_DARK: `#F0D9B0` — alternating table rows, rule lines

**Layout — Page 1 (8-Track Transcript):**
- Full-width parchment background rect behind all content
- Header block: centered institution name in large Playfair Display caps, ruled above and below with a double PARADISE line
- Left column metadata (student, year, generated date) in small Lora italic
- Right column: a small Adeline wordmark / seal image placeholder (replaced with real asset when available)
- Track summary table: PARADISE header row, alternating PARCHMENT/white rows, PAPAYA right-align for clock hours and units, FUSCHIA bold for track names, traditional equivalent in smaller italic below each track name
- OAS Standards section: grouped by track under PARADISE subheaders, italic standard text with Courier New standard ID prefix
- Footer: thin PAPAYA rule + Witness Protocol seal text in small Lora italic

**Layout — Page 2 (Traditional Subject Grid):**
- Same parchment background and header treatment
- Explanatory paragraph in Lora
- Traditional subject table: one row per subject, PARADISE subject name bold, OAS IDs in Courier New, grade in PAPAYA
- Evidence Appendix: numbered list, each source as a small "citation card" — title bold, author/year italic, archive name small, truth score in Courier New green (`#2E7D32`)

**Page size:** US Letter (8.5 × 11 in), margins 1.1 in all sides

**Page numbering:** "Page 1 of 2" / "Page 2 of 2" in small Courier New bottom-right

---

## UI Page: `/dashboard/transcript`

**Components (stacked):**

1. **Year selector** — dropdown derived from `sealed_at` dates in the student's journal. Selecting a year calls `GET /brain/transcripts/preview/{student_id}?academic_year=...` and updates the preview.

2. **Stats row** — four cards:
   - Total Clock Hours
   - Carnegie Units
   - Tracks Completed
   - Primary Sources Cited

3. **Track table** — one row per active track:
   ```
   Track 7 — Truth-Based History          A    12.5 hrs    0.1 units
   (American History / World History)
   Douglass · Bradford · Madison's Notes
   ```

4. **Traditional Subjects Covered** — collapsed section listing hidden subjects with OAS standard IDs.

5. **Download PDF button** — triggers `GET /brain/transcripts/generate/{student_id}?academic_year=...`

---

## Error Handling

| Condition | Behavior |
|---|---|
| No sealed lessons in requested year | HTTP 404 with message "No sealed lessons found for 2025-2026" |
| Neo4j unavailable | Agent proceeds with empty `mastered_standards` and `traditional_subjects`; logs warning |
| PDF build fails | HTTP 500; JSON preview endpoint still works |
| `academic_year` missing | HTTP 422 |

---

## Out of Scope

- xAPI statement generation (Phase 3)
- Supabase auth / real student names (Phase 2 — Auth)
- GPA calculation across multiple years (requires multi-year transcript view)
- Transcript signing / digital seal (future)
