# Adelinemobile ↔ Adeline Brain Integration Design

**Date:** 2026-07-31
**Repos:** `vinnymacndelilah/Adelinemobile` (game client) · `amberdawn84ac-bot/dearadeline_withlove` (brain + web)
**Status:** Approved for implementation planning

---

## Vision

Adelinemobile is the fun front door kids open every day. The `adeline-brain` FastAPI service (Railway) is the high-value asset — Witness Protocol, ZPD engine, multi-agent orchestration, xAPI/CASE records. This integration wires them together so a mission completed in Math Mines or Truth Archive produces a real, verified portfolio entry and transcript credit — not just game XP.

Two AI paths coexist deliberately:
- **Raw Gemini** — world chat, speech bubbles, quest hooks, activity detection
- **Brain endpoints** — room missions, lesson generation, credit recording, mastery tracking

---

## Section 1: Identity Bridge

### Single Supabase Project
Both apps share the same Supabase project (`gyxowttfwqbajoapfebf`). One auth system, one JWT, one source of truth.

### Student ID
`aw_student_profiles.id` (uuid) is the canonical `student_id` used in all brain API calls. No mapping layer needed.

### JWT Flow
Every brain call from Adelinemobile carries:
```
Authorization: Bearer <supabase_access_token>
```
The brain's `middleware.py` already validates Supabase JWTs. The Express `server.ts` in Adelinemobile acts as a proxy at `/api/brain/*` — it receives the JWT from the client and forwards it, optionally adding the Railway internal secret for service-to-service auth.

### Field Alignment
| Adelinemobile field | Brain field |
|---|---|
| `aw_student_profiles.id` | `student_id` |
| `aw_student_profiles.grade_level` | `grade_level` in `LessonRequest` |
| `aw_student_profiles.age` | inferred via `gradeBandFromAge()` |
| always `true` | `is_homestead` (this family homesteads) |

### Brain Registration on Child Create
When a child profile is created in Adelinemobile (`addChild()` in `AuthContext.tsx`), a one-time call registers them in the brain:

```
POST {BRAIN_URL}/students/register
Body: {
  student_id: string,
  name: string,
  grade_level: string,
  is_homestead: true,
  tracks: Track[]   ← grade-appropriate tracks from GRADE_EXPECTATIONS
}
```

- A new boolean column `registered_in_brain` on `aw_student_profiles` tracks completion
- If the call fails (Railway down), it retries silently the next time the student enters a room
- Migration: `004_brain_registration.sql`

---

## Section 2: Split AI Routing

### Raw Gemini (unchanged)
- Adeline in-world chat and speech bubbles (`HubWorld.tsx`)
- `ADELINE_LOG` activity detection and Life Map logging
- Quest intro hooks when entering a room
- Avatar/social/game responses

### Brain Endpoints (new)
All room missions route through the brain. Raw Gemini is the fallback only.

**Mission generation:**
```
POST {BRAIN_URL}/lesson/generate
Body: LessonRequest {
  student_id, track, topic: "auto",
  is_homestead: true, grade_level,
  render_mode: "standard_lesson"
}
```
The brain picks the ZPD-appropriate topic automatically. `RoomMission.tsx` renders the first open-ended block as the mission task.

**Credit recording (after submission):**
```
POST {BRAIN_URL}/learning/record      ← xAPI statement
POST {BRAIN_URL}/learning/transcript  ← CASE credit entry (0.1 credits)
```

**Fallback:** If `VITE_BRAIN_URL` is unset or the request times out (5s), `RoomMission` falls back to the existing Gemini path without surfacing an error to the user.

### Track Mapping: Room → Brain
| Game Room | Brain Track | Agent | Witness Protocol |
|---|---|---|---|
| Math Mines | APPLIED_MATHEMATICS | DiscipleshipAgent | No |
| Story Forest | ENGLISH_LITERATURE | DiscipleshipAgent | No |
| Science Lab | CREATION_SCIENCE | ScienceAgent | No |
| Homestead Farm | HOMESTEADING | ScienceAgent | No |
| Truth Archive | TRUTH_HISTORY | HistorianAgent | **Yes** (≥0.82) |
| Health Grove | HEALTH_NATUROPATHY | DiscipleshipAgent | No |
| The Council | GOVERNMENT_ECONOMICS | DiscipleshipAgent | No |
| Justice Quarter | JUSTICE_CHANGEMAKING | HistorianAgent | **Yes** (≥0.82) |
| The Chapel | DISCIPLESHIP | DiscipleshipAgent | No |
| Maker's Market | CREATIVE_ECONOMY | DiscipleshipAgent | No |

---

## Section 3: Full Hub — 10 Doors (5 Open, 5 Coming Soon)

### Existing (open)
math_mines, story_forest, science_lab, homestead_farm, truth_archive

