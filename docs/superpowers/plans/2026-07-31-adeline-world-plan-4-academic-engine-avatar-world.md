# Adeline World — Plan 4: Academic Engine + Avatar-in-World Chat Layout

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Add grade-awareness, credit-hour tracking, portfolio, graduation tracker, and exportable transcript — the full academic engine from dearadeline-withlove. (2) Show the student's avatar on the main chat screen walking around a mini world-view, with animated movement into rooms when selected.

**Architecture:**
- Academic engine: grade band stored on student profile, credit hours calculated from `aw_life_map_entries` (each entry = 0.1 credits), year-end goals per grade band, graduation unlocked when all required tracks meet credit minimums. Portfolio is a filtered Life Map view showing accomplishments only. Transcript is a formatted printable page.
- Avatar world-view: the main chat screen splits into chat (left) + mini 2D scene (right). The mini scene uses CSS animation to walk the avatar from its current position to a room door when a room is selected. Entry triggers after the walk animation completes (~600ms). On mobile, the mini world collapses to a horizontal strip above the chat.

**Tech Stack:** React 19, TypeScript, Tailwind, CSS keyframe animations, Supabase (existing), existing AuthContext + types

---

## File Structure

```
src/
  types/
    game.ts                        # Add: GradeBand, CreditSummary, PortfolioEntry types (modify)
  lib/
    academicEngine.ts              # Credit calculation, grade band, graduation check (new)
  components/
    world/
      MiniWorld.tsx                # Avatar walks around mini hub, rooms as doors (new)
    portfolio/
      Portfolio.tsx                # Accomplishments view from Life Map (new)
    graduation/
      GraduationTracker.tsx        # Per-track credit progress + graduation unlock (new)
    transcript/
      Transcript.tsx               # Printable transcript (new)
  pages/
    GameShell.tsx                  # Add MiniWorld to chat layout (modify)
```

### New Supabase column (alter existing table)

```sql
-- Add grade_level to student profile
alter table public.aw_student_profiles
  add column if not exists grade_level text default 'K-2';
```

---

## Task 1: Add Grade + Academic Types

**Files:**
- Modify: `src/types/game.ts`
- Create: `supabase/migrations/003_grade_level.sql`

- [ ] **Step 1: Create migration file `supabase/migrations/003_grade_level.sql`**

```sql
alter table public.aw_student_profiles
  add column if not exists grade_level text default 'K-2';
```

- [ ] **Step 2: Apply migration via Supabase MCP to project `gyxowttfwqbajoapfebf`**

- [ ] **Step 3: Append to bottom of `src/types/game.ts`**

```typescript
export type GradeBand = 'K-2' | '3-5' | '6-8' | '9-12'

export interface GradeExpectation {
  band: GradeBand
  minCreditsPerYear: number
  requiredTracks: Track[]
}

export const GRADE_EXPECTATIONS: GradeExpectation[] = [
  {
    band: 'K-2',
    minCreditsPerYear: 1.0,
    requiredTracks: ['CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING', 'DISCIPLESHIP', 'ENGLISH_LITERATURE']
  },
  {
    band: '3-5',
    minCreditsPerYear: 1.5,
    requiredTracks: ['CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING', 'GOVERNMENT_ECONOMICS',
      'JUSTICE_CHANGEMAKING', 'DISCIPLESHIP', 'TRUTH_HISTORY', 'ENGLISH_LITERATURE']
  },
  {
    band: '6-8',
    minCreditsPerYear: 2.0,
    requiredTracks: ['CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING', 'GOVERNMENT_ECONOMICS',
      'JUSTICE_CHANGEMAKING', 'DISCIPLESHIP', 'TRUTH_HISTORY', 'ENGLISH_LITERATURE',
      'APPLIED_MATHEMATICS', 'CREATIVE_ECONOMY']
  },
  {
    band: '9-12',
    minCreditsPerYear: 3.0,
    requiredTracks: ['CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING', 'GOVERNMENT_ECONOMICS',
      'JUSTICE_CHANGEMAKING', 'DISCIPLESHIP', 'TRUTH_HISTORY', 'ENGLISH_LITERATURE',
      'APPLIED_MATHEMATICS', 'CREATIVE_ECONOMY']
  }
]

export const CREDITS_PER_ENTRY = 0.1   // each logged activity = 0.1 credit hours

// Life-to-credit keyword mapping (from adeline.config.toml)
export const LIFE_TO_CREDIT: Record<string, Track[]> = {
  baking:      ['CREATION_SCIENCE', 'APPLIED_MATHEMATICS'],
  cooking:     ['CREATION_SCIENCE', 'APPLIED_MATHEMATICS', 'HEALTH_NATUROPATHY'],
  gardening:   ['CREATION_SCIENCE', 'HOMESTEADING'],
  building:    ['APPLIED_MATHEMATICS', 'CREATIVE_ECONOMY'],
  woodworking: ['APPLIED_MATHEMATICS', 'CREATIVE_ECONOMY'],
  sewing:      ['APPLIED_MATHEMATICS', 'CREATIVE_ECONOMY', 'TRUTH_HISTORY'],
  coding:      ['APPLIED_MATHEMATICS', 'CREATIVE_ECONOMY'],
  reading:     ['ENGLISH_LITERATURE'],
  writing:     ['ENGLISH_LITERATURE'],
  volunteering:['GOVERNMENT_ECONOMICS', 'JUSTICE_CHANGEMAKING'],
  animals:     ['CREATION_SCIENCE', 'HOMESTEADING', 'DISCIPLESHIP'],
  soap_making: ['CREATION_SCIENCE', 'CREATIVE_ECONOMY'],
  debate:      ['ENGLISH_LITERATURE', 'GOVERNMENT_ECONOMICS'],
}

export interface CreditSummary {
  track: Track
  credits: number
  entriesCount: number
  meetsYearGoal: boolean
  creditsNeeded: number
}

export interface PortfolioEntry {
  id: string
  description: string
  tracks: Track[]
  credits: number
  date: string
}
```

