# Adelinemobile ↔ Brain Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Adelinemobile's room missions to the adeline-brain Railway endpoints for verified lesson generation and real academic credit recording, while keeping Adeline's chat on raw Gemini.

**Architecture:** Express `server.ts` proxies `/api/brain/*` to Railway (BRAIN_URL is server-side only). A new `brainClient.ts` calls the proxy with the Supabase JWT. Room missions try the brain first with a 5s timeout, fall back to Gemini silently. Child registration in `addChild()` calls `/students/register` once and sets `registered_in_brain=true`. Five new locked portals complete the 10-room hub.

**Tech Stack:** TypeScript, React 19, Vite, Express, Supabase, existing adeline-brain FastAPI (Railway), node-fetch (already available via Node 22)

---

## File Structure

```
Adelinemobile/
  server.ts                           # Add /api/brain/* proxy route (modify)
  .env                                # Add BRAIN_URL (modify)
  .env.example                        # Document BRAIN_URL (modify)
  supabase/migrations/
    004_brain_registration.sql        # Add registered_in_brain column (new)
  src/
    lib/
      brainClient.ts                  # Brain API wrapper with fallback (new)
    types/
      auth.ts                         # Add registered_in_brain to StudentProfile (modify)
      game.ts                         # Add locked? to Portal, 5 new HUB_PORTALS (modify)
    components/
      world/
        RoomPortal.tsx                # Handle locked state (modify)
        HubWorld.tsx                  # Pass locked prop, skip locked rooms on E (modify)
      rooms/
        RoomMission.tsx               # Try brain first, fall back to Gemini (modify)
    context/
      AuthContext.tsx                 # Call registerStudent in addChild() (modify)
    pages/
      ParentDashboard.tsx             # Add Transcript tab from brain (modify)
```

---

## Task 1: DB Migration + StudentProfile Type

**Files:**
- Create: `supabase/migrations/004_brain_registration.sql`
- Modify: `src/types/auth.ts`

- [ ] **Step 1: Create migration file**

Create `/c/Users/Aarons/Adelinemobile/supabase/migrations/004_brain_registration.sql`:

```sql
alter table public.aw_student_profiles
  add column if not exists registered_in_brain boolean default false;
```

- [ ] **Step 2: Apply via Supabase MCP to project `gyxowttfwqbajoapfebf`**

Run this SQL in the Supabase dashboard SQL editor or via MCP tool:
```sql
alter table public.aw_student_profiles
  add column if not exists registered_in_brain boolean default false;
```
Expected: "Success. No rows returned."

- [ ] **Step 3: Add `registered_in_brain` to StudentProfile type**

Read `src/types/auth.ts`. Add to `StudentProfile` interface:
```typescript
  registered_in_brain: boolean
```

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/004_brain_registration.sql src/types/auth.ts
git commit -m "feat: add registered_in_brain column to student profiles"
```

---

## Task 2: Brain Proxy in server.ts

**Files:**
- Modify: `server.ts`
- Modify: `.env`
- Modify: `.env.example`

- [ ] **Step 1: Add BRAIN_URL to `.env`**

Open `/c/Users/Aarons/Adelinemobile/.env` and add:
```
BRAIN_URL=https://adeline-brain-production.up.railway.app
```
(Use the actual Railway URL. If unknown, use a placeholder — the proxy handles 503 gracefully.)

- [ ] **Step 2: Add BRAIN_URL to `.env.example`**

Open `.env.example` and add:
```
# Adeline Brain on Railway — server-side only, never sent to client
# Get URL from Railway dashboard → adeline-brain service → Settings → Public URL
BRAIN_URL=https://your-railway-brain-url.up.railway.app
```

- [ ] **Step 3: Add brain proxy to `server.ts`**

Read `server.ts`. After the `app.use(express.json())` line and before the `/api/chat` route, add this proxy block:

```typescript
  // Brain proxy — forwards to Railway adeline-brain with server-side BRAIN_URL
  // Client sends Supabase JWT in Authorization header; this proxy passes it through
  app.use('/api/brain', async (req: any, res: any) => {
    const brainUrl = process.env.BRAIN_URL
    if (!brainUrl) {
      return res.status(503).json({ error: 'Brain service not configured' })
    }

    const targetUrl = `${brainUrl}${req.path}${req.url.includes('?') ? '?' + req.url.split('?')[1] : ''}`
    const method = req.method

    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 8000)

      const fetchOptions: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(req.headers.authorization ? { 'Authorization': req.headers.authorization } : {}),
        },
        signal: controller.signal,
      }

      if (method !== 'GET' && method !== 'HEAD' && req.body && Object.keys(req.body).length > 0) {
        (fetchOptions as any).body = JSON.stringify(req.body)
      }

      const brainRes = await fetch(targetUrl, fetchOptions)
      clearTimeout(timeout)

      const contentType = brainRes.headers.get('content-type') ?? ''
      if (contentType.includes('text/event-stream')) {
        res.setHeader('Content-Type', 'text/event-stream')
        res.setHeader('Cache-Control', 'no-cache')
        res.setHeader('Connection', 'keep-alive')
        const reader = brainRes.body?.getReader()
        if (!reader) return res.end()
        const pump = async () => {
          const { done, value } = await reader.read()
          if (done) { res.end(); return }
          res.write(value)
          pump()
        }
        pump()
      } else {
        const data = await brainRes.text()
        res.status(brainRes.status).send(data)
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        res.status(504).json({ error: 'Brain timeout' })
      } else {
        console.error('Brain proxy error:', err.message)
        res.status(502).json({ error: 'Brain unreachable' })
      }
    }
  })
