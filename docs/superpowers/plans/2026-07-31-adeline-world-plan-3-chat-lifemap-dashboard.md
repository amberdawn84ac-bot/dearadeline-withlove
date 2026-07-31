# Adeline World — Plan 3: Chat-First UI, Activity Logging, Life Map, Room Missions, Season Pass, Parent Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the game from hub-first to chat-first — Adeline is the home base. She learns about each kid through conversation, detects and logs real-life activities to the Life Map, assigns open-ended room missions (not just quizzes), and parents get a dashboard showing everything.

**Architecture:** Adeline chat becomes the main screen. Rooms are launched from a sidebar/overlay within the chat view. Activity logging runs through the Gemini conversation — Adeline detects real-world activities mentioned in chat, confirms them, and writes `aw_life_map_entries` to Supabase. Student memories (interests, projects, family context) are stored in `aw_student_memories` so Adeline remembers each kid across sessions. Room missions are open-ended text projects evaluated by Gemini, not multiple-choice quizzes. Season pass tracks XP tiers. Parent dashboard is a separate route protected by parent session.

**Tech Stack:** React 19, TypeScript, Tailwind, Supabase (existing), Gemini via `/api/chat`, React Router (existing), AuthContext (Plan 1)

---

## File Structure

```
src/
  types/
    game.ts              # Add: LifeMapEntry, Track, SeasonTier, StudentMemory (modify)
  lib/
    memoryService.ts     # Adeline's student memory CRUD — read/write aw_student_memories (new)
    lifeMapService.ts    # Log activities to aw_life_map_entries, read Life Map (new)
  components/
    chat/
      AdelineChat.tsx    # Main chat UI — messages, input, activity detection banner (new)
      ActivityConfirm.tsx # Banner: "Adeline wants to log an activity — confirm?" (new)
    life-map/
      LifeMap.tsx        # Visual Life Map: track grid + entry cards (new)
    season-pass/
      SeasonPass.tsx     # Season pass tier display + XP progress (new)
    rooms/
      RoomMission.tsx    # Open-ended mission UI used by ALL rooms (new)
      MathMines.tsx      # Add mission mode alongside quiz mode (modify)
      StoryForest.tsx    # Add mission mode (modify)
      ScienceLab.tsx     # Add mission mode (modify)
      HomesteadFarm.tsx  # Add mission mode (modify)
      TruthArchive.tsx   # Add mission mode (modify)
  pages/
    GameShell.tsx        # Refactor: chat-first layout, room sidebar, all screens (modify)
    ParentDashboard.tsx  # Parent-only route: activity log, approvals, stats (new)
  App.tsx                # Add /parent-dashboard route (modify)
```

### New Supabase Tables (applied via MCP)

```sql
-- What Adeline knows about each student
aw_student_memories:
  id uuid PK
  student_id uuid FK → aw_student_profiles.id
  key text          -- e.g. 'interests', 'current_projects', 'homestead_animals', 'learning_style'
  value text        -- free-form text Adeline writes
  updated_at timestamptz

-- Every logged real-world activity (the Life Map entries)
aw_life_map_entries:
  id uuid PK
  student_id uuid FK → aw_student_profiles.id
  description text       -- what the student did, in their words
  tracks text[]          -- e.g. ['HOMESTEADING', 'APPLIED_MATHEMATICS']
  xp_awarded integer
  coins_awarded integer
  source text            -- 'chat_log' | 'room_mission' | 'parent_log'
  created_at timestamptz

-- Season pass: which cosmetics/rewards are unlocked per student
aw_season_pass:
  id uuid PK
  student_id uuid FK → aw_student_profiles.id
  season integer default 1
  claimed_tiers integer[] default '{}'
  created_at timestamptz
```

---

## Task 1: Apply DB Schema + Add Types

**Files:**
- Create: `supabase/migrations/002_plan3_schema.sql`
- Modify: `src/types/game.ts`

- [ ] **Step 1: Create migration file**

Create `supabase/migrations/002_plan3_schema.sql`:

```sql
-- Student memories (what Adeline knows about each kid)
create table if not exists public.aw_student_memories (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references public.aw_student_profiles(id) on delete cascade not null,
  key text not null,
  value text not null,
  updated_at timestamptz default now() not null,
  unique(student_id, key)
);

-- Life Map entries (logged real-world activities)
create table if not exists public.aw_life_map_entries (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references public.aw_student_profiles(id) on delete cascade not null,
  description text not null,
  tracks text[] not null default '{}',
  xp_awarded integer not null default 0,
  coins_awarded integer not null default 0,
  source text not null default 'chat_log',
  created_at timestamptz default now() not null
);

-- Season pass progress
create table if not exists public.aw_season_pass (
  id uuid default gen_random_uuid() primary key,
  student_id uuid references public.aw_student_profiles(id) on delete cascade not null unique,
  season integer not null default 1,
  claimed_tiers integer[] not null default '{}',
  created_at timestamptz default now() not null
);

-- RLS
alter table public.aw_student_memories enable row level security;
alter table public.aw_life_map_entries enable row level security;
alter table public.aw_season_pass enable row level security;

create policy "aw_memories_parent" on public.aw_student_memories for all
  using (student_id in (select id from public.aw_student_profiles where parent_id = auth.uid()));

create policy "aw_lifemap_parent" on public.aw_life_map_entries for all
  using (student_id in (select id from public.aw_student_profiles where parent_id = auth.uid()));

create policy "aw_season_parent" on public.aw_season_pass for all
  using (student_id in (select id from public.aw_student_profiles where parent_id = auth.uid()));
```

- [ ] **Step 2: Apply via Supabase MCP**

Use the Supabase MCP tool to apply the migration to project `gyxowttfwqbajoapfebf`. If the MCP tool is not available, paste the SQL into the Supabase SQL editor at the project dashboard.

- [ ] **Step 3: Add types to `src/types/game.ts`**

Append to the bottom of the existing file:

```typescript
export type Track =
  | 'CREATION_SCIENCE'
  | 'HEALTH_NATUROPATHY'
  | 'HOMESTEADING'
  | 'GOVERNMENT_ECONOMICS'
  | 'JUSTICE_CHANGEMAKING'
  | 'DISCIPLESHIP'
  | 'TRUTH_HISTORY'
  | 'ENGLISH_LITERATURE'
  | 'APPLIED_MATHEMATICS'
  | 'CREATIVE_ECONOMY'

export const TRACK_LABELS: Record<Track, string> = {
  CREATION_SCIENCE:    '🔬 Creation Science',
  HEALTH_NATUROPATHY:  '🌿 Health & Naturopathy',
  HOMESTEADING:        '🌾 Homesteading',
  GOVERNMENT_ECONOMICS:'⚖️ Government & Economics',
  JUSTICE_CHANGEMAKING:'✊ Justice & Changemaking',
  DISCIPLESHIP:        '✝️ Discipleship',
  TRUTH_HISTORY:       '📜 Truth & History',
  ENGLISH_LITERATURE:  '📖 English & Literature',
  APPLIED_MATHEMATICS: '⛏️ Applied Mathematics',
  CREATIVE_ECONOMY:    '🎨 Creative Economy',
}

export const TRACK_COLORS: Record<Track, string> = {
  CREATION_SCIENCE:    '#0e7490',
  HEALTH_NATUROPATHY:  '#16a34a',
  HOMESTEADING:        '#65a30d',
  GOVERNMENT_ECONOMICS:'#7c3aed',
  JUSTICE_CHANGEMAKING:'#dc2626',
  DISCIPLESHIP:        '#d97706',
  TRUTH_HISTORY:       '#92400e',
  ENGLISH_LITERATURE:  '#be185d',
  APPLIED_MATHEMATICS: '#1e3a5f',
  CREATIVE_ECONOMY:    '#c026d3',
}

export interface LifeMapEntry {
  id: string
  student_id: string
  description: string
  tracks: Track[]
  xp_awarded: number
  coins_awarded: number
  source: 'chat_log' | 'room_mission' | 'parent_log'
  created_at: string
}

export interface StudentMemory {
  id: string
  student_id: string
  key: string
  value: string
  updated_at: string
}

export interface SeasonTier {
  tier: number
  xpRequired: number
  reward: string
  rewardType: 'adecoin' | 'avatar_item' | 'cosmetic'
  rewardAmount?: number
}

export const SEASON_TIERS: SeasonTier[] = [
  { tier: 1,  xpRequired: 0,    reward: '50 AdeCoins',        rewardType: 'adecoin',     rewardAmount: 50 },
  { tier: 2,  xpRequired: 100,  reward: 'Red Star Hat',        rewardType: 'avatar_item' },
  { tier: 3,  xpRequired: 250,  reward: '100 AdeCoins',       rewardType: 'adecoin',     rewardAmount: 100 },
  { tier: 4,  xpRequired: 500,  reward: 'Golden Crown',        rewardType: 'avatar_item' },
  { tier: 5,  xpRequired: 800,  reward: '200 AdeCoins',       rewardType: 'adecoin',     rewardAmount: 200 },
  { tier: 6,  xpRequired: 1200, reward: 'Rainbow Bow',         rewardType: 'avatar_item' },
  { tier: 7,  xpRequired: 1700, reward: '500 AdeCoins',       rewardType: 'adecoin',     rewardAmount: 500 },
  { tier: 8,  xpRequired: 2300, reward: 'Adeline\'s Pendant',  rewardType: 'cosmetic' },
  { tier: 9,  xpRequired: 3000, reward: '1000 AdeCoins',      rewardType: 'adecoin',     rewardAmount: 1000 },
  { tier: 10, xpRequired: 4000, reward: 'World Builder Title', rewardType: 'cosmetic' },
]
```

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/002_plan3_schema.sql src/types/game.ts
git commit -m "feat: add Plan 3 DB schema and types - LifeMapEntry, Track, SeasonTier"
```

---

## Task 2: Memory Service + Life Map Service

**Files:**
- Create: `src/lib/memoryService.ts`
- Create: `src/lib/lifeMapService.ts`

- [ ] **Step 1: Create `src/lib/memoryService.ts`**

```typescript
import { supabase } from './supabase'
import { StudentMemory } from '../types/game'