- [ ] **Step 4: Update `StudentProfile` type in `src/types/auth.ts` to include `grade_level`**

Read `src/types/auth.ts`. Add `grade_level: string` to the `StudentProfile` interface.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/003_grade_level.sql src/types/game.ts src/types/auth.ts
git commit -m "feat: add grade band, credit types, life-to-credit mapping"
```

---

## Task 2: Academic Engine Service

**Files:**
- Create: `src/lib/academicEngine.ts`

- [ ] **Step 1: Create `src/lib/academicEngine.ts`**

```typescript
import { LifeMapEntry, Track, GradeBand, GRADE_EXPECTATIONS, CREDITS_PER_ENTRY, CreditSummary, PortfolioEntry } from '../types/game'

export function getGradeExpectation(band: GradeBand) {
  return GRADE_EXPECTATIONS.find(g => g.band === band) ?? GRADE_EXPECTATIONS[0]
}

export function calculateCredits(entries: LifeMapEntry[]): Partial<Record<Track, number>> {
  const credits: Partial<Record<Track, number>> = {}
  for (const entry of entries) {
    for (const track of entry.tracks) {
      credits[track] = (credits[track] ?? 0) + CREDITS_PER_ENTRY
    }
  }
  return credits
}

export function buildCreditSummary(
  entries: LifeMapEntry[],
  gradeBand: GradeBand
): CreditSummary[] {
  const expectation = getGradeExpectation(gradeBand)
  const credits = calculateCredits(entries)
  const perTrackGoal = expectation.minCreditsPerYear / expectation.requiredTracks.length

  return expectation.requiredTracks.map(track => {
    const earned = credits[track] ?? 0
    return {
      track,
      credits: Math.round(earned * 10) / 10,
      entriesCount: entries.filter(e => e.tracks.includes(track)).length,
      meetsYearGoal: earned >= perTrackGoal,
      creditsNeeded: Math.max(0, Math.round((perTrackGoal - earned) * 10) / 10)
    }
  })
}

export function checkGraduationEligible(
  entries: LifeMapEntry[],
  gradeBand: GradeBand
): { eligible: boolean; totalCredits: number; creditsNeeded: number; tracksComplete: number; tracksRequired: number } {
  const expectation = getGradeExpectation(gradeBand)
  const credits = calculateCredits(entries)
  const perTrackGoal = expectation.minCreditsPerYear / expectation.requiredTracks.length

  const totalCredits = Object.values(credits).reduce((sum, c) => sum + (c ?? 0), 0)
  const tracksComplete = expectation.requiredTracks.filter(t => (credits[t] ?? 0) >= perTrackGoal).length
  const creditsNeeded = Math.max(0, expectation.minCreditsPerYear - totalCredits)

  return {
    eligible: tracksComplete === expectation.requiredTracks.length && totalCredits >= expectation.minCreditsPerYear,
    totalCredits: Math.round(totalCredits * 10) / 10,
    creditsNeeded: Math.round(creditsNeeded * 10) / 10,
    tracksComplete,
    tracksRequired: expectation.requiredTracks.length
  }
}

export function buildPortfolio(entries: LifeMapEntry[]): PortfolioEntry[] {
  return entries.map(entry => ({
    id: entry.id,
    description: entry.description,
    tracks: entry.tracks,
    credits: entry.tracks.length * CREDITS_PER_ENTRY,
    date: entry.created_at
  }))
}

export function getYearProgress(entries: LifeMapEntry[], gradeBand: GradeBand): number {
  const expectation = getGradeExpectation(gradeBand)
  const credits = calculateCredits(entries)
  const total = Object.values(credits).reduce((sum, c) => sum + (c ?? 0), 0)
  return Math.min(100, Math.round((total / expectation.minCreditsPerYear) * 100))
}