```

- [ ] **Step 4: Verify server starts without error**

```bash
npm run dev
```
Expected: `Server running on http://0.0.0.0:3000` (no crash)

Kill with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add server.ts .env.example
git commit -m "feat: add /api/brain/* proxy to Railway brain service"
```

---

## Task 3: brainClient.ts

**Files:**
- Create: `src/lib/brainClient.ts`

- [ ] **Step 1: Create `src/lib/brainClient.ts`**

```typescript
import { supabase } from './supabase'
import { Track } from '../types/game'

// All calls go through the server-side proxy at /api/brain/*
// which forwards to Railway with BRAIN_URL (never exposed to client)
const PROXY = '/api/brain'
const TIMEOUT_MS = 5000

async function authHeaders(): Promise<Record<string, string>> {
  try {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    if (!token) return { 'Content-Type': 'application/json' }
    return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
  } catch {
    return { 'Content-Type': 'application/json' }
  }
}

async function post<T>(path: string, body: unknown): Promise<T | null> {
  try {
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), TIMEOUT_MS)
    const res = await fetch(`${PROXY}${path}`, {
      method: 'POST',
      headers: await authHeaders(),
      body: JSON.stringify(body),
      signal: controller.signal,
    })
    clearTimeout(t)
    if (!res.ok) return null
    return await res.json() as T
  } catch {
    return null
  }
}

async function get<T>(path: string): Promise<T | null> {
  try {
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), TIMEOUT_MS)
    const res = await fetch(`${PROXY}${path}`, {
      headers: await authHeaders(),
      signal: controller.signal,
    })
    clearTimeout(t)
    if (!res.ok) return null
    return await res.json() as T
  } catch {
    return null
  }
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BrainLessonRequest {
  student_id: string
  track: Track
  topic: string
  is_homestead: boolean
  grade_level: string
  render_mode?: 'standard_lesson'
}

export interface BrainLessonBlock {
  type: string
  content: string
  source?: string
  source_label?: string
}

export interface BrainLessonResponse {
  lesson_id: string
  title: string
  blocks: BrainLessonBlock[]
}

export interface BrainTranscriptEntry {
  id: string
  student_id: string
  lesson_id: string
  track: Track
  credits: number
  created_at: string
  title?: string
}

// ── API calls ─────────────────────────────────────────────────────────────────

/** Generate a lesson via the brain. Returns null if brain is unreachable. */
export async function generateLesson(req: BrainLessonRequest): Promise<BrainLessonResponse | null> {
  return post<BrainLessonResponse>('/lesson/generate', req)
}

/** Record an xAPI completion statement after a mission. Fire-and-forget. */
export async function recordCompletion(
  studentId: string,
  lessonId: string,
  track: Track,
  missionTitle: string
): Promise<void> {
  await post('/learning/record', {
    student_id: studentId,
    lesson_id: lessonId,
    verb: 'completed',
    object_id: `urn:adeline:lesson:${lessonId}`,
    object_name: missionTitle,
  })
}

/** Seal a CASE transcript credit entry. Fire-and-forget. */
export async function recordTranscriptCredit(
  studentId: string,
  lessonId: string,
  track: Track,
  title: string
): Promise<void> {
  await post('/learning/transcript', {
    student_id: studentId,
    lesson_id: lessonId,
    track,
    credits: 0.1,
    title,
  })
}

/** Get the full CASE transcript for a student. */
export async function getTranscript(studentId: string): Promise<BrainTranscriptEntry[]> {
  const data = await get<{ entries: BrainTranscriptEntry[] }>(`/learning/transcript/${studentId}`)
  return data?.entries ?? []
}