export async function getMemories(studentId: string): Promise<StudentMemory[]> {
  const { data } = await supabase
    .from('aw_student_memories')
    .select('*')
    .eq('student_id', studentId)
    .order('updated_at', { ascending: false })
  return data ?? []
}

export async function upsertMemory(studentId: string, key: string, value: string): Promise<void> {
  await supabase
    .from('aw_student_memories')
    .upsert({ student_id: studentId, key, value, updated_at: new Date().toISOString() },
             { onConflict: 'student_id,key' })
}

export async function buildMemoryContext(studentId: string): Promise<string> {
  const memories = await getMemories(studentId)
  if (memories.length === 0) return ''
  return '\n\nWhat you know about this student:\n' +
    memories.map(m => `- ${m.key}: ${m.value}`).join('\n')
}
```

- [ ] **Step 2: Create `src/lib/lifeMapService.ts`**

```typescript
import { supabase } from './supabase'
import { LifeMapEntry, Track } from '../types/game'

export async function logActivity(
  studentId: string,
  description: string,
  tracks: Track[],
  xpAwarded: number,
  coinsAwarded: number,
  source: 'chat_log' | 'room_mission' | 'parent_log' = 'chat_log'
): Promise<LifeMapEntry | null> {
  const { data, error } = await supabase
    .from('aw_life_map_entries')
    .insert({ student_id: studentId, description, tracks, xp_awarded: xpAwarded, coins_awarded: coinsAwarded, source })
    .select()
    .single()
  if (error) { console.error('lifeMapService.logActivity', error); return null }
  return data
}

export async function getLifeMap(studentId: string): Promise<LifeMapEntry[]> {
  const { data } = await supabase
    .from('aw_life_map_entries')
    .select('*')
    .eq('student_id', studentId)
    .order('created_at', { ascending: false })
  return (data ?? []) as LifeMapEntry[]
}

export async function getLifeMapByTrack(studentId: string): Promise<Partial<Record<Track, LifeMapEntry[]>>> {
  const entries = await getLifeMap(studentId)
  const byTrack: Partial<Record<Track, LifeMapEntry[]>> = {}
  for (const entry of entries) {
    for (const track of entry.tracks) {
      if (!byTrack[track]) byTrack[track] = []
      byTrack[track]!.push(entry)
    }
  }
  return byTrack
}
```

- [ ] **Step 3: Commit**

```bash
git add src/lib/memoryService.ts src/lib/lifeMapService.ts
git commit -m "feat: add memory service and life map service"
```

---

## Task 3: Adeline Chat (Main Screen)

**Files:**
- Create: `src/components/chat/ActivityConfirm.tsx`
- Create: `src/components/chat/AdelineChat.tsx`

This is the most important component. Adeline is the main UI. She talks to kids, detects real-life activities, offers to log them, and launches rooms.

- [ ] **Step 1: Create `src/components/chat/ActivityConfirm.tsx`**

```typescript
import { Track, TRACK_LABELS, TRACK_COLORS } from '../../types/game'

export interface PendingActivity {
  description: string
  tracks: Track[]
  xpReward: number
  coinReward: number
}

interface Props {
  activity: PendingActivity
  onConfirm: () => void
  onDismiss: () => void
}