export function gradeBandFromAge(age: number | null): GradeBand {
  if (!age) return 'K-2'
  if (age <= 8)  return 'K-2'
  if (age <= 11) return '3-5'
  if (age <= 14) return '6-8'
  return '9-12'
}
```

- [ ] **Step 2: Commit**

```bash
git add src/lib/academicEngine.ts
git commit -m "feat: add academic engine - credits, grade bands, graduation check, portfolio"
```

---

## Task 3: Graduation Tracker Component

**Files:**
- Create: `src/components/graduation/GraduationTracker.tsx`

- [ ] **Step 1: Create `src/components/graduation/GraduationTracker.tsx`**

```typescript
import { useMemo } from 'react'
import { LifeMapEntry, GradeBand, TRACK_LABELS, TRACK_COLORS } from '../../types/game'
import { buildCreditSummary, checkGraduationEligible, getYearProgress } from '../../lib/academicEngine'

interface Props {
  entries: LifeMapEntry[]
  gradeBand: GradeBand
  studentName: string
  onClose: () => void
}

export default function GraduationTracker({ entries, gradeBand, studentName, onClose }: Props) {
  const summary = useMemo(() => buildCreditSummary(entries, gradeBand), [entries, gradeBand])
  const graduation = useMemo(() => checkGraduationEligible(entries, gradeBand), [entries, gradeBand])
  const yearProgress = useMemo(() => getYearProgress(entries, gradeBand), [entries, gradeBand])

  const bandLabel: Record<GradeBand, string> = {
    'K-2':  'Kindergarten–2nd Grade',
    '3-5':  '3rd–5th Grade',
    '6-8':  '6th–8th Grade',
    '9-12': '9th–12th Grade (High School)'
  }

  return (
    <div className="fixed inset-0 bg-slate-900/95 z-50 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div>
          <h2 className="text-white font-bold text-xl font-serif">🎓 Learning Path</h2>
          <p className="text-white/50 text-xs mt-0.5">{studentName} · {bandLabel[gradeBand]}</p>
        </div>
        <button onClick={onClose} className="text-white/60 hover:text-white text-2xl px-2">✕</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">

        {/* Year progress */}
        <div className="bg-white/10 rounded-2xl p-4 border border-white/20">
          <div className="flex items-center justify-between mb-3">
            <p className="text-white font-bold">Year Progress</p>
            <p className="text-amber-300 font-bold text-sm">{yearProgress}%</p>
          </div>
          <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${yearProgress}%`,
                background: yearProgress >= 100 ? '#10b981' : 'linear-gradient(90deg, #f59e0b, #f97316)'
              }}
            />
          </div>
          <div className="flex justify-between mt-2">
            <p className="text-white/50 text-xs">{graduation.totalCredits} credits earned</p>
            <p className="text-white/50 text-xs">{graduation.creditsNeeded > 0 ? `${graduation.creditsNeeded} more needed` : '✓ Year goal met!'}</p>
          </div>
        </div>

        {/* Graduation status */}
        {graduation.eligible ? (
          <div className="bg-emerald-500/20 border-2 border-emerald-400 rounded-2xl p-5 text-center space-y-2">
            <p className="text-5xl">🎓</p>
            <p className="text-emerald-300 font-bold text-xl">Graduation Unlocked!</p>
            <p className="text-white/70 text-sm">
              {studentName} has completed all required tracks for {bandLabel[gradeBand]}.
            </p>
          </div>
        ) : (
          <div className="bg-white/5 rounded-2xl p-4 border border-white/10">
            <p className="text-white font-semibold text-sm mb-1">Path to Graduation</p>
            <p className="text-white/50 text-xs">
              {graduation.tracksComplete}/{graduation.tracksRequired} tracks complete ·{' '}
              {graduation.creditsNeeded} credits remaining
            </p>
          </div>
        )}

        {/* Per-track credit bars */}
        <div>
          <p className="text-white/50 text-xs font-bold uppercase tracking-wider mb-3">Track Progress</p>
          <div className="space-y-3">
            {summary.map(item => (
              <div key={item.track} className="bg-white/5 rounded-xl p-3 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white text-sm font-semibold">{TRACK_LABELS[item.track]}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-white/50 text-xs">{item.credits} cr · {item.entriesCount} entries</span>
                    {item.meetsYearGoal && <span className="text-emerald-400 text-xs">✓</span>}
                  </div>
                </div>
                <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, item.meetsYearGoal ? 100 : (item.credits / (item.credits + item.creditsNeeded)) * 100)}%`,
                      backgroundColor: TRACK_COLORS[item.track]
                    }}
                  />
                </div>
                {!item.meetsYearGoal && (
                  <p className="text-white/30 text-xs mt-1">{item.creditsNeeded} more credits needed</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/graduation/GraduationTracker.tsx
git commit -m "feat: add GraduationTracker with per-track credit bars and year progress"
```

---

## Task 4: Portfolio Component

**Files:**
- Create: `src/components/portfolio/Portfolio.tsx`

- [ ] **Step 1: Create `src/components/portfolio/Portfolio.tsx`**

```typescript
import { useMemo } from 'react'
import { LifeMapEntry, Track, TRACK_LABELS, TRACK_COLORS, GradeBand } from '../../types/game'
import { buildPortfolio, buildCreditSummary } from '../../lib/academicEngine'

interface Props {
  entries: LifeMapEntry[]
  studentName: string
  gradeBand: GradeBand
  onClose: () => void
  onExport: () => void
}

export default function Portfolio({ entries, studentName, gradeBand, onClose, onExport }: Props) {
  const portfolio = useMemo(() => buildPortfolio(entries), [entries])
  const creditSummary = useMemo(() => buildCreditSummary(entries, gradeBand), [entries, gradeBand])
  const totalCredits = creditSummary.reduce((sum, s) => sum + s.credits, 0)

  // Group by track for display
  const byTrack: Partial<Record<Track, typeof portfolio>> = {}
  for (const item of portfolio) {
    for (const track of item.tracks) {
      if (!byTrack[track]) byTrack[track] = []
      byTrack[track]!.push(item)
    }
  }

  return (
    <div className="fixed inset-0 bg-slate-900/95 z-50 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div>
          <h2 className="text-white font-bold text-xl font-serif">📁 Portfolio</h2>
          <p className="text-white/50 text-xs mt-0.5">
            {studentName} · {portfolio.length} accomplishments · {Math.round(totalCredits * 10) / 10} credits
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onExport}
            className="px-3 py-1.5 text-xs bg-amber-500 hover:bg-amber-400 text-white font-bold rounded-xl"
          >
            Export →
          </button>
          <button onClick={onClose} className="text-white/60 hover:text-white text-2xl px-2">✕</button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {portfolio.length === 0 ? (
          <div className="text-center py-16 space-y-4">
            <p className="text-5xl">📁</p>
            <p className="text-white font-bold text-lg">Portfolio is empty</p>
            <p className="text-white/50 text-sm max-w-xs mx-auto">
              Tell Adeline what you've done — built, grown, cooked, written, coded — and it goes here.
            </p>
          </div>
        ) : (
          Object.entries(byTrack).map(([track, items]) => (
            <div key={track} className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: TRACK_COLORS[track as Track] }} />
                <p className="text-white font-bold text-sm">{TRACK_LABELS[track as Track]}</p>
                <span className="text-white/30 text-xs">{items!.length} entries</span>
              </div>
              <div className="space-y-2 ml-5">
                {items!.map(item => (
                  <div key={item.id} className="bg-white/5 rounded-xl p-3 border border-white/10">
                    <p className="text-white/90 text-sm">{item.description}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-amber-300 text-xs">{item.credits} credits</span>
                      <span className="text-white/30 text-xs">
                        {new Date(item.date).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/portfolio/Portfolio.tsx
git commit -m "feat: add Portfolio component grouped by track with credit display"
```

---

## Task 5: Transcript Component

**Files:**
- Create: `src/components/transcript/Transcript.tsx`

- [ ] **Step 1: Create `src/components/transcript/Transcript.tsx`**

```typescript
import { useMemo, useRef } from 'react'
import { LifeMapEntry, GradeBand, TRACK_LABELS, GRADE_EXPECTATIONS } from '../../types/game'
import { buildCreditSummary, checkGraduationEligible } from '../../lib/academicEngine'

interface Props {
  entries: LifeMapEntry[]
  studentName: string
  gradeBand: GradeBand
  parentName: string
  onClose: () => void
}

export default function Transcript({ entries, studentName, gradeBand, parentName, onClose }: Props) {
  const printRef = useRef<HTMLDivElement>(null)
  const summary = useMemo(() => buildCreditSummary(entries, gradeBand), [entries, gradeBand])
  const graduation = useMemo(() => checkGraduationEligible(entries, gradeBand), [entries, gradeBand])
  const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
  const expectation = GRADE_EXPECTATIONS.find(g => g.band === gradeBand)!

  const bandLabel: Record<GradeBand, string> = {
    'K-2':  'Kindergarten through 2nd Grade',
    '3-5':  '3rd through 5th Grade',
    '6-8':  '6th through 8th Grade',
    '9-12': '9th through 12th Grade'
  }

  function printTranscript() {
    window.print()
  }

  return (
    <div className="fixed inset-0 bg-slate-900/95 z-50 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-white/10 print:hidden">
        <h2 className="text-white font-bold text-xl font-serif">📄 Transcript</h2>
        <div className="flex gap-2">
          <button
            onClick={printTranscript}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-white text-sm font-bold rounded-xl"
          >
            🖨️ Print / Save PDF
          </button>
          <button onClick={onClose} className="text-white/60 hover:text-white text-2xl px-2">✕</button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div ref={printRef} className="max-w-2xl mx-auto bg-white rounded-2xl p-8 space-y-6 print:rounded-none print:p-6">

          {/* Header */}
          <div className="text-center border-b border-slate-200 pb-6">
            <h1 className="text-2xl font-bold text-slate-900 font-serif">Academic Transcript</h1>
            <p className="text-slate-500 text-sm mt-1">Dear Adeline Homeschool · Adeline World</p>
          </div>

          {/* Student info */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-500 font-semibold">Student</p>
              <p className="text-slate-900 font-bold text-lg">{studentName}</p>
            </div>
            <div>
              <p className="text-slate-500 font-semibold">Parent / Guardian</p>
              <p className="text-slate-900">{parentName}</p>
            </div>
            <div>
              <p className="text-slate-500 font-semibold">Grade Level</p>
              <p className="text-slate-900">{bandLabel[gradeBand]}</p>
            </div>
            <div>
              <p className="text-slate-500 font-semibold">Date Issued</p>
              <p className="text-slate-900">{today}</p>
            </div>
          </div>

          {/* Credit summary table */}
          <div>
            <h2 className="font-bold text-slate-800 text-lg mb-3 border-b border-slate-200 pb-2">Credit Summary</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 text-slate-600 font-semibold">Subject Area</th>
                  <th className="text-right py-2 text-slate-600 font-semibold">Credits</th>
                  <th className="text-right py-2 text-slate-600 font-semibold">Activities</th>
                  <th className="text-right py-2 text-slate-600 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {summary.map(item => (
                  <tr key={item.track} className="border-b border-slate-100">
                    <td className="py-2 text-slate-800">{TRACK_LABELS[item.track]}</td>
                    <td className="py-2 text-right text-slate-800 font-mono">{item.credits.toFixed(1)}</td>
                    <td className="py-2 text-right text-slate-500">{item.entriesCount}</td>
                    <td className="py-2 text-right">
                      {item.meetsYearGoal
                        ? <span className="text-emerald-600 font-semibold">✓ Complete</span>
                        : <span className="text-amber-600">In Progress</span>
                      }
                    </td>
                  </tr>
                ))}
                <tr className="border-t-2 border-slate-300 font-bold">
                  <td className="py-2 text-slate-900">TOTAL</td>
                  <td className="py-2 text-right font-mono text-slate-900">
                    {summary.reduce((s, i) => s + i.credits, 0).toFixed(1)}
                  </td>
                  <td className="py-2 text-right text-slate-500">{entries.length}</td>
                  <td className="py-2 text-right">
                    {graduation.eligible
                      ? <span className="text-emerald-600 font-bold">✓ Year Complete</span>
                      : <span className="text-slate-500">–</span>
                    }
                  </td>
                </tr>
              </tbody>
            </table>
            <p className="text-slate-400 text-xs mt-2">
              Required: {expectation.minCreditsPerYear} credits/year across {expectation.requiredTracks.length} subject areas
            </p>
          </div>

          {/* Recent accomplishments */}
          <div>
            <h2 className="font-bold text-slate-800 text-lg mb-3 border-b border-slate-200 pb-2">
              Selected Accomplishments
            </h2>
            <div className="space-y-2">
              {entries.slice(0, 15).map(entry => (
                <div key={entry.id} className="flex gap-3 text-sm">
                  <span className="text-slate-400 shrink-0">
                    {new Date(entry.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                  <span className="text-slate-700">{entry.description}</span>
                </div>
              ))}
              {entries.length > 15 && (
                <p className="text-slate-400 text-xs">+ {entries.length - 15} more activities on record</p>
              )}
            </div>
          </div>

          {/* Graduation status */}
          {graduation.eligible && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
              <p className="text-emerald-800 font-bold">🎓 Year Requirements Satisfied</p>
              <p className="text-emerald-600 text-sm mt-1">
                {studentName} has met all requirements for {bandLabel[gradeBand]}.
              </p>
            </div>
          )}

          {/* Signature line */}
          <div className="border-t border-slate-200 pt-6 flex justify-between text-sm text-slate-500">
            <div>
              <div className="border-b border-slate-400 w-48 mb-1" />
              <p>Parent / Guardian Signature</p>
            </div>
            <div className="text-right">
              <p>Generated by Adeline World</p>
              <p>{today}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/transcript/Transcript.tsx
git commit -m "feat: add printable Transcript with credit table and accomplishments"
```

---

## Task 6: MiniWorld — Avatar Walks to Rooms

**Files:**
- Create: `src/components/world/MiniWorld.tsx`

This is the animated mini world shown on the right side of the chat screen. The avatar stands in the hub and walks toward whichever room door is clicked, then the room opens after the walk animation.

- [ ] **Step 1: Create `src/components/world/MiniWorld.tsx`**

```typescript
import { useState, useEffect } from 'react'
import { AvatarData, RoomId, HUB_PORTALS } from '../../types/game'
import AvatarRenderer from '../avatar/AvatarRenderer'

interface Props {
  avatarData: AvatarData
  playerName: string
  onEnterRoom: (roomId: RoomId) => void
}

// Mini-world positions (% of container, scaled down from full hub)
const AVATAR_HOME = { x: 50, y: 72 }

// Door positions in the mini world (match hub portal layout but scaled)
const DOOR_POSITIONS: Record<RoomId, { x: number; y: number }> = {
  math_mines:     { x: 22, y: 42 },
  story_forest:   { x: 75, y: 38 },
  science_lab:    { x: 50, y: 18 },
  homestead_farm: { x: 15, y: 62 },
  truth_archive:  { x: 85, y: 62 },
}

const WALK_DURATION_MS = 600

export default function MiniWorld({ avatarData, playerName, onEnterRoom }: Props) {
  const [avatarPos, setAvatarPos] = useState(AVATAR_HOME)
  const [walking, setWalking] = useState(false)
  const [targetRoom, setTargetRoom] = useState<RoomId | null>(null)
  const [hovered, setHovered] = useState<RoomId | null>(null)

  function handleRoomClick(roomId: RoomId) {
    if (walking) return
    const dest = DOOR_POSITIONS[roomId]
    setTargetRoom(roomId)
    setWalking(true)
    setAvatarPos(dest)

    setTimeout(() => {
      setWalking(false)
      setAvatarPos(AVATAR_HOME)
      setTargetRoom(null)
      onEnterRoom(roomId)
    }, WALK_DURATION_MS + 100)
  }

  const portal = HUB_PORTALS.find(p => p.id === targetRoom)

  return (
    <div
      className="relative w-full h-full overflow-hidden rounded-2xl select-none"
      style={{ background: 'linear-gradient(180deg, #87CEEB 0%, #b0e0ff 35%, #5DBB5D 35%, #228B22 100%)' }}
    >
      {/* Path */}
      <div
        className="absolute rounded-lg"
        style={{ left: '25%', top: '35%', width: '50%', height: '50%', background: 'rgba(210,180,140,0.5)' }}
      />

      {/* Mini trees */}
      {[{x:5,y:45},{x:88,y:50},{x:8,y:68},{x:90,y:65}].map((t,i) => (
        <div key={i} className="absolute" style={{ left: `${t.x}%`, top: `${t.y}%` }}>
          <div style={{ width:14, height:18, background:'#1a6b1a', borderRadius:'50% 50% 30% 30%', marginLeft:-7 }} />
          <div style={{ width:4, height:8, background:'#5D4037', marginLeft:-2 }} />
        </div>
      ))}

      {/* Hub sign */}
      <div className="absolute" style={{ left:'50%', top:'26%', transform:'translateX(-50%)' }}>
        <div className="bg-amber-800/90 text-amber-100 font-bold text-[9px] px-2 py-1 rounded-md whitespace-nowrap">
          🏘️ Hub
        </div>
      </div>

      {/* Room doors */}
      {HUB_PORTALS.map(portal => {
        const pos = DOOR_POSITIONS[portal.id]
        const isHovered = hovered === portal.id
        const isTarget = targetRoom === portal.id
        return (
          <button
            key={portal.id}
            onClick={() => handleRoomClick(portal.id)}
            onMouseEnter={() => setHovered(portal.id)}
            onMouseLeave={() => setHovered(null)}
            disabled={walking}
            className="absolute flex flex-col items-center transition-transform"
            style={{
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              transform: `translate(-50%, -50%) ${isHovered || isTarget ? 'scale(1.15)' : 'scale(1)'}`,
            }}
          >
            <div
              className="w-8 h-11 rounded-t-full flex items-center justify-center text-lg shadow-md border-2"
              style={{
                backgroundColor: portal.color,
                borderColor: isHovered || isTarget ? '#FBBF24' : 'rgba(255,255,255,0.3)',
                boxShadow: isHovered || isTarget ? `0 0 10px ${portal.color}` : undefined
              }}
            >
              <span style={{ fontSize: 14 }}>{portal.emoji}</span>
            </div>
            <div
              className="w-10 h-1.5 rounded-b"
              style={{ backgroundColor: portal.color, filter: 'brightness(0.7)' }}
            />
            {isHovered && (
              <div className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap bg-black/70 text-white text-[9px] px-2 py-0.5 rounded-full">
                {portal.label}
              </div>
            )}
          </button>
        )
      })}

      {/* Player avatar — animated walk */}
      <div
        className="absolute flex flex-col items-center pointer-events-none z-20"
        style={{
          left: `${avatarPos.x}%`,
          top: `${avatarPos.y}%`,
          transform: 'translate(-50%, -50%)',
          transition: walking ? `left ${WALK_DURATION_MS}ms ease-in-out, top ${WALK_DURATION_MS}ms ease-in-out` : 'none',
          filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.4))'
        }}
      >
        <AvatarRenderer avatar={avatarData} size={36} />
        <p className="text-white text-[8px] font-bold text-center bg-black/40 px-1.5 rounded-full mt-0.5 whitespace-nowrap">
          {playerName.length > 10 ? playerName.slice(0, 10) + '…' : playerName}
        </p>
      </div>

      {/* Walking indicator */}
      {walking && portal && (
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-black/60 text-white text-[9px] px-2 py-1 rounded-full whitespace-nowrap">
          Walking to {portal.label}...
        </div>
      )}

      {/* Click-to-enter hint */}
      {!walking && (
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-white/50 text-[8px] whitespace-nowrap">
          Click a room to enter
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/world/MiniWorld.tsx
git commit -m "feat: add MiniWorld with avatar walk animation to room doors"
```

---

## Task 7: Wire Academic Features + MiniWorld into GameShell

**Files:**
- Modify: `src/pages/GameShell.tsx`
- Modify: `src/context/AuthContext.tsx` — pass grade_level through student profile

This task modifies `GameShell.tsx` to:
1. Show MiniWorld in the chat layout (right panel alongside chat)
2. Add Graduation, Portfolio, and Transcript to overlay options
3. Pass grade band to all academic components
4. Show year progress bar in the top bar

- [ ] **Step 1: Read `src/pages/GameShell.tsx` current content**

- [ ] **Step 2: Add new imports at the top**

After the existing imports, add:

```typescript
import MiniWorld from '../components/world/MiniWorld'
import GraduationTracker from '../components/graduation/GraduationTracker'
import Portfolio from '../components/portfolio/Portfolio'
import Transcript from '../components/transcript/Transcript'
import { getLifeMap } from '../lib/lifeMapService'
import { gradeBandFromAge, getYearProgress } from '../lib/academicEngine'
import { GradeBand } from '../types/game'
```

- [ ] **Step 3: Add state variables after existing state**

After `const [showRooms, setShowRooms] = useState(false)`, add:

```typescript
  const [allEntries, setAllEntries] = useState<LifeMapEntry[]>([])
  const [showTranscript, setShowTranscript] = useState(false)

  const gradeBand = gradeBandFromAge(activeChild?.age ?? null) as GradeBand
  const yearProgress = getYearProgress(allEntries, gradeBand)
```

- [ ] **Step 4: Add effect to load all life map entries**

After the existing `useEffect` for season pass, add:

```typescript
  useEffect(() => {
    if (activeChild) {
      getLifeMap(activeChild.id).then(setAllEntries)
    }
  }, [activeChild])
```

- [ ] **Step 5: Update `handleLifeMapEntry` to also add to `allEntries`**

Find `function handleLifeMapEntry(entry: LifeMapEntry)` and update it:

```typescript
  function handleLifeMapEntry(entry: LifeMapEntry) {
    setLifeMapEntries(prev => [entry, ...prev])
    setAllEntries(prev => [entry, ...prev])
  }
```

- [ ] **Step 6: Add year progress bar to top bar**

In the top bar div, after the `hidden sm:flex` XP/coins display, add:

```typescript
          {/* Year progress mini bar */}
          <div className="hidden md:flex items-center gap-2 bg-slate-100 rounded-xl px-3 py-1.5">
            <span className="text-xs text-slate-500">Year</span>
            <div className="w-16 h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all"
                style={{ width: `${yearProgress}%` }}
              />
            </div>
            <span className="text-xs font-bold text-emerald-700">{yearProgress}%</span>
          </div>
```

- [ ] **Step 7: Add Graduation and Portfolio buttons to top bar**

After the `🌟 Pass` button, add:

```typescript
          <button onClick={() => setOverlay('graduation' as any)}
            className="px-3 py-1.5 text-xs font-semibold bg-emerald-100 hover:bg-emerald-200 text-emerald-700 rounded-xl transition-all">
            🎓 Path
          </button>
          <button onClick={() => setOverlay('portfolio' as any)}
            className="px-3 py-1.5 text-xs font-semibold bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-xl transition-all">
            📁 Portfolio
          </button>
```

- [ ] **Step 8: Update Overlay type and add MiniWorld to chat layout**

Change:
```typescript
type Overlay = 'life_map' | 'season_pass' | null
```
To:
```typescript
type Overlay = 'life_map' | 'season_pass' | 'graduation' | 'portfolio' | null
```

In the main chat layout, find the `{/* Main content */}` div that contains the chat and room sidebar. Replace the room sidebar section (the `hidden lg:flex flex-col w-56` div) with this combined MiniWorld + room sidebar:

```typescript
        {/* Right panel — desktop: mini world + rooms */}
        <div className="hidden lg:flex flex-col w-64 bg-white border-l border-amber-100 shrink-0">
          {/* Mini world with avatar */}
          <div className="h-52 p-2 border-b border-amber-100">
            <MiniWorld
              avatarData={avatarData}
              playerName={playerName}
              onEnterRoom={(id) => enterRoom(id, 'mission')}
            />
          </div>

          {/* Room list */}
          <div className="flex-1 overflow-y-auto p-3 gap-2 flex flex-col">
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

            <div className="mt-auto pt-2 border-t border-slate-100">
              <button
                onClick={handleSignOut}
                className="w-full text-xs text-slate-400 hover:text-slate-600 py-2 rounded-lg hover:bg-slate-50 transition-all"
              >
                {isGuest ? 'Leave Game' : 'Sign Out'}
              </button>
            </div>
          </div>
        </div>
```

- [ ] **Step 9: Add overlay renders**

After the existing `{overlay === 'season_pass' && ...}` block, add:

```typescript
      {overlay === 'graduation' && (
        <GraduationTracker
          entries={allEntries}
          gradeBand={gradeBand}
          studentName={playerName}
          onClose={() => setOverlay(null)}
        />
      )}
      {overlay === 'portfolio' && (
        <Portfolio
          entries={allEntries}
          studentName={playerName}
          gradeBand={gradeBand}
          onClose={() => setOverlay(null)}
          onExport={() => { setOverlay(null); setShowTranscript(true) }}
        />
      )}
      {showTranscript && (
        <Transcript
          entries={allEntries}
          studentName={playerName}
          gradeBand={gradeBand}
          parentName={parentAccount?.display_name ?? 'Parent'}
          onClose={() => setShowTranscript(false)}
        />
      )}
```

- [ ] **Step 10: Commit**

```bash
git add src/pages/GameShell.tsx
git commit -m "feat: add MiniWorld to chat layout, graduation/portfolio/transcript overlays, year progress"
```

---

## Task 8: Grade Level Selection in CreateChildPage + ChildSelect

**Files:**
- Modify: `src/pages/CreateChildPage.tsx`
- Modify: `src/context/AuthContext.tsx`

Kids need to have a grade band set when their profile is created.

- [ ] **Step 1: Read `src/pages/CreateChildPage.tsx`**

- [ ] **Step 2: Add grade band selector to the form**

After the age input field, add:

```typescript
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Grade Level</label>
            <select
              value={gradeBand}
              onChange={e => setGradeBand(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 bg-white"
            >
              <option value="K-2">Kindergarten–2nd Grade</option>
              <option value="3-5">3rd–5th Grade</option>
              <option value="6-8">6th–8th Grade</option>
              <option value="9-12">9th–12th Grade (High School)</option>
            </select>
          </div>
```

Add `const [gradeBand, setGradeBand] = useState('K-2')` to the component state.

- [ ] **Step 3: Pass grade_level to addChild call**

Find the `addChild(displayName.trim(), username, parseInt(age) || 10)` call and change it to:
```typescript
const child = await addChild(displayName.trim(), username, parseInt(age) || 10, gradeBand)
```

- [ ] **Step 4: Update `addChild` in `AuthContext.tsx` to accept and save grade_level**

Read `src/context/AuthContext.tsx`. Find `async function addChild(displayName: string, username: string, age: number)` and update:

```typescript
  async function addChild(displayName: string, username: string, age: number, gradeBand: string = 'K-2'): Promise<StudentProfile> {
    if (!session) throw new Error('Not authenticated')
    const { data, error } = await supabase
      .from('aw_student_profiles')
      .insert({ parent_id: session.user.id, display_name: displayName, username, age, grade_level: gradeBand })
      .select()
      .single()
    if (error) throw error
    await refreshChildren()
    return data
  }
```

Also update the `AuthContextType` interface to match:
```typescript
  addChild: (displayName: string, username: string, age: number, gradeBand?: string) => Promise<StudentProfile>
```

- [ ] **Step 5: Commit**

```bash
git add src/pages/CreateChildPage.tsx src/context/AuthContext.tsx
git commit -m "feat: add grade level selection when creating child profile"
```

---

## Task 9: TypeScript Check + Push

- [ ] **Step 1: Run TypeScript check**

```bash
npx tsc --noEmit 2>&1
```

Fix any errors. Common issues:
- `Overlay` type doesn't include `'graduation'` or `'portfolio'` — already fixed in Task 7 Step 8, but verify
- `allEntries` combined from both DB and local `lifeMapEntries` — if type mismatch, cast
- `gradeBand` from `gradeBandFromAge()` returns `GradeBand | string` — cast explicitly with `as GradeBand`

- [ ] **Step 2: Commit fixes if needed**

```bash
git add -A
git commit -m "fix: TypeScript errors from Plan 4 implementation"
```

- [ ] **Step 3: Push**

```bash
git push origin adeline-world-plan-1
```

---

## Self-Review

**Spec coverage:**
- ✅ Grade-awareness (grade band on profile) — Tasks 1, 8
- ✅ Credit hours from Life Map entries — Tasks 1, 2
- ✅ Year-end credit goals per grade band — Tasks 1, 2, 3
- ✅ Graduation tracker (per-track progress) — Task 3
- ✅ Portfolio (accomplishments by track) — Task 4
- ✅ Exportable transcript (print/PDF) — Task 5
- ✅ Avatar visible on chat screen — Task 6 (MiniWorld)
- ✅ Avatar walks to room when selected — Task 6 (CSS transition)
- ✅ Year progress bar in top bar — Task 7
- ✅ Graduation + Portfolio + Transcript overlays — Task 7
- ✅ Life-to-credit keyword mapping — Task 1 (LIFE_TO_CREDIT)

**Type consistency:**
- `GradeBand` defined in Task 1, used in Tasks 2, 3, 4, 5, 7, 8 ✅
- `GRADE_EXPECTATIONS` defined in Task 1, used in academicEngine.ts Task 2 ✅
- `buildCreditSummary()` defined in Task 2, used in Tasks 3, 4, 5 ✅
- `checkGraduationEligible()` defined in Task 2, used in Tasks 3, 5 ✅
- `gradeBandFromAge()` defined in Task 2, used in Task 7 ✅
- `MiniWorld` props: `avatarData`, `playerName`, `onEnterRoom` — consistent between Task 6 definition and Task 7 usage ✅
- `GraduationTracker` props: `entries`, `gradeBand`, `studentName`, `onClose` — consistent ✅
- `Portfolio` props: `entries`, `studentName`, `gradeBand`, `onClose`, `onExport` — consistent ✅
- `Transcript` props: `entries`, `studentName`, `gradeBand`, `parentName`, `onClose` — consistent ✅