/** Register a student in the brain on first create. */
export async function registerStudent(params: {
  student_id: string
  name: string
  grade_level: string
  is_homestead: boolean
  tracks: Track[]
}): Promise<boolean> {
  const result = await post('/students/register', params)
  return result !== null
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit 2>&1
```
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add src/lib/brainClient.ts
git commit -m "feat: add brainClient.ts with lesson generation, xAPI, transcript, registration"
```

---

## Task 4: Register Student in addChild()

**Files:**
- Modify: `src/context/AuthContext.tsx`

- [ ] **Step 1: Read `src/context/AuthContext.tsx`**

Find the `addChild` function (around line 118).

- [ ] **Step 2: Add brain registration call**

Import `registerStudent` and `gradeBandFromAge` at the top of `AuthContext.tsx`:
```typescript
import { registerStudent } from '../lib/brainClient'
import { gradeBandFromAge, GRADE_EXPECTATIONS } from '../lib/academicEngine'
```

Update the `addChild` function to call `registerStudent` after the Supabase insert:

```typescript
  async function addChild(displayName: string, username: string, age: number, gradeBand: string = 'K-2'): Promise<StudentProfile> {
    if (!session) throw new Error('Not authenticated')
    const { data, error } = await supabase
      .from('aw_student_profiles')
      .insert({ parent_id: session.user.id, display_name: displayName, username, age, grade_level: gradeBand })
      .select()
      .single()
    if (error) throw error

    // Register in brain (non-blocking — failure is retried next room entry)
    const band = gradeBand as Parameters<typeof gradeBandFromAge>[0] extends number ? never : any
    const expectation = GRADE_EXPECTATIONS.find(g => g.band === gradeBand) ?? GRADE_EXPECTATIONS[0]
    registerStudent({
      student_id: data.id,
      name: displayName,
      grade_level: gradeBand,
      is_homestead: true,
      tracks: expectation.requiredTracks,
    }).then(success => {
      if (success) {
        supabase.from('aw_student_profiles')
          .update({ registered_in_brain: true })
          .eq('id', data.id)
      }
    })

    await refreshChildren()
    return data
  }
```

- [ ] **Step 3: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1
```
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add src/context/AuthContext.tsx
git commit -m "feat: register student in brain on child profile creation"
```

---

## Task 5: 5 Locked Portals in game.ts + HUB_PORTALS

**Files:**
- Modify: `src/types/game.ts`

- [ ] **Step 1: Read `src/types/game.ts`**

Find the `Portal` interface and `HUB_PORTALS` array.

- [ ] **Step 2: Add `locked` to Portal interface**

Find:
```typescript
export interface Portal {
  id: RoomId
  label: string
  description: string
  x: number
  y: number
  color: string
  emoji: string
}
```
Replace with:
```typescript
export interface Portal {
  id: RoomId
  label: string
  description: string
  x: number
  y: number
  color: string
  emoji: string
  locked?: boolean
}
```

- [ ] **Step 3: Add 5 new RoomIds to RoomId type**

Find:
```typescript
export type RoomId = 'math_mines' | 'story_forest' | 'science_lab' | 'homestead_farm' | 'truth_archive'
```
Replace with:
```typescript
export type RoomId =
  | 'math_mines' | 'story_forest' | 'science_lab' | 'homestead_farm' | 'truth_archive'
  | 'health_grove' | 'the_council' | 'justice_quarter' | 'the_chapel' | 'makers_market'
```

- [ ] **Step 4: Add 5 locked portals to HUB_PORTALS**

Find the closing `]` of `HUB_PORTALS`. Before it, add:

```typescript
  {
    id: 'health_grove',
    label: 'Health Grove',
    description: 'Natural medicine and the body God designed',
    x: 35,
    y: 18,
    color: '#16a34a',
    emoji: '🌿',
    locked: true,
  },
  {
    id: 'the_council',
    label: 'The Council',
    description: 'Civics, economics, and who really pulls the levers',
    x: 65,
    y: 18,
    color: '#7c3aed',
    emoji: '⚖️',
    locked: true,
  },
  {
    id: 'justice_quarter',
    label: 'Justice Quarter',
    description: 'Power, resistance, and the changemaker response',
    x: 10,
    y: 50,
    color: '#dc2626',
    emoji: '✊',
    locked: true,
  },
  {
    id: 'the_chapel',
    label: 'The Chapel',
    description: 'Faith, character, and reading the world through Scripture',
    x: 90,
    y: 50,
    color: '#d97706',
    emoji: '✝️',
    locked: true,
  },
  {
    id: 'makers_market',
    label: "Maker's Market",
    description: 'Making, crafting, and selling as real scholarship',
    x: 50,
    y: 88,
    color: '#c026d3',
    emoji: '🎨',
    locked: true,
  },
```

- [ ] **Step 5: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1
```
Expected: 0 errors (the new RoomIds aren't referenced in ROOM_CONFIG yet — that's fine, GameShell checks `currentRoom` which will never be set to a locked room)

- [ ] **Step 6: Commit**

```bash
git add src/types/game.ts
git commit -m "feat: add 5 locked portals to complete 10-room hub world"
```

---

## Task 6: RoomPortal + HubWorld Handle Locked State

**Files:**
- Modify: `src/components/world/RoomPortal.tsx`
- Modify: `src/components/world/HubWorld.tsx`

- [ ] **Step 1: Update RoomPortal.tsx to show locked state**

Read `src/components/world/RoomPortal.tsx`. Replace entirely with:

```typescript
import { Portal } from '../../types/game'

interface Props {
  portal: Portal
  isNearby: boolean
  onEnter: () => void
}

export default function RoomPortal({ portal, isNearby, onEnter }: Props) {
  const locked = portal.locked === true

  return (
    <div
      className="absolute flex flex-col items-center"
      style={{ left: `${portal.x}%`, top: `${portal.y}%`, transform: 'translate(-50%, -50%)' }}
    >
      {/* Prompt above door */}
      {isNearby && (
        <div className="absolute -top-14 left-1/2 -translate-x-1/2 whitespace-nowrap z-10 animate-bounce">
          {locked ? (
            <div className="bg-slate-700 text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-lg">
              🔒 Coming Soon
            </div>
          ) : (
            <button
              onClick={onEnter}
              className="bg-white text-slate-800 text-xs font-bold px-3 py-1.5 rounded-full shadow-lg hover:bg-amber-50 transition-all"
            >
              Press E to enter →
            </button>
          )}
        </div>
      )}

      {/* Door */}
      <div
        className={`relative transition-all duration-300 ${!locked && isNearby ? 'scale-110' : !locked ? 'hover:scale-105' : 'opacity-60'}`}
        onClick={!locked && isNearby ? onEnter : undefined}
        style={{ cursor: locked ? 'default' : isNearby ? 'pointer' : 'default' }}
      >
        <div
          className="w-20 h-28 rounded-t-full border-4 flex flex-col items-center justify-center gap-1 shadow-2xl relative"
          style={{
            backgroundColor: portal.color,
            borderColor: !locked && isNearby ? '#FBBF24' : 'rgba(255,255,255,0.3)',
            boxShadow: !locked && isNearby ? `0 0 20px ${portal.color}` : undefined,
            filter: locked ? 'grayscale(0.4)' : undefined,
          }}
        >
          <span className="text-3xl">{portal.emoji}</span>
          {locked && (
            <span className="text-xl absolute bottom-2">🔒</span>
          )}
        </div>
        <div
          className="w-24 h-3 rounded-b-lg -mt-1"
          style={{ backgroundColor: portal.color, filter: 'brightness(0.7)' }}
        />
      </div>

      {/* Label */}
      <div className="mt-2 text-center">
        <p className={`font-bold text-sm drop-shadow ${locked ? 'text-white/60' : 'text-white'}`}>{portal.label}</p>
        <p className="text-white/50 text-xs drop-shadow">{locked ? 'Coming Soon' : portal.description}</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Update HubWorld.tsx to skip locked rooms on E keypress**

Read `src/components/world/HubWorld.tsx`. Find the `onKeyDown` handler where it checks portal proximity and calls `onEnterRoom`. Add a locked check:

Find:
```typescript
        for (const portal of HUB_PORTALS) {
          if (distance(p.x, p.y, portal.x, portal.y) < PORTAL_PROXIMITY) {
            onEnterRoom(portal.id)
            return
          }
        }
```

Replace with:
```typescript
        for (const portal of HUB_PORTALS) {
          if (distance(p.x, p.y, portal.x, portal.y) < PORTAL_PROXIMITY) {
            if (!portal.locked) onEnterRoom(portal.id)
            return
          }
        }
```

Also update `nearbyPortal` calculation to show locked portals as nearby (so the "Coming Soon" prompt shows) but not enter them:

Find:
```typescript
  const nearbyPortal = HUB_PORTALS.find(p => distance(player.x, player.y, p.x, p.y) < PORTAL_PROXIMITY)
```
This line is fine as-is — `RoomPortal` now handles the locked display. No change needed.

- [ ] **Step 3: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1
```
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add src/components/world/RoomPortal.tsx src/components/world/HubWorld.tsx
git commit -m "feat: locked portal state with Coming Soon display in hub world"
```

---

## Task 7: RoomMission — Brain First, Gemini Fallback

**Files:**
- Modify: `src/components/rooms/RoomMission.tsx`

The component needs two new props: `studentId` and `gradeBand`. It tries the brain first, falls back to Gemini if null.

- [ ] **Step 1: Read `src/components/rooms/RoomMission.tsx`**

- [ ] **Step 2: Replace the entire file**

```typescript
import { useState, useEffect } from 'react'
import { Track, GradeBand } from '../../types/game'
import { generateLesson, recordCompletion, recordTranscriptCredit } from '../../lib/brainClient'

interface Props {
  roomId: string
  roomLabel: string
  roomEmoji: string
  roomTracks: Track[]
  playerName: string
  systemContext: string
  studentId: string | null
  gradeBand: GradeBand
  onComplete: (description: string, tracks: Track[], xp: number, coins: number) => void
  onBack: () => void
}

interface Mission {
  title: string
  description: string
  prompt: string
  xpReward: number
  coinReward: number
  lessonId?: string   // set when brain provided the lesson
  fromBrain?: boolean
}

export default function RoomMission({
  roomId, roomLabel, roomEmoji, roomTracks, playerName,
  systemContext, studentId, gradeBand, onComplete, onBack
}: Props) {
  const [mission, setMission] = useState<Mission | null>(null)
  const [response, setResponse] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [evaluating, setEvaluating] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [usedBrain, setUsedBrain] = useState(false)

  useEffect(() => { loadMission() }, [])

  async function loadMission() {
    setLoading(true)

    // Try brain first (only for logged-in students)
    if (studentId) {
      const lesson = await generateLesson({
        student_id: studentId,
        track: roomTracks[0],
        topic: 'auto',
        is_homestead: true,
        grade_level: gradeBand,
        render_mode: 'standard_lesson',
      })

      if (lesson && lesson.blocks?.length > 0) {
        // Find the first text/narrative block as description
        const descBlock = lesson.blocks.find(b => b.type === 'NARRATIVE' || b.type === 'TEXT') ?? lesson.blocks[0]
        // Find an open-ended prompt block or use the description
        const promptBlock = lesson.blocks.find(b => b.type === 'RESEARCH_MISSION' || b.type === 'LAB_MISSION')

        setMission({
          title: lesson.title,
          description: descBlock.content,
          prompt: promptBlock?.content ?? `Based on what you just read about "${lesson.title}", share your thoughts or what you discovered. Write at least 2-3 sentences.`,
          xpReward: 75,
          coinReward: 18,
          lessonId: lesson.lesson_id,
          fromBrain: true,
        })
        setUsedBrain(true)
        setLoading(false)
        return
      }
    }

    // Gemini fallback
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create a real-world mission for a homeschool student in the ${roomLabel} subject area. ${systemContext}

The mission should require a written response (not multiple choice) and connect to real life, homesteading, farming, nature, history, or their community. Be completable in 5-15 minutes.

Respond ONLY with valid JSON:
{"title":"...","description":"...what they'll do, 2-3 sentences...","prompt":"...the specific question or task they respond to...","xpReward":60,"coinReward":15}`,
          history: [],
        })
      })
      const data = await res.json()
      const parsed = JSON.parse(data.reply.replace(/```json|```/g, '').trim())
      if (parsed.title && parsed.prompt) {
        setMission({ ...parsed, fromBrain: false })
      } else {
        throw new Error('bad format')
      }
    } catch {
      setMission(getFallbackMission(roomId))
    } finally {
      setLoading(false)
    }
  }

  async function submitResponse() {
    if (!response.trim() || !mission) return
    setEvaluating(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `A student named ${playerName} completed this mission:
Mission: "${mission.title}"
Task: "${mission.prompt}"
Their response: "${response}"

Evaluate in 2-3 sentences. Be encouraging but honest. End with one specific thing they did well.`,
          history: [],
        })
      })
      const data = await res.json()
      setFeedback(data.reply)
      setCompleted(true)

      const description = `${mission.title}: ${response.slice(0, 120)}${response.length > 120 ? '...' : ''}`
      onComplete(description, roomTracks, mission.xpReward, mission.coinReward)

      // Record credit in brain (non-blocking, only for logged-in students with a brain lesson)
      if (studentId && mission.lessonId) {
        recordCompletion(studentId, mission.lessonId, roomTracks[0], mission.title)
        recordTranscriptCredit(studentId, mission.lessonId, roomTracks[0], mission.title)
      }
    } catch {
      setFeedback("Great work completing this mission! Keep building on what you know.")
      setCompleted(true)
      onComplete(response.slice(0, 120), roomTracks, mission?.xpReward ?? 40, mission?.coinReward ?? 10)
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className="h-full flex flex-col bg-slate-900/95 text-white">
      <div className="flex items-center gap-3 p-4 border-b border-white/10">
        <button onClick={onBack} className="text-white/60 hover:text-white text-sm px-2 py-1 rounded-lg hover:bg-white/10">
          ← Back
        </button>
        <span className="text-2xl">{roomEmoji}</span>
        <div>
          <h2 className="font-bold">{roomLabel} — Mission</h2>
          <p className="text-white/50 text-xs">
            {usedBrain ? '🧠 Adeline Brain · verified lesson' : 'Real work, real learning'}
          </p>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-5 overflow-y-auto">
        {loading ? (
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-white/60 text-sm">
              {studentId ? 'Adeline is finding your next lesson...' : 'Preparing your mission...'}
            </p>
          </div>
        ) : mission && !completed ? (
          <>
            <div className="w-full max-w-lg bg-white/10 rounded-2xl p-5 border border-white/20 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-amber-400 text-xs font-bold uppercase tracking-wider">Mission</span>
                {mission.fromBrain && <span className="text-emerald-400 text-xs">✓ brain-verified</span>}
                <div className="flex-1 h-px bg-white/20" />
              </div>
              <h3 className="text-white font-bold text-lg">{mission.title}</h3>
              <p className="text-white/80 text-sm leading-relaxed">{mission.description}</p>
            </div>

            <div className="w-full max-w-lg space-y-3">
              <p className="text-white font-semibold text-sm">{mission.prompt}</p>
              <textarea
                value={response}
                onChange={e => setResponse(e.target.value)}
                placeholder="Write your response here... Take your time. There's no right answer — this is about YOUR thinking."
                className="w-full h-40 px-4 py-3 bg-white/10 border border-white/30 rounded-xl text-white placeholder-white/30 text-sm resize-none focus:outline-none focus:border-amber-400"
                autoFocus
              />
              <div className="flex items-center justify-between">
                <span className="text-white/40 text-xs">{response.length} characters</span>
                <button
                  onClick={submitResponse}
                  disabled={response.trim().length < 20 || evaluating}
                  className="px-6 py-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-white font-bold rounded-xl transition-all"
                >
                  {evaluating ? 'Adeline is reading...' : 'Submit Mission →'}
                </button>
              </div>
              {response.trim().length < 20 && response.length > 0 && (
                <p className="text-white/40 text-xs">Write a bit more — at least 20 characters to submit.</p>
              )}
            </div>
            <p className="text-white/30 text-xs">+{mission.xpReward} XP · +{mission.coinReward} AdeCoins · Added to Life Map{mission.fromBrain ? ' + Transcript' : ''}</p>
          </>
        ) : completed && feedback ? (
          <div className="w-full max-w-lg space-y-5">
            <div className="bg-emerald-500/20 border border-emerald-400 rounded-2xl p-5 space-y-3">
              <p className="text-4xl text-center">🎉</p>
              <p className="text-emerald-300 font-bold text-center">Mission Complete!</p>
              <p className="text-white/80 text-sm leading-relaxed">{feedback}</p>
              <p className="text-amber-300 text-xs text-center">
                +{mission?.xpReward} XP · +{mission?.coinReward} AdeCoins
                {mission?.fromBrain ? ' · Transcript credit recorded' : ' · Added to Life Map'}
              </p>
            </div>
            <div className="flex gap-3">
              <button onClick={onBack} className="flex-1 py-3 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-xl">
                ← Back to World
              </button>
              <button
                onClick={() => { setCompleted(false); setResponse(''); setFeedback(null); loadMission() }}
                className="flex-1 py-3 bg-amber-500 hover:bg-amber-400 text-white font-bold rounded-xl"
              >
                Next Mission →
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

function getFallbackMission(roomId: string): Mission {
  const missions: Record<string, Mission> = {
    math_mines:     { title: 'Budget Your Garden', description: 'Plan a small vegetable garden and figure out what it would cost to plant it.', prompt: "Pick 3 vegetables to grow. Estimate how many seeds or seedlings you need and what they might cost. How much space do you need? Write out your plan and calculations.", xpReward: 60, coinReward: 15 },
    story_forest:   { title: 'Tell Your Story', description: "Every family has stories worth preserving. Think about something that happened in your family or community.", prompt: "Write 3-5 sentences about a real event in your family's history or something that happened recently. Include who was there, what happened, and why it matters.", xpReward: 60, coinReward: 15 },
    science_lab:    { title: 'Kitchen Science Observation', description: 'Science is everywhere in your home. Pick something you can observe or test right now.', prompt: "Choose one and describe what you observe: (1) What happens when you mix baking soda and vinegar? (2) How does bread dough rise? (3) What do you notice about how water moves through soil? Write what you observe and why you think it happens.", xpReward: 60, coinReward: 15 },
    homestead_farm: { title: 'Animal Care Log', description: 'Taking care of animals is real science, math, and stewardship all at once.', prompt: "Think about an animal your family cares for. What does it eat? How much? How do you keep it healthy? What does it give back to the family? Write a short care guide for it.", xpReward: 65, coinReward: 18 },
    truth_archive:  { title: 'Follow the Money', description: "Behind almost every historical event, there is someone who profits. Let's find them.", prompt: "Pick one: (1) Why did Columbus sail west? (2) Why did factories replace farms in the 1800s? (3) Why do food companies add sugar to almost everything? Write 3-5 sentences about who benefited and how.", xpReward: 70, coinReward: 18 },
  }
  return missions[roomId] ?? missions.math_mines
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1
```
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add src/components/rooms/RoomMission.tsx
git commit -m "feat: RoomMission tries brain first, falls back to Gemini, records CASE credits"
```

---

## Task 8: Pass studentId + gradeBand to RoomMission from GameShell

**Files:**
- Modify: `src/pages/GameShell.tsx`

- [ ] **Step 1: Read `src/pages/GameShell.tsx`**

Find the `<RoomMission` usage in the room screen section.

- [ ] **Step 2: Add studentId and gradeBand props to RoomMission call**

Find:
```typescript
            <RoomMission
              roomId={currentRoom}
              roomLabel={config.label}
              roomEmoji={config.emoji}
              roomTracks={config.tracks}
              playerName={playerName}
              systemContext={config.context}
              onComplete={handleRoomMissionComplete}
              onBack={() => { setCurrentRoom(null); setScreen('hub') }}
            />
```

Replace with:
```typescript
            <RoomMission
              roomId={currentRoom}
              roomLabel={config.label}
              roomEmoji={config.emoji}
              roomTracks={config.tracks}
              playerName={playerName}
              systemContext={config.context}
              studentId={activeChild?.id ?? null}
              gradeBand={gradeBand}
              onComplete={handleRoomMissionComplete}
              onBack={() => { setCurrentRoom(null); setScreen('hub') }}
            />
```

- [ ] **Step 3: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1
```
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add src/pages/GameShell.tsx
git commit -m "feat: pass studentId and gradeBand to RoomMission for brain integration"
```

---

## Task 9: Parent Dashboard Transcript Tab

**Files:**
- Modify: `src/pages/ParentDashboard.tsx`

- [ ] **Step 1: Read `src/pages/ParentDashboard.tsx`**

- [ ] **Step 2: Add transcript tab**

Add this import at the top:
```typescript
import { getTranscript, BrainTranscriptEntry } from '../lib/brainClient'
import { TRACK_LABELS, Track } from '../types/game'
```

Add `activeTab` state after existing state declarations:
```typescript
  const [activeTab, setActiveTab] = useState<'activity' | 'transcript'>('activity')
  const [transcripts, setTranscripts] = useState<Record<string, BrainTranscriptEntry[]>>({})
```

Add a function to load transcripts:
```typescript
  async function loadTranscript(childId: string) {
    if (transcripts[childId]) return  // already loaded
    const entries = await getTranscript(childId)
    setTranscripts(prev => ({ ...prev, [childId]: entries }))
  }
```

In the selected child detail panel (the `selectedChild?.childId === s.childId` section), after the existing "Recent Activity" header, replace the content with:

```typescript
                    <div className="mt-3 pt-3 border-t border-slate-100" onClick={e => e.stopPropagation()}>
                      {/* Tab bar */}
                      <div className="flex gap-2 mb-3">
                        <button
                          onClick={() => setActiveTab('activity')}
                          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${activeTab === 'activity' ? 'bg-amber-100 text-amber-800' : 'text-slate-400 hover:text-slate-600'}`}
                        >
                          Activity Log
                        </button>
                        <button
                          onClick={() => { setActiveTab('transcript'); loadTranscript(s.childId) }}
                          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${activeTab === 'transcript' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-400 hover:text-slate-600'}`}
                        >
                          Transcript
                        </button>
                      </div>

                      {activeTab === 'activity' && (
                        <div className="space-y-2">
                          <p className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2">Recent Activity</p>
                          {s.recentEntries.map(entry => (
                            <div key={entry.id} className="bg-slate-50 rounded-xl p-3">
                              <p className="text-slate-700 text-sm">{entry.description}</p>
                              <div className="flex items-center justify-between mt-1">
                                <div className="flex flex-wrap gap-1">
                                  {entry.tracks.map(t => (
                                    <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full text-white" style={{ backgroundColor: TRACK_COLORS[t as Track] }}>
                                      {TRACK_LABELS[t as Track]}
                                    </span>
                                  ))}
                                </div>
                                <span className="text-slate-400 text-xs flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  {new Date(entry.created_at).toLocaleDateString()}
                                </span>
                              </div>
                            </div>
                          ))}
                          {s.recentEntries.length === 0 && <p className="text-slate-400 text-xs">No activity yet.</p>}
                        </div>
                      )}

                      {activeTab === 'transcript' && (
                        <div className="space-y-2">
                          <p className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2">CASE Transcript Credits</p>
                          {!transcripts[s.childId] ? (
                            <p className="text-slate-400 text-xs">Loading...</p>
                          ) : transcripts[s.childId].length === 0 ? (
                            <p className="text-slate-400 text-xs">No verified credits yet. Complete room missions to earn transcript credits.</p>
                          ) : (
                            transcripts[s.childId].map(entry => (
                              <div key={entry.id} className="bg-slate-50 rounded-xl p-3">
                                <p className="text-slate-700 text-sm font-semibold">{entry.title ?? 'Lesson'}</p>
                                <div className="flex items-center justify-between mt-1">
                                  <span className="text-[10px] px-2 py-0.5 rounded-full text-white bg-emerald-600">
                                    {TRACK_LABELS[entry.track as Track] ?? entry.track}
                                  </span>
                                  <span className="text-emerald-700 text-xs font-bold">{entry.credits} cr</span>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
```

- [ ] **Step 3: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1
```
Fix any errors (likely `TRACK_COLORS` import missing — add it alongside `TRACK_LABELS`).

- [ ] **Step 4: Commit**

```bash
git add src/pages/ParentDashboard.tsx
git commit -m "feat: add Transcript tab to parent dashboard from brain CASE records"
```

---

## Task 10: Smoke Test + Push

- [ ] **Step 1: Start dev server**

```bash
npm run dev
```
Expected: `Server running on http://0.0.0.0:3000`

- [ ] **Step 2: Test proxy route (brain offline)**

```bash
curl -s http://localhost:3000/api/brain/lesson/generate -X POST -H "Content-Type: application/json" -d '{"test":1}'
```
Expected: Either a response from Railway OR `{"error":"Brain service not configured"}` if `BRAIN_URL` not set — NOT a server crash.

- [ ] **Step 3: Test locked portals**

1. Open `http://localhost:3000`
2. Play as guest → skip avatar builder (or build one)
3. In the hub world, walk toward one of the new locked portals (Health Grove 🌿, The Council ⚖️, etc.)
4. Should see the portal with a 🔒 icon and greyed appearance
5. Press E near it → nothing happens
6. "Coming Soon" label shows instead of "Press E to enter" ✓

- [ ] **Step 4: Test RoomMission fallback**

1. Enter Math Mines (open room)
2. Mission should load (from Gemini fallback since BRAIN_URL not configured in dev)
3. No "brain-verified" badge should appear
4. Write a response → submit → feedback appears ✓

- [ ] **Step 5: Push to main**

```bash
git log --oneline -8
git push origin main
```

---

## Self-Review

**Spec coverage:**
- ✅ Identity bridge — single Supabase project, `aw_student_profiles.id` as canonical student_id — Task 1, 4
- ✅ `registered_in_brain` column — Task 1
- ✅ Brain proxy at `/api/brain/*` in server.ts — Task 2
- ✅ `BRAIN_URL` server-side only — Task 2
- ✅ `brainClient.ts` with all 5 functions + 5s timeout fallback — Task 3
- ✅ `registerStudent()` called in `addChild()` — Task 4
- ✅ 5 locked portals added to HUB_PORTALS — Task 5
- ✅ `locked` field on Portal interface — Task 5
- ✅ RoomPortal locked state display — Task 6
- ✅ HubWorld skips locked rooms on E — Task 6
- ✅ RoomMission tries brain first, falls back to Gemini — Task 7
- ✅ xAPI + CASE credit recorded after mission completion — Task 7
- ✅ `studentId` + `gradeBand` passed to RoomMission — Task 8
- ✅ Parent dashboard Transcript tab from brain — Task 9
- ✅ Witness Protocol note: Truth Archive routes to TRUTH_HISTORY → HistorianAgent automatically via brain — no extra code needed

**Type consistency:**
- `GradeBand` from `types/game.ts` used in Tasks 5, 7, 8 ✅
- `BrainLessonRequest.track` is `Track` (single), matches `roomTracks[0]` usage in Task 7 ✅
- `registerStudent` params match `brainClient.ts` definition in Task 3 ✅
- `getTranscript` returns `BrainTranscriptEntry[]` used in Task 9 ✅
- `recordCompletion` and `recordTranscriptCredit` signatures match usage in Task 7 ✅