export default function ActivityConfirm({ activity, onConfirm, onDismiss }: Props) {
  return (
    <div className="mx-4 mb-3 bg-amber-50 border-2 border-amber-400 rounded-2xl p-4 space-y-3">
      <div className="flex items-start gap-3">
        <span className="text-2xl">📋</span>
        <div className="flex-1">
          <p className="text-amber-900 font-bold text-sm">Log this to your Life Map?</p>
          <p className="text-amber-800 text-sm mt-1">"{activity.description}"</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {activity.tracks.map(track => (
          <span
            key={track}
            className="text-xs font-semibold px-2 py-1 rounded-full text-white"
            style={{ backgroundColor: TRACK_COLORS[track] }}
          >
            {TRACK_LABELS[track]}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-amber-700">
          +{activity.xpReward} XP · +{activity.coinReward} AdeCoins
        </span>
        <div className="flex gap-2">
          <button
            onClick={onDismiss}
            className="px-3 py-1.5 text-xs text-amber-700 hover:bg-amber-100 rounded-lg transition-all"
          >
            Skip
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-1.5 text-xs bg-amber-500 hover:bg-amber-400 text-white font-bold rounded-lg transition-all"
          >
            Yes, log it! ✓
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `src/components/chat/AdelineChat.tsx`**

This component handles the full chat conversation. It builds a rich system prompt with student memory, detects activities in Adeline's responses, and surfaces the ActivityConfirm banner.

```typescript
import { useState, useEffect, useRef } from 'react'
import { StudentMemory, Track, LifeMapEntry } from '../../types/game'
import ActivityConfirm, { PendingActivity } from './ActivityConfirm'
import { buildMemoryContext, upsertMemory } from '../../lib/memoryService'
import { logActivity } from '../../lib/lifeMapService'

interface ChatMessage {
  id: string
  text: string
  fromAdeline: boolean
  timestamp: string
}

interface Props {
  studentId: string | null     // null = guest
  playerName: string
  currentXP: number
  onXpEarned: (amount: number) => void
  onCoinsEarned: (amount: number) => void
  onLifeMapEntry: (entry: LifeMapEntry) => void
}

// Adeline's full system prompt including persona from adeline.config.toml
const ADELINE_SYSTEM_PROMPT = `You are Adeline — a warm, sharp-witted educational mentor for Christian homeschool families.

You believe: Knowledge without love is nothing. Every child has a calling.

Your persona rules:
- Ask questions and REMEMBER what kids tell you. Build a picture of who they are.
- Every activity must have PURPOSE — it helps someone, solves a problem, or creates something real.
- Always ask "Who profits?" when teaching history, civics, or economics. Follow the money.
- Affirm each student's unique worth and calling.
- For history: never sanitize. Show what really happened. Primary sources when you can.
- For science: connect to the natural world, farming, animals, how things actually work.
- Mathematics lives in real life: budgets, land measurement, recipes, building plans.
- A student's portfolio is their ACCOMPLISHMENTS, not their assignments.

ACTIVITY DETECTION — CRITICAL:
When a student mentions something real they did (canned tomatoes, read a book, helped build something, practiced math, took care of animals, researched something, wrote something, cooked a meal, etc.), you MUST:
1. Ask follow-up questions to understand the scope and learning
2. Then end your message with a special JSON block on its own line:

ADELINE_LOG:{"description":"...what they did in their own words...","tracks":["HOMESTEADING","APPLIED_MATHEMATICS"],"xpReward":50,"coinReward":12}

Valid track values: CREATION_SCIENCE, HEALTH_NATUROPATHY, HOMESTEADING, GOVERNMENT_ECONOMICS, JUSTICE_CHANGEMAKING, DISCIPLESHIP, TRUTH_HISTORY, ENGLISH_LITERATURE, APPLIED_MATHEMATICS, CREATIVE_ECONOMY

Choose tracks that actually match what they did. XP reward should reflect depth and effort (20-100). Be generous but honest.

Do NOT output the ADELINE_LOG block for casual chat, greetings, questions, or anything not related to a real learning activity. Only use it when a student describes something they actually DID.`

function parseAdelineResponse(reply: string): { message: string; activity: PendingActivity | null } {
  const logMatch = reply.match(/ADELINE_LOG:(\{.*?\})/s)
  if (!logMatch) return { message: reply, activity: null }

  const message = reply.replace(/ADELINE_LOG:\{.*?\}/s, '').trim()
  try {
    const parsed = JSON.parse(logMatch[1])
    return {
      message,
      activity: {
        description: parsed.description,
        tracks: parsed.tracks as Track[],
        xpReward: parsed.xpReward ?? 30,
        coinReward: parsed.coinReward ?? 8,
      }
    }
  } catch {
    return { message: reply, activity: null }
  }
}

export default function AdelineChat({ studentId, playerName, currentXP, onXpEarned, onCoinsEarned, onLifeMapEntry }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingActivity, setPendingActivity] = useState<PendingActivity | null>(null)
  const [memoryContext, setMemoryContext] = useState('')
  const [initialized, setInitialized] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pendingActivity])

  useEffect(() => {
    initChat()
  }, [studentId])

  async function initChat() {
    // Load memory context for logged-in students
    let ctx = ''
    if (studentId) {
      ctx = await buildMemoryContext(studentId)
      setMemoryContext(ctx)
    }

    // Adeline's opening greeting
    const hour = new Date().getHours()
    const timeGreet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

    setLoading(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `[SYSTEM: This is the student's greeting message. Greet them warmly as ${playerName}. Ask them what they've been up to, what they're curious about, or what they worked on today. Keep it short — 2-3 sentences. Time of day: ${timeGreet}.${ctx}]`,
          history: [],
          systemPrompt: ADELINE_SYSTEM_PROMPT
        })
      })
      const data = await res.json()
      const { message } = parseAdelineResponse(data.reply)
      setMessages([{
        id: '0',
        text: message,
        fromAdeline: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    } catch {
      setMessages([{
        id: '0',
        text: `${timeGreet}, ${playerName}! I'm here and ready to learn with you. What have you been up to today?`,
        fromAdeline: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    } finally {
      setLoading(false)
      setInitialized(true)
    }
  }

  async function sendMessage() {
    if (!input.trim() || loading) return
    const userText = input.trim()
    setInput('')

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      text: userText,
      fromAdeline: false,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    // Build conversation history for context (last 10 messages)
    const history = messages.slice(-10).map(m => ({
      isFromUser: !m.fromAdeline,
      text: m.text
    }))

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          history,
          systemPrompt: ADELINE_SYSTEM_PROMPT + memoryContext
        })
      })
      const data = await res.json()
      const { message, activity } = parseAdelineResponse(data.reply)

      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        text: message,
        fromAdeline: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])

      if (activity) setPendingActivity(activity)

      // Detect interests from conversation and save to memory
      if (studentId && userText.length > 20) {
        detectAndSaveMemory(studentId, userText)
      }
    } catch {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        text: "My thoughts got a little tangled — try again!",
        fromAdeline: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    } finally {
      setLoading(false)
    }
  }

  async function detectAndSaveMemory(sId: string, text: string) {
    // Simple keyword detection for memory — non-blocking
    const lower = text.toLowerCase()
    if (lower.includes('chicken') || lower.includes('hen') || lower.includes('egg'))
      upsertMemory(sId, 'homestead_animals', 'chickens/hens')
    if (lower.includes('sheep') || lower.includes('wool'))
      upsertMemory(sId, 'homestead_animals', 'sheep')
    if (lower.includes('horse') || lower.includes('equestrian'))
      upsertMemory(sId, 'homestead_animals', 'horses')
    if (lower.includes('garden') || lower.includes('plant') || lower.includes('tomato') || lower.includes('crop'))
      upsertMemory(sId, 'interests', 'gardening/farming')
    if (lower.includes('code') || lower.includes('program') || lower.includes('app'))
      upsertMemory(sId, 'interests', 'coding/programming')
    if (lower.includes('read') || lower.includes('book'))
      upsertMemory(sId, 'interests', 'reading')
    if (lower.includes('build') || lower.includes('built') || lower.includes('wood'))
      upsertMemory(sId, 'interests', 'building/woodworking')
  }

  async function confirmActivity() {
    if (!pendingActivity) return
    const xp = pendingActivity.xpReward
    const coins = pendingActivity.coinReward
    onXpEarned(xp)
    onCoinsEarned(coins)

    if (studentId) {
      const entry = await logActivity(studentId, pendingActivity.description, pendingActivity.tracks, xp, coins, 'chat_log')
      if (entry) onLifeMapEntry(entry)
    }

    setPendingActivity(null)
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      text: `Logged! That goes right onto your Life Map. +${xp} XP and +${coins} AdeCoins for you. Keep it up — real work counts.`,
      fromAdeline: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }])
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!initialized && (
          <div className="flex justify-center py-8">
            <div className="w-8 h-8 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`flex gap-3 max-w-2xl ${msg.fromAdeline ? '' : 'ml-auto flex-row-reverse'}`}>
            {msg.fromAdeline && (
              <div className="w-9 h-9 rounded-full overflow-hidden border-2 border-amber-400 flex-shrink-0 mt-1">
                <img src="/adeline_portrait.png" alt="Adeline" className="w-full h-full object-cover"
                  onError={e => { e.currentTarget.style.display='none'; e.currentTarget.parentElement!.style.backgroundColor='#D97706'; e.currentTarget.parentElement!.innerHTML='<span style="color:white;font-size:16px;display:flex;align-items:center;justify-content:center;height:100%">A</span>' }} />
              </div>
            )}
            <div>
              <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm max-w-sm ${
                msg.fromAdeline
                  ? 'bg-white text-slate-800 border border-amber-100 rounded-tl-sm'
                  : 'bg-amber-600 text-white rounded-tr-sm'
              }`}>
                {msg.text}
              </div>
              <p className={`text-[10px] text-slate-400 mt-1 px-1 ${msg.fromAdeline ? '' : 'text-right'}`}>
                {msg.timestamp}
              </p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 max-w-2xl">
            <div className="w-9 h-9 rounded-full bg-amber-600 flex-shrink-0 flex items-center justify-center mt-1">
              <span className="text-white text-xs font-bold">A</span>
            </div>
            <div className="bg-white border border-amber-100 rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1 items-center shadow-sm">
              <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Activity confirm banner */}
      {pendingActivity && (
        <ActivityConfirm
          activity={pendingActivity}
          onConfirm={confirmActivity}
          onDismiss={() => setPendingActivity(null)}
        />
      )}

      {/* Input */}
      <div className="p-4 bg-white border-t border-amber-100">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder="Tell Adeline what you've been up to..."
            className="flex-1 px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 text-sm bg-slate-50/50"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="px-5 py-3 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold rounded-xl transition-all text-sm"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/chat/ActivityConfirm.tsx src/components/chat/AdelineChat.tsx
git commit -m "feat: add AdelineChat with activity detection, memory, and life map logging"
```

---

## Task 4: RoomMission Component (Open-Ended Projects)

**Files:**
- Create: `src/components/rooms/RoomMission.tsx`

This replaces the quiz pattern in rooms. Adeline assigns a real project, kid responds in open text, Adeline evaluates and logs to Life Map.

- [ ] **Step 1: Create `src/components/rooms/RoomMission.tsx`**

```typescript
import { useState, useEffect } from 'react'
import { Track } from '../../types/game'

interface Props {
  roomId: string
  roomLabel: string
  roomEmoji: string
  roomTracks: Track[]
  playerName: string
  systemContext: string  // extra context for Gemini (e.g. "This is a homesteading mission")
  onComplete: (description: string, tracks: Track[], xp: number, coins: number) => void
  onBack: () => void
}

interface Mission {
  title: string
  description: string    // what Adeline wants the student to do
  prompt: string         // what the student is asked to write/respond
  xpReward: number
  coinReward: number
}

export default function RoomMission({ roomId, roomLabel, roomEmoji, roomTracks, playerName, systemContext, onComplete, onBack }: Props) {
  const [mission, setMission] = useState<Mission | null>(null)
  const [response, setResponse] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [evaluating, setEvaluating] = useState(false)
  const [completed, setCompleted] = useState(false)

  useEffect(() => { loadMission() }, [])

  async function loadMission() {
    setLoading(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create a real-world mission for a homeschool student in the ${roomLabel} subject area. ${systemContext}

The mission should:
- Be something they can actually DO or THINK THROUGH right now
- Require a written response (not multiple choice)
- Connect to real life, homesteading, farming, nature, history, or their community
- Be completable in 5-15 minutes
- Have a clear prompt they respond to

Respond ONLY with valid JSON:
{"title":"...","description":"...what they'll do, 2-3 sentences...","prompt":"...the specific question or task they respond to...","xpReward":60,"coinReward":15}`,
          history: [],
        })
      })
      const data = await res.json()
      const parsed = JSON.parse(data.reply.replace(/```json|```/g, '').trim())
      if (parsed.title && parsed.prompt) setMission(parsed)
      else throw new Error('bad format')
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