### New locked portals
| Room | Track | Emoji | Color |
|---|---|---|---|
| Health Grove | HEALTH_NATUROPATHY | 🌿 | #16a34a |
| The Council | GOVERNMENT_ECONOMICS | ⚖️ | #7c3aed |
| Justice Quarter | JUSTICE_CHANGEMAKING | ✊ | #dc2626 |
| The Chapel | DISCIPLESHIP | ✝️ | #d97706 |
| Maker's Market | CREATIVE_ECONOMY | 🎨 | #c026d3 |

### Locked portal behavior
- Renders in hub world at full size with the room's emoji and color
- Overlays a 🔒 icon on the door
- Proximity prompt shows "Coming Soon" instead of "Press E to enter"
- `E` key and click do nothing
- Parent dashboard shows all 10 tracks (locked rooms display as "Coming Soon")

### Portal type change
`HUB_PORTALS` in `game.ts` gains an optional `locked?: boolean` field. `RoomPortal.tsx` and `HubWorld.tsx` handle the locked state.

---

## Section 4: New Files

### `src/lib/brainClient.ts`
Mirrors `adeline-ui/src/lib/brain-client.ts`. Provides:
```typescript
generateLesson(req: BrainLessonRequest): Promise<BrainLessonResponse | null>
recordXAPI(statement: XAPIStatement): Promise<void>
recordTranscript(entry: TranscriptEntry): Promise<void>
getTranscript(studentId: string): Promise<TranscriptEntry[]>
registerStudent(profile: StudentRegistration): Promise<void>
```
All functions fetch the live Supabase JWT and forward it. Return `null` / silent fail on network error.

### `server.ts` additions
New proxy route at `/api/brain/*`:
```typescript
app.use('/api/brain', async (req, res) => {
  const brainUrl = process.env.BRAIN_URL
  if (!brainUrl) return res.status(503).json({ error: 'Brain offline' })
  // forward request with auth headers
})
```
This keeps `BRAIN_URL` server-side only (not exposed to the client).

### `supabase/migrations/004_brain_registration.sql`
```sql
alter table public.aw_student_profiles
  add column if not exists registered_in_brain boolean default false;
```

---

## Section 5: Parent Dashboard Enrichment

`ParentDashboard.tsx` gets a second data source after brain integration:

```typescript
GET /api/brain/learning/transcript/{student_id}
```

Shows formal CASE transcript credits alongside the existing Life Map entries. Two tabs:
- **Activity Log** — `aw_life_map_entries` (what the kid did, in their words)
- **Transcript** — brain's CASE entries (verified credits with standard mapping)

This is additive — the dashboard works without the brain if Railway is down.

---

## Environment Variables

### Adelinemobile `.env`
```
BRAIN_URL=https://adeline-brain-production.up.railway.app   # server-side only
VITE_SUPABASE_URL=https://gyxowttfwqbajoapfebf.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...
GEMINI_API_KEY=...
```

### `.env.example` additions
```
# Adeline Brain (Railway) — server-side only, never exposed to client
BRAIN_URL=https://your-railway-brain-url.up.railway.app
```

---

## Implementation Sequence

1. `004_brain_registration.sql` migration + `aw_student_profiles` column
2. `src/lib/brainClient.ts` with all 5 functions + fallback handling
3. `/api/brain/*` proxy in `server.ts`
4. `addChild()` in `AuthContext.tsx` → call `registerStudent()` after Supabase insert
5. Add 5 locked portals to `HUB_PORTALS` in `game.ts`
6. Update `RoomPortal.tsx` and `HubWorld.tsx` for locked state
7. Update `RoomMission.tsx` to try brain first, fall back to Gemini
8. Update `ParentDashboard.tsx` with transcript tab
9. Wire `aw_life_map_entries` writes to also call `recordXAPI` + `recordTranscript`

---

## What Does NOT Change

- Adeline's in-world chat stays on raw Gemini — no Witness Protocol needed for conversation
- `aw_student_profiles`, `aw_life_map_entries`, `aw_season_pass` tables remain the game's local state
- The brain's existing tables (`LearningRecord`, `TranscriptEntry`, `SpacedRepetitionCard`) are the academic source of truth
- The full `dearadeline-withlove` monorepo remains the source of truth for curriculum, agents, and compliance
- No Witness Protocol, agent orchestration, or Hippocampus code goes into the Adelinemobile repo

---

## Risks

| Risk | Mitigation |
|---|---|
| Railway paused/down | All brain calls have 5s timeout + silent Gemini fallback |
| Credit inflation (every activity = 0.1 credits) | Brain's RegistrarAgent applies mastery gating before emitting CASE credit |
| JWT expiry mid-session | `brainClient.ts` always calls `supabase.auth.getSession()` fresh per request |
| Two student IDs drifting apart | `aw_student_profiles.id` is the single canonical ID everywhere |
| COPPA consistency | Both apps use same Supabase Auth + same parent account — one consent covers both |