Evaluate their response in 2-3 sentences. Be encouraging but honest. If they put in real effort, affirm it. If they were vague, nudge them to go deeper next time. End with one specific thing they did well.`,
          history: [],
        })
      })
      const data = await res.json()
      setFeedback(data.reply)
      setCompleted(true)

      const description = `${mission.title}: ${response.slice(0, 120)}${response.length > 120 ? '...' : ''}`
      onComplete(description, roomTracks, mission.xpReward, mission.coinReward)
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
          <p className="text-white/50 text-xs">Real work, real learning</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-5 overflow-y-auto">
        {loading ? (
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-white/60 text-sm">Adeline is preparing your mission...</p>
          </div>
        ) : mission && !completed ? (
          <>
            <div className="w-full max-w-lg bg-white/10 rounded-2xl p-5 border border-white/20 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-amber-400 text-xs font-bold uppercase tracking-wider">Mission</span>
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

            <div className="text-center">
              <p className="text-white/40 text-xs">+{mission.xpReward} XP · +{mission.coinReward} AdeCoins on completion · Logged to Life Map</p>
            </div>
          </>
        ) : completed && feedback ? (
          <div className="w-full max-w-lg space-y-5">
            <div className="bg-emerald-500/20 border border-emerald-400 rounded-2xl p-5 space-y-3">
              <p className="text-4xl text-center">🎉</p>
              <p className="text-emerald-300 font-bold text-center">Mission Complete!</p>
              <p className="text-white/80 text-sm leading-relaxed">{feedback}</p>
              <p className="text-amber-300 text-xs text-center">+{mission?.xpReward} XP · +{mission?.coinReward} AdeCoins · Added to Life Map</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={onBack}
                className="flex-1 py-3 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-xl"
              >
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
    math_mines: {
      title: 'Budget Your Garden',
      description: 'Plan a small vegetable garden and figure out what it would cost to plant it.',
      prompt: 'Pick 3 vegetables to grow. Estimate how many seeds or seedlings you need and what they might cost. How much space do you need? Write out your plan and calculations.',
      xpReward: 60,
      coinReward: 15
    },
    story_forest: {
      title: 'Tell Your Story',
      description: 'Every family has stories worth preserving. Think about something that happened in your family or community.',
      prompt: 'Write 3-5 sentences about a real event in your family\'s history or something that happened recently. Include who was there, what happened, and why it matters.',
      xpReward: 60,
      coinReward: 15
    },
    science_lab: {
      title: 'Kitchen Science Observation',
      description: 'Science is everywhere in your home. Pick something you can observe or test right now.',
      prompt: 'Choose one of these and describe what you observe: (1) What happens when you mix baking soda and vinegar? (2) How does bread dough rise? (3) What do you notice about how water moves through soil or sand? Write what you observe and why you think it happens.',
      xpReward: 60,
      coinReward: 15
    },
    homestead_farm: {
      title: 'Animal Care Log',
      description: 'Taking care of animals is real science, math, and stewardship all at once.',
      prompt: 'Think about an animal your family cares for (or would like to care for). What does it eat? How much? How do you keep it healthy? What does it give back to the family? Write a short care guide for it.',
      xpReward: 65,
      coinReward: 18
    },
    truth_archive: {
      title: 'Follow the Money',
      description: 'Behind almost every historical event, there is someone who profits. Let\'s find them.',
      prompt: 'Pick one of these events: (1) Why did Columbus sail west? (2) Why did factories replace farms in the 1800s? (3) Why do food companies add sugar to almost everything? Write 3-5 sentences about who benefited and how.',
      xpReward: 70,
      coinReward: 18
    },
  }
  return missions[roomId] ?? missions.math_mines
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/rooms/RoomMission.tsx
git commit -m "feat: add RoomMission component for open-ended project missions"
```

---

## Task 5: Life Map Display

**Files:**
- Create: `src/components/life-map/LifeMap.tsx`

- [ ] **Step 1: Create `src/components/life-map/LifeMap.tsx`**

```typescript
import { useState, useEffect } from 'react'
import { LifeMapEntry, Track, TRACK_LABELS, TRACK_COLORS } from '../../types/game'
import { getLifeMapByTrack } from '../../lib/lifeMapService'

interface Props {
  studentId: string | null
  localEntries: LifeMapEntry[]   // guest entries or newly added entries before DB refresh
  onClose: () => void
}

const ALL_TRACKS: Track[] = [
  'CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING',
  'GOVERNMENT_ECONOMICS', 'JUSTICE_CHANGEMAKING', 'DISCIPLESHIP',
  'TRUTH_HISTORY', 'ENGLISH_LITERATURE', 'APPLIED_MATHEMATICS', 'CREATIVE_ECONOMY'
]

export default function LifeMap({ studentId, localEntries, onClose }: Props) {
  const [byTrack, setByTrack] = useState<Partial<Record<Track, LifeMapEntry[]>>>({})
  const [loading, setLoading] = useState(true)
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null)

  useEffect(() => {
    loadEntries()
  }, [studentId, localEntries])

  async function loadEntries() {
    setLoading(true)
    let entries: Partial<Record<Track, LifeMapEntry[]>> = {}

    if (studentId) {
      entries = await getLifeMapByTrack(studentId)
    }

    // Merge local entries (for guests or freshly logged items)
    for (const entry of localEntries) {
      for (const track of entry.tracks) {
        if (!entries[track]) entries[track] = []
        if (!entries[track]!.find(e => e.id === entry.id)) {
          entries[track]!.unshift(entry)
        }
      }
    }

    setByTrack(entries)
    setLoading(false)
  }

  const totalEntries = Object.values(byTrack).flat().filter((v, i, a) => a.findIndex(e => e.id === v.id) === i).length
  const tracksActive = ALL_TRACKS.filter(t => (byTrack[t]?.length ?? 0) > 0).length

  return (
    <div className="fixed inset-0 bg-slate-900/95 z-50 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div>
          <h2 className="text-white font-bold text-xl font-serif">✨ Your Life Map</h2>
          <p className="text-white/50 text-xs mt-0.5">{totalEntries} accomplishments · {tracksActive}/10 tracks explored</p>
        </div>
        <button onClick={onClose} className="text-white/60 hover:text-white text-2xl px-2">✕</button>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4">
          {totalEntries === 0 ? (
            <div className="text-center py-16 space-y-4">
              <p className="text-5xl">🗺️</p>
              <p className="text-white font-bold text-lg">Your Life Map is empty</p>
              <p className="text-white/50 text-sm max-w-xs mx-auto">
                Tell Adeline what you've been doing — canning, building, reading, farming — and she'll add it here.
              </p>
            </div>
          ) : (
            <>
              {/* Track grid */}
              <div className="grid grid-cols-2 gap-3 mb-6">
                {ALL_TRACKS.map(track => {
                  const entries = byTrack[track] ?? []
                  const active = entries.length > 0
                  return (
                    <button
                      key={track}
                      onClick={() => setSelectedTrack(active ? track : null)}
                      className={`rounded-2xl p-3 text-left transition-all border ${
                        active
                          ? 'border-white/20 hover:border-white/40 hover:scale-[1.02]'
                          : 'border-white/5 opacity-30'
                      }`}
                      style={{ backgroundColor: active ? `${TRACK_COLORS[track]}33` : 'rgba(255,255,255,0.03)' }}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-bold text-white">{TRACK_LABELS[track]}</span>
                        {active && (
                          <span
                            className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                            style={{ backgroundColor: TRACK_COLORS[track] }}
                          >
                            {entries.length}
                          </span>
                        )}
                      </div>
                      {active && (
                        <p className="text-white/60 text-xs truncate">{entries[0].description}</p>
                      )}
                    </button>
                  )
                })}
              </div>

              {/* Detail panel for selected track */}
              {selectedTrack && (byTrack[selectedTrack]?.length ?? 0) > 0 && (
                <div className="bg-white/5 rounded-2xl p-4 border border-white/10 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-white font-bold">{TRACK_LABELS[selectedTrack]}</h3>
                    <button onClick={() => setSelectedTrack(null)} className="text-white/40 text-sm">✕</button>
                  </div>
                  <div className="space-y-2">
                    {byTrack[selectedTrack]!.map(entry => (
                      <div key={entry.id} className="bg-white/5 rounded-xl p-3 border border-white/10">
                        <p className="text-white/90 text-sm">{entry.description}</p>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-white/40 text-xs">
                            {new Date(entry.created_at).toLocaleDateString()}
                          </span>
                          <span className="text-amber-300 text-xs">+{entry.xp_awarded} XP</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/life-map/LifeMap.tsx
git commit -m "feat: add LifeMap display with track grid and entry detail"
```

---

## Task 6: Season Pass

**Files:**
- Create: `src/components/season-pass/SeasonPass.tsx`

- [ ] **Step 1: Create `src/components/season-pass/SeasonPass.tsx`**

```typescript
import { SEASON_TIERS } from '../../types/game'

interface Props {
  currentXP: number
  claimedTiers: number[]
  onClaimTier: (tier: number, coinsToAdd: number) => void
  onClose: () => void
}

export default function SeasonPass({ currentXP, claimedTiers, onClaimTier, onClose }: Props) {
  const currentTier = SEASON_TIERS.filter(t => currentXP >= t.xpRequired).length

  return (
    <div className="fixed inset-0 bg-slate-900/95 z-50 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div>
          <h2 className="text-white font-bold text-xl font-serif">🌟 Season Pass</h2>
          <p className="text-white/50 text-xs mt-0.5">Season 1 · {currentXP} XP total · Tier {currentTier}/{SEASON_TIERS.length}</p>
        </div>
        <button onClick={onClose} className="text-white/60 hover:text-white text-2xl px-2">✕</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {SEASON_TIERS.map((tier, i) => {
          const unlocked = currentXP >= tier.xpRequired
          const claimed = claimedTiers.includes(tier.tier)
          const canClaim = unlocked && !claimed

          return (
            <div
              key={tier.tier}
              className={`rounded-2xl p-4 border transition-all ${
                unlocked
                  ? 'bg-white/10 border-white/20'
                  : 'bg-white/3 border-white/5 opacity-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                      unlocked ? 'bg-amber-500 text-white' : 'bg-white/10 text-white/30'
                    }`}
                  >
                    {claimed ? '✓' : tier.tier}
                  </div>
                  <div>
                    <p className={`font-semibold text-sm ${unlocked ? 'text-white' : 'text-white/30'}`}>
                      {tier.reward}
                    </p>
                    <p className="text-white/40 text-xs">{tier.xpRequired} XP required</p>
                  </div>
                </div>

                {canClaim ? (
                  <button
                    onClick={() => onClaimTier(tier.tier, tier.rewardType === 'adecoin' ? (tier.rewardAmount ?? 0) : 0)}
                    className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-white text-xs font-bold rounded-xl transition-all animate-pulse"
                  >
                    Claim!
                  </button>
                ) : claimed ? (
                  <span className="text-emerald-400 text-xs font-bold">Claimed ✓</span>
                ) : (
                  <span className="text-white/20 text-xs">
                    {tier.xpRequired - currentXP} XP away
                  </span>
                )}
              </div>

              {/* XP progress bar for next unclaimed tier */}
              {!unlocked && i === currentTier && (
                <div className="mt-3">
                  <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-400 rounded-full transition-all"
                      style={{ width: `${Math.round(currentXP / tier.xpRequired * 100)}%` }}
                    />
                  </div>
                  <p className="text-white/40 text-xs mt-1 text-right">
                    {currentXP} / {tier.xpRequired} XP
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/season-pass/SeasonPass.tsx
git commit -m "feat: add Season Pass UI with tier unlocks and XP progress"
```

---

## Task 7: Parent Dashboard

**Files:**
- Create: `src/pages/ParentDashboard.tsx`
- Modify: `src/App.tsx` — add `/parent-dashboard` route

- [ ] **Step 1: Create `src/pages/ParentDashboard.tsx`**

```typescript
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { supabase } from '../lib/supabase'
import { LifeMapEntry, TRACK_LABELS, TRACK_COLORS, Track } from '../types/game'
import { ArrowLeft, Users, BookOpen, Clock, Star } from 'lucide-react'

interface ChildStats {
  childId: string
  displayName: string
  username: string
  xp: number
  adeCoins: number
  avatarApproved: boolean
  usernameApproved: boolean
  recentEntries: LifeMapEntry[]
  totalEntries: number
}

export default function ParentDashboard() {
  const { children, parentAccount, signOut } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState<ChildStats[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedChild, setSelectedChild] = useState<ChildStats | null>(null)
  const [approvingId, setApprovingId] = useState<string | null>(null)

  useEffect(() => {
    if (children.length > 0) loadStats()
    else setLoading(false)
  }, [children])

  async function loadStats() {
    setLoading(true)
    const results: ChildStats[] = []
    for (const child of children) {
      const { data: entries } = await supabase
        .from('aw_life_map_entries')
        .select('*')
        .eq('student_id', child.id)
        .order('created_at', { ascending: false })
        .limit(5)

      const { count } = await supabase
        .from('aw_life_map_entries')
        .select('*', { count: 'exact', head: true })
        .eq('student_id', child.id)

      results.push({
        childId: child.id,
        displayName: child.display_name,
        username: child.username,
        xp: child.xp,
        adeCoins: child.ade_coins,
        avatarApproved: child.avatar_approved,
        usernameApproved: child.username_approved,
        recentEntries: (entries ?? []) as LifeMapEntry[],
        totalEntries: count ?? 0
      })
    }
    setStats(results)
    setLoading(false)
  }

  async function approveUsername(childId: string) {
    setApprovingId(childId)
    await supabase.from('aw_student_profiles').update({ username_approved: true }).eq('id', childId)
    await loadStats()
    setApprovingId(null)
  }

  async function approveAvatar(childId: string) {
    setApprovingId(childId)
    await supabase.from('aw_student_profiles').update({ avatar_approved: true }).eq('id', childId)
    await loadStats()
    setApprovingId(null)
  }

  const pendingApprovals = stats.filter(s => !s.usernameApproved || !s.avatarApproved)

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')} className="p-2 rounded-lg hover:bg-slate-100 text-slate-500">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="font-bold text-slate-800">Parent Dashboard</h1>
            <p className="text-xs text-slate-500">Hi {parentAccount?.display_name}</p>
          </div>
        </div>
        <button
          onClick={() => { signOut(); navigate('/') }}
          className="text-xs text-slate-400 hover:text-slate-600 px-3 py-1.5 rounded-lg hover:bg-slate-100"
        >
          Sign Out
        </button>
      </div>

      <div className="max-w-2xl mx-auto p-4 space-y-6">

        {/* Pending approvals */}
        {pendingApprovals.length > 0 && (
          <div className="bg-amber-50 border-2 border-amber-400 rounded-2xl p-4 space-y-3">
            <h2 className="font-bold text-amber-900 flex items-center gap-2">
              <Star className="w-4 h-4" /> Action Needed
            </h2>
            {pendingApprovals.map(s => (
              <div key={s.childId} className="bg-white rounded-xl p-3 space-y-2">
                <p className="font-semibold text-slate-800 text-sm">{s.displayName}</p>
                <div className="flex flex-wrap gap-2">
                  {!s.usernameApproved && (
                    <button
                      onClick={() => approveUsername(s.childId)}
                      disabled={approvingId === s.childId}
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-white text-xs font-bold rounded-lg"
                    >
                      Approve username: @{s.username}
                    </button>
                  )}
                  {!s.avatarApproved && (
                    <button
                      onClick={() => approveAvatar(s.childId)}
                      disabled={approvingId === s.childId}
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-white text-xs font-bold rounded-lg"
                    >
                      Approve avatar
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Kids overview */}
        <div>
          <h2 className="font-bold text-slate-700 flex items-center gap-2 mb-3">
            <Users className="w-4 h-4" /> Your Kids
          </h2>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-8 h-8 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : stats.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-8">No kids added yet.</p>
          ) : (
            <div className="space-y-3">
              {stats.map(s => (
                <button
                  key={s.childId}
                  onClick={() => setSelectedChild(selectedChild?.childId === s.childId ? null : s)}
                  className="w-full bg-white rounded-2xl p-4 border border-slate-200 text-left hover:border-amber-300 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-bold text-slate-800">{s.displayName}</p>
                      <p className="text-xs text-slate-500">@{s.username}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-amber-600 font-bold text-sm">{s.xp} XP</p>
                      <p className="text-slate-500 text-xs">{s.adeCoins} AdeCoins</p>
                    </div>
                  </div>

                  <div className="flex gap-4 mt-3 pt-3 border-t border-slate-100">
                    <div className="flex items-center gap-1 text-xs text-slate-500">
                      <BookOpen className="w-3 h-3" />
                      <span>{s.totalEntries} activities logged</span>
                    </div>
                    {(!s.usernameApproved || !s.avatarApproved) && (
                      <span className="text-xs text-amber-600 font-semibold">⚠ Needs approval</span>
                    )}
                  </div>

                  {/* Recent activity */}
                  {selectedChild?.childId === s.childId && s.recentEntries.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-100 space-y-2" onClick={e => e.stopPropagation()}>
                      <p className="text-xs font-bold text-slate-600 uppercase tracking-wider">Recent Activity</p>
                      {s.recentEntries.map(entry => (
                        <div key={entry.id} className="bg-slate-50 rounded-xl p-3">
                          <p className="text-slate-700 text-sm">{entry.description}</p>
                          <div className="flex items-center justify-between mt-1">
                            <div className="flex flex-wrap gap-1">
                              {entry.tracks.map(t => (
                                <span
                                  key={t}
                                  className="text-[10px] px-1.5 py-0.5 rounded-full text-white"
                                  style={{ backgroundColor: TRACK_COLORS[t as Track] }}
                                >
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
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add route to `src/App.tsx`**

Add this import at the top:
```typescript
import ParentDashboard from './pages/ParentDashboard'
```

Add this route inside `<Routes>` (before the `*` catch-all):
```typescript
        <Route path="/parent-dashboard" element={
          <RequireParent><ParentDashboard /></RequireParent>
        } />
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/ParentDashboard.tsx src/App.tsx
git commit -m "feat: add Parent Dashboard with activity log, approvals, and child stats"
```

---

## Task 8: Refactor GameShell — Chat-First Layout

**Files:**
- Modify: `src/pages/GameShell.tsx`

This is the biggest change. The main game screen is now: Adeline chat (center) + room launcher sidebar (right side on desktop, bottom drawer on mobile) + Life Map and Season Pass accessible via buttons.

- [ ] **Step 1: Replace `src/pages/GameShell.tsx` entirely**

```typescript
import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AvatarData, RoomId, DEFAULT_AVATAR, LifeMapEntry, SEASON_TIERS, Track } from '../types/game'
import AvatarBuilder from '../components/avatar/AvatarBuilder'
import GameHUD from '../components/hud/GameHUD'
import AdelineChat from '../components/chat/AdelineChat'
import HubWorld from '../components/world/HubWorld'
import LifeMap from '../components/life-map/LifeMap'
import SeasonPass from '../components/season-pass/SeasonPass'
import RoomMission from '../components/rooms/RoomMission'
import MathMines from '../components/rooms/MathMines'
import StoryForest from '../components/rooms/StoryForest'
import ScienceLab from '../components/rooms/ScienceLab'
import HomesteadFarm from '../components/rooms/HomesteadFarm'
import TruthArchive from '../components/rooms/TruthArchive'
import { supabase } from '../lib/supabase'
import { logActivity } from '../lib/lifeMapService'

type GameScreen = 'avatar_builder' | 'chat' | 'hub' | 'room'
type Overlay = 'life_map' | 'season_pass' | null

const ROOM_CONFIG: Record<RoomId, { label: string; emoji: string; tracks: Track[]; context: string }> = {
  math_mines:     { label: 'Math Mines',      emoji: '⛏️', tracks: ['APPLIED_MATHEMATICS'],                     context: 'Focus on real-world math: farming budgets, measurements, building calculations, market pricing.' },
  story_forest:   { label: 'Story Forest',    emoji: '🌲', tracks: ['ENGLISH_LITERATURE'],                      context: 'Focus on reading, writing, storytelling, rhetoric, and comprehension.' },
  science_lab:    { label: 'Science Lab',     emoji: '🔬', tracks: ['CREATION_SCIENCE'],                        context: 'Focus on creation science, nature observation, household experiments, animal biology.' },
  homestead_farm: { label: 'Homestead Farm',  emoji: '🌾', tracks: ['HOMESTEADING', 'APPLIED_MATHEMATICS'],     context: 'Focus on farming, animal husbandry, canning, building, selling at market, off-grid living.' },
  truth_archive:  { label: 'Truth Archive',   emoji: '📜', tracks: ['TRUTH_HISTORY', 'JUSTICE_CHANGEMAKING'],  context: 'Focus on primary source history, follow the money, who profits, real unfiltered events.' },
}

function parseAvatar(data: Record<string, unknown>): AvatarData | null {
  if (!data || !data.skinTone) return null
  return data as unknown as AvatarData
}

export default function GameShell() {
  const { activeChild, guestSession, signOut, parentAccount } = useAuth()
  const navigate = useNavigate()

  const storedAvatar = activeChild?.avatar_data ? parseAvatar(activeChild.avatar_data as Record<string, unknown>) : null
  const guestAvatarRaw = guestSession?.avatarData
  const guestAvatar = guestAvatarRaw && Object.keys(guestAvatarRaw).length > 0
    ? parseAvatar(guestAvatarRaw as Record<string, unknown>) : null
  const hasAvatar = storedAvatar !== null || guestAvatar !== null

  const [screen, setScreen] = useState<GameScreen>(hasAvatar ? 'chat' : 'avatar_builder')
  const [avatarData, setAvatarData] = useState<AvatarData>(storedAvatar ?? guestAvatar ?? DEFAULT_AVATAR)
  const [currentRoom, setCurrentRoom] = useState<RoomId | null>(null)
  const [roomMode, setRoomMode] = useState<'quiz' | 'mission'>('mission')
  const [localXP, setLocalXP] = useState(activeChild?.xp ?? guestSession?.xp ?? 0)
  const [localCoins, setLocalCoins] = useState(activeChild?.ade_coins ?? guestSession?.adeCoins ?? 0)
  const [overlay, setOverlay] = useState<Overlay>(null)
  const [lifeMapEntries, setLifeMapEntries] = useState<LifeMapEntry[]>([])
  const [claimedTiers, setClaimedTiers] = useState<number[]>([])
  const [showRooms, setShowRooms] = useState(false)

  const playerName = activeChild?.display_name ?? guestSession?.displayName ?? 'Explorer'
  const isGuest = !activeChild && !!guestSession

  // Load claimed tiers on mount
  useEffect(() => {
    if (activeChild) {
      supabase.from('aw_season_pass').select('claimed_tiers').eq('student_id', activeChild.id).single()
        .then(({ data }) => { if (data) setClaimedTiers(data.claimed_tiers ?? []) })
    }
  }, [activeChild])

  async function saveAvatar(avatar: AvatarData) {
    setAvatarData(avatar)
    if (activeChild) {
      await supabase.from('aw_student_profiles')
        .update({ avatar_data: avatar as unknown as Record<string, unknown> }).eq('id', activeChild.id)
    } else if (guestSession) {
      localStorage.setItem('adeline_guest', JSON.stringify({ ...guestSession, avatarData: avatar }))
    }
    setScreen('chat')
  }

  async function addXP(amount: number) {
    const newXP = localXP + amount
    setLocalXP(newXP)
    if (activeChild) {
      await supabase.from('aw_student_profiles').update({ xp: newXP }).eq('id', activeChild.id)
    }
  }

  async function addCoins(amount: number) {
    const newCoins = localCoins + amount
    setLocalCoins(newCoins)
    if (activeChild) {
      await supabase.from('aw_student_profiles').update({ ade_coins: newCoins }).eq('id', activeChild.id)
    }
  }

  function handleLifeMapEntry(entry: LifeMapEntry) {
    setLifeMapEntries(prev => [entry, ...prev])
  }

  async function handleRoomMissionComplete(description: string, tracks: Track[], xp: number, coins: number) {
    addXP(xp)
    addCoins(coins)
    if (activeChild) {
      const entry = await logActivity(activeChild.id, description, tracks, xp, coins, 'room_mission')
      if (entry) handleLifeMapEntry(entry)
    }
  }

  async function claimSeasonTier(tier: number, coinsToAdd: number) {
    const newClaimed = [...claimedTiers, tier]
    setClaimedTiers(newClaimed)
    if (coinsToAdd > 0) addCoins(coinsToAdd)
    if (activeChild) {
      await supabase.from('aw_season_pass')
        .upsert({ student_id: activeChild.id, claimed_tiers: newClaimed }, { onConflict: 'student_id' })
    }
  }

  const enterRoom = useCallback((roomId: RoomId, mode: 'quiz' | 'mission' = 'mission') => {
    setCurrentRoom(roomId)
    setRoomMode(mode)
    setScreen('room')
    setShowRooms(false)
  }, [])

  async function handleSignOut() {
    await signOut()
    navigate('/')
  }

  const hudPlayer = activeChild ? { ...activeChild, xp: localXP, ade_coins: localCoins } : null
  const hudGuest = guestSession ? { ...guestSession, xp: localXP, adeCoins: localCoins } : null

  // ── Avatar Builder ──
  if (screen === 'avatar_builder') {
    return (
      <AvatarBuilder
        initialAvatar={storedAvatar ?? guestAvatar ?? undefined}
        playerName={playerName}
        onSave={saveAvatar}
      />
    )
  }

  // ── Room view ──
  if (screen === 'room' && currentRoom) {
    const config = ROOM_CONFIG[currentRoom]
    return (
      <div className="w-screen h-screen overflow-hidden relative">
        <GameHUD
          player={hudPlayer}
          guestSession={hudGuest}
          avatarData={avatarData}
          roomLabel={`${config.emoji} ${config.label}`}
          onExitRoom={() => { setCurrentRoom(null); setScreen('chat') }}
          onSignOut={handleSignOut}
        />
        <div className="w-full h-full pt-16">
          {roomMode === 'mission' ? (
            <RoomMission
              roomId={currentRoom}
              roomLabel={config.label}
              roomEmoji={config.emoji}
              roomTracks={config.tracks}
              playerName={playerName}
              systemContext={config.context}
              onComplete={handleRoomMissionComplete}
              onBack={() => { setCurrentRoom(null); setScreen('chat') }}
            />
          ) : (
            <>
              {currentRoom === 'math_mines'     && <MathMines     playerName={playerName} onXpEarned={addXP} onCoinsEarned={addCoins} />}
              {currentRoom === 'story_forest'   && <StoryForest   playerName={playerName} onXpEarned={addXP} onCoinsEarned={addCoins} />}
              {currentRoom === 'science_lab'    && <ScienceLab    playerName={playerName} onXpEarned={addXP} onCoinsEarned={addCoins} />}
              {currentRoom === 'homestead_farm' && <HomesteadFarm playerName={playerName} onXpEarned={addXP} onCoinsEarned={addCoins} />}
              {currentRoom === 'truth_archive'  && <TruthArchive  playerName={playerName} onXpEarned={addXP} onCoinsEarned={addCoins} />}
            </>
          )}
        </div>
      </div>
    )
  }

  // ── Hub World (2D exploration) ──
  if (screen === 'hub') {
    return (
      <div className="w-screen h-screen overflow-hidden relative">
        <GameHUD
          player={hudPlayer}
          guestSession={hudGuest}
          avatarData={avatarData}
          onExitRoom={() => setScreen('chat')}
          onSignOut={handleSignOut}
        />
        <div className="w-full h-full pt-16">
          <HubWorld
            avatarData={avatarData}
            playerName={playerName}
            onEnterRoom={(id) => enterRoom(id, 'mission')}
            onChatAdeline={() => setScreen('chat')}
          />
        </div>
      </div>
    )
  }

  // ── Main Chat Screen ──
  return (
    <div className="w-screen h-screen overflow-hidden flex flex-col bg-amber-50/30">
      {/* Top bar */}
      <div className="h-14 bg-white border-b border-amber-100 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full overflow-hidden border-2 border-amber-400">
            <img src="/adeline_portrait.png" alt="Adeline" className="w-full h-full object-cover"
              onError={e => { e.currentTarget.style.display='none' }} />
          </div>
          <div>
            <p className="font-bold text-slate-800 text-sm">Adeline</p>
            <p className="text-xs text-amber-600">Learning Guide</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* XP + coins mini display */}
          <div className="hidden sm:flex items-center gap-3 bg-slate-100 rounded-xl px-3 py-1.5">
            <span className="text-xs font-bold text-amber-700">{localXP} XP</span>
            <span className="text-slate-300">·</span>
            <span className="text-xs font-bold text-amber-700">🪙 {localCoins}</span>
          </div>

          <button onClick={() => setOverlay('life_map')}
            className="px-3 py-1.5 text-xs font-semibold bg-violet-100 hover:bg-violet-200 text-violet-700 rounded-xl transition-all">
            🗺️ Life Map
          </button>
          <button onClick={() => setOverlay('season_pass')}
            className="px-3 py-1.5 text-xs font-semibold bg-amber-100 hover:bg-amber-200 text-amber-700 rounded-xl transition-all">
            🌟 Pass
          </button>
          <button onClick={() => setScreen('hub')}
            className="px-3 py-1.5 text-xs font-semibold bg-green-100 hover:bg-green-200 text-green-700 rounded-xl transition-all">
            🏘️ Hub
          </button>
          {parentAccount && (
            <button onClick={() => navigate('/parent-dashboard')}
              className="px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl transition-all">
              👪
            </button>
          )}
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden">

        {/* Chat (main) */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <AdelineChat
            studentId={activeChild?.id ?? null}
            playerName={playerName}
            currentXP={localXP}
            onXpEarned={addXP}
            onCoinsEarned={addCoins}
            onLifeMapEntry={handleLifeMapEntry}
          />
        </div>

        {/* Room sidebar — desktop */}
        <div className="hidden lg:flex flex-col w-56 bg-white border-l border-amber-100 p-3 gap-2 overflow-y-auto shrink-0">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider px-1 mb-1">Enter a Room</p>
          {(Object.entries(ROOM_CONFIG) as [RoomId, typeof ROOM_CONFIG[RoomId]][]).map(([id, cfg]) => (
            <div key={id} className="rounded-xl border border-slate-100 overflow-hidden">
              <button
                onClick={() => enterRoom(id, 'mission')}
                className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-amber-50 transition-all text-left"
              >
                <span className="text-xl">{cfg.emoji}</span>
                <span className="text-sm font-semibold text-slate-700">{cfg.label}</span>
              </button>
              <button
                onClick={() => enterRoom(id, 'quiz')}
                className="w-full px-3 py-1.5 text-xs text-slate-400 hover:text-slate-600 hover:bg-slate-50 border-t border-slate-100 transition-all text-left"
              >
                Quick quiz →
              </button>
            </div>
          ))}

          <div className="mt-2 pt-2 border-t border-slate-100">
            <button
              onClick={handleSignOut}
              className="w-full text-xs text-slate-400 hover:text-slate-600 py-2 rounded-lg hover:bg-slate-50 transition-all"
            >
              {isGuest ? 'Leave Game' : 'Sign Out'}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile room launcher button */}
      <div className="lg:hidden fixed bottom-20 right-4 z-30">
        <button
          onClick={() => setShowRooms(!showRooms)}
          className="w-14 h-14 bg-amber-500 hover:bg-amber-400 text-white rounded-full shadow-xl text-2xl flex items-center justify-center transition-all"
        >
          {showRooms ? '✕' : '🏫'}
        </button>
      </div>

      {/* Mobile room drawer */}
      {showRooms && (
        <div className="lg:hidden fixed bottom-36 right-4 z-30 bg-white rounded-2xl shadow-xl border border-amber-100 p-3 w-52 space-y-1">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider px-1 mb-2">Enter a Room</p>
          {(Object.entries(ROOM_CONFIG) as [RoomId, typeof ROOM_CONFIG[RoomId]][]).map(([id, cfg]) => (
            <button
              key={id}
              onClick={() => enterRoom(id, 'mission')}
              className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-amber-50 rounded-xl transition-all text-left"
            >
              <span className="text-xl">{cfg.emoji}</span>
              <span className="text-sm font-semibold text-slate-700">{cfg.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Guest nudge */}
      {isGuest && (
        <div className="lg:hidden fixed bottom-4 left-4 right-20 bg-amber-500 text-white text-xs font-semibold px-4 py-2 rounded-2xl shadow-lg">
          💾 Guest — progress not saved.{' '}
          <button onClick={handleSignOut} className="underline">Create account</button>
        </div>
      )}

      {/* Overlays */}
      {overlay === 'life_map' && (
        <LifeMap
          studentId={activeChild?.id ?? null}
          localEntries={lifeMapEntries}
          onClose={() => setOverlay(null)}
        />
      )}
      {overlay === 'season_pass' && (
        <SeasonPass
          currentXP={localXP}
          claimedTiers={claimedTiers}
          onClaimTier={claimSeasonTier}
          onClose={() => setOverlay(null)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/GameShell.tsx
git commit -m "feat: refactor GameShell to chat-first layout with room sidebar, Life Map, Season Pass"
```

---

## Task 9: Update server.ts to Accept systemPrompt Override

The new AdelineChat passes a full `systemPrompt` field. The server needs to use it if provided.

**Files:**
- Modify: `server.ts`

- [ ] **Step 1: Read and update `server.ts` chat handler**

Find the `/api/chat` handler. Replace the current `systemInstruction` constant with logic that uses `req.body.systemPrompt` if provided:

```typescript
  app.post("/api/chat", async (req, res) => {
    try {
      const { message, history, systemPrompt } = req.body;
      const apiKey = process.env.GEMINI_API_KEY;

      if (!apiKey) {
        return res.json({
          reply: "Hello! I am Adeline, your AI Mentor. (Note: GEMINI_API_KEY is not configured yet.)",
        });
      }

      const ai = new GoogleGenAI({ apiKey });

      const defaultSystemInstruction = `You are Adeline — a warm, sharp-witted educational mentor for Christian homeschool families.

You believe: Knowledge without love is nothing. Every child has a calling.

Your rules:
- Every quest or activity you suggest must have a REAL PURPOSE — it helps someone, solves a problem, or creates something beautiful.
- Always ask "Who profits?" when teaching history, civics, or economics. Follow the money.
- Affirm each student's unique worth and calling — you see who they are becoming.
- For history: never sanitize. Show what really happened. Quote real sources when you can.
- For science: connect everything to the natural world, farming, animals, and how things actually work.
- Mathematics lives in real life: budgets, land measurement, recipes, building plans.
- A student's portfolio is their ACCOMPLISHMENTS, not their assignments. What did they make, build, grow, or sell?

You are speaking to a child in Adeline World. Keep your tone age-appropriate, encouraging, and adventurous.`;

      const systemInstruction = systemPrompt || defaultSystemInstruction;

      const contents = [
        { role: 'user', parts: [{ text: systemInstruction }] },
        ...(history || []).map((msg: any) => ({
          role: msg.isFromUser ? 'user' : 'model',
          parts: [{ text: msg.text }]
        })),
        { role: 'user', parts: [{ text: message }] }
      ];

      const response = await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents,
      });

      const reply = response.text || "I'm here with you! Let's keep exploring.";
      res.json({ reply });
    } catch (err: any) {
      console.error("Gemini API Error:", err);
      res.status(500).json({ reply: "I ran into a temporary hiccup. Let's try again!" });
    }
  });
```

- [ ] **Step 2: Commit**

```bash
git add server.ts
git commit -m "feat: server accepts systemPrompt override from client for rich Adeline context"
```

---

## Task 10: TypeScript Check + Smoke Test + Push

- [ ] **Step 1: Run TypeScript check**

```bash
npx tsc --noEmit 2>&1
```

Fix any errors before proceeding. Common issues:
- Missing imports
- `LifeMapEntry` used before being exported from `game.ts` — verify the export exists

- [ ] **Step 2: Kill existing server and restart**

```bash
npx kill-port 3000 2>/dev/null || true
npm run dev
```

- [ ] **Step 3: Test guest flow — chat first**

1. Open `http://localhost:3000` → Play as Guest → enter name
2. Avatar builder appears → build avatar → "Enter Adeline World!"
3. **Main screen should now be the Adeline chat** (NOT the hub world)
4. Adeline greets you, asks what you've been up to
5. Type: "I helped my mom can 30 jars of tomatoes today"
6. Adeline responds and shows **ADELINE_LOG activity banner**
7. Click "Yes, log it!" → XP and coins increase in top bar
8. Life Map button → click → your activity appears in HOMESTEADING track ✓

- [ ] **Step 4: Test room missions**

1. Click ⛏️ Math Mines in the sidebar
2. Mission appears (not a quiz) — text area to write response
3. Write a response (at least 20 chars) → Submit
4. Adeline gives written feedback
5. "+XP" banner appears ✓

- [ ] **Step 5: Test quick quiz mode**

1. In the room sidebar, click "Quick quiz →" under Math Mines
2. Multiple choice quiz loads (old behavior) ✓

- [ ] **Step 6: Test parent dashboard**

1. Sign out → Create Parent Account → add a child → enter game
2. Top bar shows 👪 button → click → Parent Dashboard opens
3. Shows child's name, XP, coins, logged activities ✓

- [ ] **Step 7: Final push**

```bash
git add -A
git status  # should be clean
git log --oneline -10
git push origin adeline-world-plan-1
```

---

## Self-Review

**Spec coverage:**
- ✅ Chat-first main screen — Task 8
- ✅ Adeline learns about kids through conversation — Task 3 (memory detection + upsert)
- ✅ Real-life activity logging — Tasks 2, 3 (ActivityConfirm, lifeMapService, ADELINE_LOG detection)
- ✅ Life Map visual display — Task 5
- ✅ Room missions (open-ended, not just quizzes) — Task 4 (RoomMission)
- ✅ Quick quiz mode still available — Task 8 (roomMode toggle)
- ✅ Season Pass — Task 6
- ✅ Parent Dashboard with activity log + approvals — Task 7
- ✅ Supabase schema for memories, life map, season pass — Task 1
- ✅ systemPrompt override so Adeline's full persona reaches Gemini — Task 9

**Type consistency:**
- `LifeMapEntry` defined in `game.ts` Task 1, used in Tasks 3, 5, 8 ✅
- `Track` defined in `game.ts` Task 1, used in Tasks 2, 3, 4, 5, 7, 8 ✅
- `SEASON_TIERS` defined in `game.ts` Task 1, used in Task 6 ✅
- `logActivity()` defined in `lifeMapService.ts` Task 2, used in Tasks 3, 8 ✅
- `buildMemoryContext()` defined in `memoryService.ts` Task 2, used in Task 3 ✅
- `AdelineChat` props: `studentId`, `playerName`, `currentXP`, `onXpEarned`, `onCoinsEarned`, `onLifeMapEntry` — consistent between Task 3 definition and Task 8 usage ✅
- `RoomMission` props: `roomId`, `roomLabel`, `roomEmoji`, `roomTracks`, `playerName`, `systemContext`, `onComplete`, `onBack` — consistent between Task 4 definition and Task 8 usage ✅
- `ROOM_CONFIG` defined in Task 8 GameShell, provides `tracks` to `RoomMission` as `Track[]` ✅
