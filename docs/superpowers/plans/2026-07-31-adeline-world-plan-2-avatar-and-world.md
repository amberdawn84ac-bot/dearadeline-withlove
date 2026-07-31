# Adeline World — Plan 2: Avatar Builder + 2D Hub World

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the GameShell placeholder with a real playable game: an avatar builder on first login, a 2D top-down hub world with keyboard movement, Adeline as a fixed NPC, two game room portals (Math Mines + Story Forest), and an in-game HUD showing XP and AdeCoins.

**Architecture:** CSS/SVG layered avatar system (no game engine — just React + CSS transforms). The 2D hub is a full-screen div with absolute-positioned elements and keyboard-driven player movement tracked in React state. Proximity detection (simple distance math) triggers room entry prompts. Adeline's portrait PNG is served from `/public/`. Auth context from Plan 1 provides player data.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, Vite, existing AuthContext (Plan 1), Supabase (already wired), Gemini via `/api/chat`

---

## File Structure

```
public/
  adeline_portrait.png          # Copy from Android assets — Adeline's fixed NPC image
  adeline_character.png         # Copy from Android assets — smaller sprite version

src/
  types/
    game.ts                     # AvatarData, RoomId, PlayerState, NPCConfig types (new)
  components/
    avatar/
      avatarLayers.ts           # Layer definitions: skin tones, hair styles/colors, outfits, accessories (new)
      AvatarRenderer.tsx        # Pure display: renders SVG avatar from AvatarData (new)
      AvatarBuilder.tsx         # Interactive customization UI with layer pickers (new)
    hud/
      GameHUD.tsx               # Fixed overlay: player name, XP bar, AdeCoins, room label, exit button (new)
    world/
      AdelineNPC.tsx            # Adeline portrait + speech bubble, click to chat (new)
      RoomPortal.tsx            # Labeled door/portal, glows when player is near (new)
      HubWorld.tsx              # 2D top-down scene: terrain, portals, NPC, player movement (new)
    rooms/
      MathMines.tsx             # Math Mines room: Gemini-powered math quest (new)
      StoryForest.tsx           # Story Forest room: Gemini-powered reading quest (new)
  pages/
    GameShell.tsx               # Modify: orchestrate avatar-builder-first → hub → rooms flow
```

---

## Task 1: Game Types

**Files:**
- Create: `src/types/game.ts`

- [ ] **Step 1: Create `src/types/game.ts`**

```typescript
export interface AvatarData {
  skinTone: string       // hex color e.g. '#F4C89A'
  hairStyle: 'short' | 'long' | 'curly' | 'braids' | 'ponytail'
  hairColor: string      // hex color
  eyeStyle: 'round' | 'almond' | 'wide'
  outfitId: 'red' | 'blue' | 'green' | 'purple' | 'orange' | 'teal'
  accessoryId: 'none' | 'hat' | 'bow' | 'crown'
}

export type RoomId = 'math_mines' | 'story_forest'

export interface PlayerState {
  x: number    // position in hub world (0-100, percentage of world width)
  y: number    // position in hub world (0-100, percentage of world height)
  facing: 'up' | 'down' | 'left' | 'right'
}

export interface Portal {
  id: RoomId
  label: string
  description: string
  x: number    // center x % in world
  y: number    // center y % in world
  color: string
  emoji: string
}

export const HUB_PORTALS: Portal[] = [
  {
    id: 'math_mines',
    label: 'Math Mines',
    description: 'Dig for answers in the mines of numbers',
    x: 25,
    y: 40,
    color: '#1e3a5f',
    emoji: '⛏️'
  },
  {
    id: 'story_forest',
    label: 'Story Forest',
    description: 'Where words grow wild and tales come alive',
    x: 72,
    y: 35,
    color: '#14532d',
    emoji: '🌲'
  }
]

export const DEFAULT_AVATAR: AvatarData = {
  skinTone: '#F4C89A',
  hairStyle: 'short',
  hairColor: '#3D2314',
  eyeStyle: 'round',
  outfitId: 'blue',
  accessoryId: 'none'
}
```

- [ ] **Step 2: Commit**

```bash
git add src/types/game.ts
git commit -m "feat: add game types - AvatarData, PlayerState, Portal, RoomId"
```

---

## Task 2: Avatar Layer Definitions + AvatarRenderer

**Files:**
- Create: `src/components/avatar/avatarLayers.ts`
- Create: `src/components/avatar/AvatarRenderer.tsx`

- [ ] **Step 1: Create `src/components/avatar/avatarLayers.ts`**

```typescript
import { AvatarData } from '../../types/game'

export const SKIN_TONES = [
  { label: 'Porcelain', value: '#FDDBB4' },
  { label: 'Fair',      value: '#F4C89A' },
  { label: 'Medium',    value: '#D4956A' },
  { label: 'Tan',       value: '#C07A4A' },
  { label: 'Deep',      value: '#7D4E2A' },
  { label: 'Rich',      value: '#4A2810' },
]

export const HAIR_COLORS = [
  { label: 'Black',     value: '#1A0A00' },
  { label: 'Dark Brown',value: '#3D2314' },
  { label: 'Brown',     value: '#6B3A2A' },
  { label: 'Auburn',    value: '#922B21' },
  { label: 'Blonde',    value: '#D4A843' },
  { label: 'Strawberry',value: '#E8735A' },
  { label: 'Red',       value: '#C0392B' },
  { label: 'Silver',    value: '#BDC3C7' },
  { label: 'White',     value: '#ECF0F1' },
  { label: 'Blue',      value: '#2980B9' },
  { label: 'Purple',    value: '#8E44AD' },
  { label: 'Pink',      value: '#E91E8C' },
  { label: 'Teal',      value: '#16A085' },
]

export const HAIR_STYLES: { id: AvatarData['hairStyle']; label: string }[] = [
  { id: 'short',    label: 'Short' },
  { id: 'long',     label: 'Long' },
  { id: 'curly',    label: 'Curly' },
  { id: 'braids',   label: 'Braids' },
  { id: 'ponytail', label: 'Ponytail' },
]

export const EYE_STYLES: { id: AvatarData['eyeStyle']; label: string }[] = [
  { id: 'round',  label: 'Round' },
  { id: 'almond', label: 'Almond' },
  { id: 'wide',   label: 'Wide' },
]

export const OUTFITS: { id: AvatarData['outfitId']; label: string; color: string; accent: string }[] = [
  { id: 'red',    label: 'Red',    color: '#E74C3C', accent: '#C0392B' },
  { id: 'blue',   label: 'Blue',   color: '#3498DB', accent: '#2980B9' },
  { id: 'green',  label: 'Green',  color: '#27AE60', accent: '#1E8449' },
  { id: 'purple', label: 'Purple', color: '#9B59B6', accent: '#7D3C98' },
  { id: 'orange', label: 'Orange', color: '#E67E22', accent: '#CA6F1E' },
  { id: 'teal',   label: 'Teal',   color: '#16A085', accent: '#0E6655' },
]

export const ACCESSORIES: { id: AvatarData['accessoryId']; label: string; emoji: string }[] = [
  { id: 'none',  label: 'None',  emoji: '∅' },
  { id: 'hat',   label: 'Hat',   emoji: '🎩' },
  { id: 'bow',   label: 'Bow',   emoji: '🎀' },
  { id: 'crown', label: 'Crown', emoji: '👑' },
]

export function getOutfit(id: AvatarData['outfitId']) {
  return OUTFITS.find(o => o.id === id) ?? OUTFITS[1]
}
```

- [ ] **Step 2: Create `src/components/avatar/AvatarRenderer.tsx`**

This is an inline SVG avatar — 100×120px, composed of layered shapes.

```typescript
import { AvatarData } from '../../types/game'
import { getOutfit } from './avatarLayers'

interface Props {
  avatar: AvatarData
  size?: number   // width in px, height scales proportionally (×1.2)
  className?: string
}

// SVG hair paths per style (viewBox 0 0 100 120)
function HairShape({ style, color }: { style: AvatarData['hairStyle']; color: string }) {
  switch (style) {
    case 'short':
      return <ellipse cx="50" cy="32" rx="26" ry="18" fill={color} />
    case 'long':
      return (
        <g fill={color}>
          <ellipse cx="50" cy="30" rx="26" ry="18" />
          <rect x="24" y="38" width="8" height="45" rx="4" />
          <rect x="68" y="38" width="8" height="45" rx="4" />
        </g>
      )
    case 'curly':
      return (
        <g fill={color}>
          <ellipse cx="50" cy="28" rx="30" ry="22" />
          <ellipse cx="22" cy="42" rx="10" ry="12" />
          <ellipse cx="78" cy="42" rx="10" ry="12" />
        </g>
      )
    case 'braids':
      return (
        <g fill={color}>
          <ellipse cx="50" cy="30" rx="26" ry="18" />
          <rect x="26" y="44" width="7" height="50" rx="3" />
          <rect x="67" y="44" width="7" height="50" rx="3" />
          <ellipse cx="29" cy="96" rx="5" ry="4" />
          <ellipse cx="71" cy="96" rx="5" ry="4" />
        </g>
      )
    case 'ponytail':
      return (
        <g fill={color}>
          <ellipse cx="50" cy="30" rx="26" ry="18" />
          <ellipse cx="74" cy="28" rx="8" ry="6" />
          <rect x="72" y="28" width="6" height="30" rx="3" />
          <ellipse cx="75" cy="60" rx="6" ry="5" />
        </g>
      )
  }
}

function EyeShape({ style }: { style: AvatarData['eyeStyle'] }) {
  switch (style) {
    case 'round':
      return (
        <g fill="#1a1a2e">
          <circle cx="38" cy="55" r="5" />
          <circle cx="62" cy="55" r="5" />
          <circle cx="40" cy="53" r="1.5" fill="white" />
          <circle cx="64" cy="53" r="1.5" fill="white" />
        </g>
      )
    case 'almond':
      return (
        <g fill="#1a1a2e">
          <ellipse cx="38" cy="55" rx="6" ry="4" />
          <ellipse cx="62" cy="55" rx="6" ry="4" />
          <circle cx="40" cy="54" r="1.5" fill="white" />
          <circle cx="64" cy="54" r="1.5" fill="white" />
        </g>
      )
    case 'wide':
      return (
        <g fill="#1a1a2e">
          <circle cx="38" cy="55" r="6.5" />
          <circle cx="62" cy="55" r="6.5" />
          <circle cx="40" cy="52" r="2" fill="white" />
          <circle cx="64" cy="52" r="2" fill="white" />
        </g>
      )
  }
}

function AccessoryShape({ id, hairColor }: { id: AvatarData['accessoryId']; hairColor: string }) {
  switch (id) {
    case 'hat':
      return (
        <g fill={hairColor}>
          <rect x="24" y="18" width="52" height="8" rx="3" />
          <rect x="32" y="5" width="36" height="16" rx="4" />
        </g>
      )
    case 'bow':
      return (
        <g fill="#E91E8C">
          <ellipse cx="35" cy="16" rx="10" ry="7" />
          <ellipse cx="65" cy="16" rx="10" ry="7" />
          <circle cx="50" cy="16" r="5" />
        </g>
      )
    case 'crown':
      return (
        <g fill="#F1C40F">
          <rect x="28" y="18" width="44" height="8" rx="2" />
          <polygon points="28,18 35,6 42,18" />
          <polygon points="43,18 50,6 57,18" />
          <polygon points="58,18 65,6 72,18" />
        </g>
      )
    case 'none':
    default:
      return null
  }
}

export default function AvatarRenderer({ avatar, size = 80, className = '' }: Props) {
  const outfit = getOutfit(avatar.outfitId)
  const width = size
  const height = Math.round(size * 1.2)

  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 100 120"
      className={className}
      aria-label="Player avatar"
    >
      {/* Body / outfit */}
      <rect x="28" y="78" width="44" height="38" rx="8" fill={outfit.color} />
      {/* Outfit accent (collar) */}
      <rect x="42" y="78" width="16" height="12" rx="4" fill={outfit.accent} />

      {/* Neck */}
      <rect x="44" y="70" width="12" height="12" rx="4" fill={avatar.skinTone} />

      {/* Head */}
      <ellipse cx="50" cy="50" rx="26" ry="28" fill={avatar.skinTone} />

      {/* Hair (behind face overlay for short styles) */}
      <HairShape style={avatar.hairStyle} color={avatar.hairColor} />

      {/* Face details — ears */}
      <ellipse cx="24" cy="52" rx="4" ry="6" fill={avatar.skinTone} />
      <ellipse cx="76" cy="52" rx="4" ry="6" fill={avatar.skinTone} />

      {/* Eyes */}
      <EyeShape style={avatar.eyeStyle} />

      {/* Nose */}
      <ellipse cx="50" cy="62" rx="3" ry="2" fill="rgba(0,0,0,0.12)" />

      {/* Smile */}
      <path d="M 40 68 Q 50 75 60 68" stroke="rgba(0,0,0,0.25)" strokeWidth="2" fill="none" strokeLinecap="round" />

      {/* Accessory (on top of hair) */}
      <AccessoryShape id={avatar.accessoryId} hairColor={avatar.hairColor} />
    </svg>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/avatar/avatarLayers.ts src/components/avatar/AvatarRenderer.tsx
git commit -m "feat: add avatar layer definitions and SVG renderer"
```

---

## Task 3: Avatar Builder

**Files:**
- Create: `src/components/avatar/AvatarBuilder.tsx`

- [ ] **Step 1: Create `src/components/avatar/AvatarBuilder.tsx`**

```typescript
import { useState } from 'react'
import { AvatarData, DEFAULT_AVATAR } from '../../types/game'
import {
  SKIN_TONES, HAIR_COLORS, HAIR_STYLES,
  EYE_STYLES, OUTFITS, ACCESSORIES, getOutfit
} from './avatarLayers'
import AvatarRenderer from './AvatarRenderer'

interface Props {
  initialAvatar?: AvatarData
  playerName: string
  onSave: (avatar: AvatarData) => void
}

type Tab = 'skin' | 'hair' | 'eyes' | 'outfit' | 'accessory'

const TABS: { id: Tab; label: string; emoji: string }[] = [
  { id: 'skin',      label: 'Skin',      emoji: '🎨' },
  { id: 'hair',      label: 'Hair',      emoji: '💇' },
  { id: 'eyes',      label: 'Eyes',      emoji: '👀' },
  { id: 'outfit',    label: 'Outfit',    emoji: '👕' },
  { id: 'accessory', label: 'Extra',     emoji: '✨' },
]

export default function AvatarBuilder({ initialAvatar, playerName, onSave }: Props) {
  const [avatar, setAvatar] = useState<AvatarData>(initialAvatar ?? DEFAULT_AVATAR)
  const [activeTab, setActiveTab] = useState<Tab>('skin')

  function set<K extends keyof AvatarData>(key: K, value: AvatarData[K]) {
    setAvatar(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-900 via-purple-800 to-indigo-900 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white/10 backdrop-blur rounded-3xl p-6 space-y-6">

        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white font-serif">Build Your Avatar</h1>
          <p className="text-purple-200 text-sm mt-1">Hey {playerName}, make it yours!</p>
        </div>

        {/* Preview */}
        <div className="flex justify-center">
          <div className="bg-white/20 rounded-2xl p-6 flex flex-col items-center gap-3">
            <AvatarRenderer avatar={avatar} size={120} />
            <span className="text-white font-semibold text-sm">{playerName}</span>
          </div>
        </div>

        {/* Tab Nav */}
        <div className="flex gap-2 overflow-x-auto pb-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-shrink-0 flex flex-col items-center gap-1 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === tab.id
                  ? 'bg-white text-purple-900'
                  : 'bg-white/20 text-white hover:bg-white/30'
              }`}
            >
              <span className="text-lg">{tab.emoji}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="min-h-[140px]">

          {activeTab === 'skin' && (
            <div>
              <p className="text-purple-200 text-xs font-semibold uppercase tracking-wider mb-3">Skin Tone</p>
              <div className="flex flex-wrap gap-3">
                {SKIN_TONES.map(tone => (
                  <button
                    key={tone.value}
                    onClick={() => set('skinTone', tone.value)}
                    title={tone.label}
                    className={`w-10 h-10 rounded-full border-4 transition-all ${
                      avatar.skinTone === tone.value ? 'border-white scale-110' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: tone.value }}
                  />
                ))}
              </div>
            </div>
          )}

          {activeTab === 'hair' && (
            <div className="space-y-4">
              <div>
                <p className="text-purple-200 text-xs font-semibold uppercase tracking-wider mb-3">Style</p>
                <div className="flex flex-wrap gap-2">
                  {HAIR_STYLES.map(style => (
                    <button
                      key={style.id}
                      onClick={() => set('hairStyle', style.id)}
                      className={`px-3 py-2 rounded-xl text-sm font-semibold transition-all ${
                        avatar.hairStyle === style.id
                          ? 'bg-white text-purple-900'
                          : 'bg-white/20 text-white hover:bg-white/30'
                      }`}
                    >
                      {style.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-purple-200 text-xs font-semibold uppercase tracking-wider mb-3">Color</p>
                <div className="flex flex-wrap gap-2">
                  {HAIR_COLORS.map(color => (
                    <button
                      key={color.value}
                      onClick={() => set('hairColor', color.value)}
                      title={color.label}
                      className={`w-8 h-8 rounded-full border-3 transition-all ${
                        avatar.hairColor === color.value ? 'border-white scale-110' : 'border-transparent'
                      }`}
                      style={{ backgroundColor: color.value }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'eyes' && (
            <div>
              <p className="text-purple-200 text-xs font-semibold uppercase tracking-wider mb-3">Eye Style</p>
              <div className="flex gap-3">
                {EYE_STYLES.map(style => (
                  <button
                    key={style.id}
                    onClick={() => set('eyeStyle', style.id)}
                    className={`flex-1 py-3 rounded-xl text-sm font-semibold transition-all ${
                      avatar.eyeStyle === style.id
                        ? 'bg-white text-purple-900'
                        : 'bg-white/20 text-white hover:bg-white/30'
                    }`}
                  >
                    {style.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'outfit' && (
            <div>
              <p className="text-purple-200 text-xs font-semibold uppercase tracking-wider mb-3">Outfit Color</p>
              <div className="flex flex-wrap gap-3">
                {OUTFITS.map(outfit => (
                  <button
                    key={outfit.id}
                    onClick={() => set('outfitId', outfit.id)}
                    title={outfit.label}
                    className={`w-12 h-12 rounded-xl border-4 transition-all flex items-center justify-center ${
                      avatar.outfitId === outfit.id ? 'border-white scale-110' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: outfit.color }}
                  >
                    {avatar.outfitId === outfit.id && (
                      <span className="text-white text-lg">✓</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'accessory' && (
            <div>
              <p className="text-purple-200 text-xs font-semibold uppercase tracking-wider mb-3">Accessory</p>
              <div className="flex flex-wrap gap-2">
                {ACCESSORIES.map(acc => (
                  <button
                    key={acc.id}
                    onClick={() => set('accessoryId', acc.id)}
                    className={`flex flex-col items-center gap-1 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                      avatar.accessoryId === acc.id
                        ? 'bg-white text-purple-900'
                        : 'bg-white/20 text-white hover:bg-white/30'
                    }`}
                  >
                    <span className="text-2xl">{acc.emoji}</span>
                    {acc.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Save Button */}
        <button
          onClick={() => onSave(avatar)}
          className="w-full py-4 bg-amber-500 hover:bg-amber-400 text-white font-bold text-lg rounded-2xl transition-all shadow-lg shadow-amber-500/30"
        >
          Enter Adeline World! →
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/avatar/AvatarBuilder.tsx
git commit -m "feat: add AvatarBuilder with skin/hair/eyes/outfit/accessory tabs"
```

---

## Task 4: Game HUD

**Files:**
- Create: `src/components/hud/GameHUD.tsx`

- [ ] **Step 1: Create `src/components/hud/GameHUD.tsx`**

```typescript
import { StudentProfile } from '../../types/auth'
import { GuestSession, AvatarData } from '../../types/game'
import AvatarRenderer from '../avatar/AvatarRenderer'

// GuestSession from types/auth doesn't have AvatarData — we pass it separately
interface Props {
  player: StudentProfile | null
  guestSession: GuestSession | null
  avatarData: AvatarData
  roomLabel?: string    // shown when inside a room (undefined = in hub)
  onExitRoom?: () => void
  onSignOut: () => void
}

export default function GameHUD({ player, guestSession, avatarData, roomLabel, onExitRoom, onSignOut }: Props) {
  const name = player?.display_name ?? guestSession?.displayName ?? 'Explorer'
  const xp = player?.xp ?? guestSession?.xp ?? 0
  const coins = player?.ade_coins ?? guestSession?.adeCoins ?? 0
  const xpMax = 500  // XP needed to level up (simplified for MVP)
  const xpPct = Math.min(100, Math.round((xp % xpMax) / xpMax * 100))

  return (
    <div className="fixed top-0 left-0 right-0 z-50 pointer-events-none">
      <div className="flex items-start justify-between p-3 gap-3">

        {/* Left: Player info */}
        <div className="bg-black/70 backdrop-blur rounded-2xl px-3 py-2 flex items-center gap-3 pointer-events-auto">
          <AvatarRenderer avatar={avatarData} size={36} />
          <div>
            <p className="text-white font-bold text-sm leading-tight">{name}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <div className="w-20 h-2 bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-400 rounded-full transition-all duration-500"
                  style={{ width: `${xpPct}%` }}
                />
              </div>
              <span className="text-amber-300 text-xs font-semibold">{xp} XP</span>
            </div>
          </div>
        </div>

        {/* Center: Room label (only when in a room) */}
        {roomLabel && (
          <div className="bg-black/70 backdrop-blur rounded-2xl px-4 py-2 text-center">
            <p className="text-white font-bold text-sm">{roomLabel}</p>
          </div>
        )}

        {/* Right: Coins + controls */}
        <div className="flex flex-col items-end gap-2 pointer-events-auto">
          <div className="bg-black/70 backdrop-blur rounded-2xl px-3 py-2 flex items-center gap-2">
            <span className="text-lg">🪙</span>
            <span className="text-amber-300 font-bold text-sm">{coins}</span>
          </div>
          {onExitRoom ? (
            <button
              onClick={onExitRoom}
              className="bg-black/70 backdrop-blur rounded-xl px-3 py-1.5 text-white text-xs font-semibold hover:bg-white/20 transition-all"
            >
              ← Hub
            </button>
          ) : (
            <button
              onClick={onSignOut}
              className="bg-black/70 backdrop-blur rounded-xl px-3 py-1.5 text-white/60 text-xs hover:text-white transition-all"
            >
              Exit
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/hud/GameHUD.tsx
git commit -m "feat: add GameHUD with XP bar, AdeCoins, room label, exit button"
```

---

## Task 5: Copy Adeline Assets + AdelineNPC Component

**Files:**
- Create: `public/adeline_portrait.png` (copy from Android assets)
- Create: `public/adeline_character.png` (copy from Android assets)
- Create: `src/components/world/AdelineNPC.tsx`

- [ ] **Step 1: Copy Adeline's images to public folder**

```bash
mkdir -p public
cp app/src/main/res/drawable/adeline_original.png public/adeline_portrait.png
cp app/src/main/res/drawable-xxhdpi/adeline_character.png public/adeline_character.png
```

Verify:
```bash
ls -lh public/
```
Expected: two PNG files listed.

- [ ] **Step 2: Create `src/components/world/AdelineNPC.tsx`**

```typescript
import { useState } from 'react'

interface Props {
  x: number    // % position in world
  y: number    // % position in world
  onChat: () => void
}

export default function AdelineNPC({ x, y, onChat }: Props) {
  const [showPrompt, setShowPrompt] = useState(false)

  return (
    <div
      className="absolute flex flex-col items-center cursor-pointer group"
      style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }}
      onMouseEnter={() => setShowPrompt(true)}
      onMouseLeave={() => setShowPrompt(false)}
      onClick={onChat}
    >
      {/* Speech bubble */}
      {showPrompt && (
        <div className="absolute -top-16 left-1/2 -translate-x-1/2 bg-white rounded-2xl px-3 py-2 shadow-lg whitespace-nowrap z-10">
          <p className="text-xs font-semibold text-slate-700">Talk to Adeline</p>
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-white" />
        </div>
      )}

      {/* Adeline's portrait */}
      <div className="w-16 h-16 rounded-full border-4 border-amber-400 shadow-xl overflow-hidden group-hover:border-amber-300 transition-all group-hover:scale-105">
        <img
          src="/adeline_portrait.png"
          alt="Adeline"
          className="w-full h-full object-cover"
          onError={e => {
            // Fallback if image doesn't load
            const target = e.currentTarget
            target.style.display = 'none'
            target.parentElement!.style.backgroundColor = '#D97706'
            target.parentElement!.innerHTML = '<span style="color:white;font-size:24px;display:flex;align-items:center;justify-content:center;height:100%">A</span>'
          }}
        />
      </div>
      <span className="text-white text-xs font-bold mt-1 bg-black/50 px-2 py-0.5 rounded-full">Adeline</span>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add public/ src/components/world/AdelineNPC.tsx
git commit -m "feat: add Adeline NPC with portrait assets and hover chat prompt"
```

---

## Task 6: Room Portal Component

**Files:**
- Create: `src/components/world/RoomPortal.tsx`

- [ ] **Step 1: Create `src/components/world/RoomPortal.tsx`**

```typescript
import { Portal } from '../../types/game'

interface Props {
  portal: Portal
  isNearby: boolean    // player is close enough to enter
  onEnter: () => void
}

export default function RoomPortal({ portal, isNearby, onEnter }: Props) {
  return (
    <div
      className="absolute flex flex-col items-center"
      style={{ left: `${portal.x}%`, top: `${portal.y}%`, transform: 'translate(-50%, -50%)' }}
    >
      {/* Entry prompt */}
      {isNearby && (
        <div className="absolute -top-14 left-1/2 -translate-x-1/2 whitespace-nowrap z-10 animate-bounce">
          <button
            onClick={onEnter}
            className="bg-white text-slate-800 text-xs font-bold px-3 py-1.5 rounded-full shadow-lg hover:bg-amber-50 transition-all"
          >
            Press E to enter →
          </button>
        </div>
      )}

      {/* Portal door */}
      <div
        className={`relative cursor-pointer transition-all duration-300 ${isNearby ? 'scale-110' : 'hover:scale-105'}`}
        onClick={isNearby ? onEnter : undefined}
      >
        {/* Door frame */}
        <div
          className="w-20 h-28 rounded-t-full border-4 flex flex-col items-center justify-center gap-1 shadow-2xl"
          style={{
            backgroundColor: portal.color,
            borderColor: isNearby ? '#FBBF24' : 'rgba(255,255,255,0.3)',
            boxShadow: isNearby ? `0 0 20px ${portal.color}` : undefined
          }}
        >
          <span className="text-3xl">{portal.emoji}</span>
        </div>

        {/* Door step */}
        <div
          className="w-24 h-3 rounded-b-lg -mt-1"
          style={{ backgroundColor: portal.color, filter: 'brightness(0.7)' }}
        />
      </div>

      {/* Label */}
      <div className="mt-2 text-center">
        <p className="text-white font-bold text-sm drop-shadow">{portal.label}</p>
        <p className="text-white/70 text-xs drop-shadow">{portal.description}</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/world/RoomPortal.tsx
git commit -m "feat: add RoomPortal with proximity glow and entry prompt"
```

---

## Task 7: Hub World (2D Scene + Player Movement)

**Files:**
- Create: `src/components/world/HubWorld.tsx`

- [ ] **Step 1: Create `src/components/world/HubWorld.tsx`**

```typescript
import { useState, useEffect, useCallback, useRef } from 'react'
import { AvatarData, PlayerState, Portal, HUB_PORTALS, RoomId } from '../../types/game'
import AvatarRenderer from '../avatar/AvatarRenderer'
import AdelineNPC from './AdelineNPC'
import RoomPortal from './RoomPortal'

const ADELINE_X = 50
const ADELINE_Y = 60
const MOVE_SPEED = 1.5    // % per keypress
const PROXIMITY = 12      // % distance to trigger portal glow
const CHAT_PROXIMITY = 10 // % distance to trigger Adeline chat

interface Props {
  avatarData: AvatarData
  playerName: string
  onEnterRoom: (roomId: RoomId) => void
  onChatAdeline: () => void
}

function distance(ax: number, ay: number, bx: number, by: number) {
  return Math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)
}

export default function HubWorld({ avatarData, playerName, onEnterRoom, onChatAdeline }: Props) {
  const [player, setPlayer] = useState<PlayerState>({ x: 50, y: 75, facing: 'up' })
  const keysPressed = useRef<Set<string>>(new Set())
  const animFrame = useRef<number>()

  const movePlayer = useCallback(() => {
    setPlayer(prev => {
      let { x, y, facing } = prev
      if (keysPressed.current.has('ArrowUp')    || keysPressed.current.has('w') || keysPressed.current.has('W')) { y -= MOVE_SPEED; facing = 'up' }
      if (keysPressed.current.has('ArrowDown')  || keysPressed.current.has('s') || keysPressed.current.has('S')) { y += MOVE_SPEED; facing = 'down' }
      if (keysPressed.current.has('ArrowLeft')  || keysPressed.current.has('a') || keysPressed.current.has('A')) { x -= MOVE_SPEED; facing = 'left' }
      if (keysPressed.current.has('ArrowRight') || keysPressed.current.has('d') || keysPressed.current.has('D')) { x += MOVE_SPEED; facing = 'right' }
      x = Math.max(3, Math.min(97, x))
      y = Math.max(10, Math.min(95, y))
      return { x, y, facing }
    })
    animFrame.current = requestAnimationFrame(movePlayer)
  }, [])

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      keysPressed.current.add(e.key)
      // Enter room with E key
      if (e.key === 'e' || e.key === 'E') {
        for (const portal of HUB_PORTALS) {
          if (distance(player.x, player.y, portal.x, portal.y) < PROXIMITY) {
            onEnterRoom(portal.id)
            return
          }
        }
        if (distance(player.x, player.y, ADELINE_X, ADELINE_Y) < CHAT_PROXIMITY) {
          onChatAdeline()
        }
      }
    }
    function onKeyUp(e: KeyboardEvent) {
      keysPressed.current.delete(e.key)
    }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    animFrame.current = requestAnimationFrame(movePlayer)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
      if (animFrame.current) cancelAnimationFrame(animFrame.current)
    }
  }, [movePlayer, onEnterRoom, onChatAdeline, player.x, player.y])

  const nearbyPortal = HUB_PORTALS.find(p => distance(player.x, player.y, p.x, p.y) < PROXIMITY)
  const nearAdeline = distance(player.x, player.y, ADELINE_X, ADELINE_Y) < CHAT_PROXIMITY

  return (
    <div className="relative w-full h-full overflow-hidden select-none" style={{ background: 'linear-gradient(180deg, #87CEEB 0%, #90EE90 40%, #228B22 100%)' }}>

      {/* Sky */}
      <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #87CEEB 0%, #b0e0ff 30%)' }} />

      {/* Ground */}
      <div className="absolute bottom-0 left-0 right-0" style={{ height: '65%', background: 'linear-gradient(180deg, #5DBB5D 0%, #228B22 100%)' }} />

      {/* Path/walkway */}
      <div className="absolute" style={{ left: '30%', top: '35%', width: '40%', height: '55%', background: 'rgba(210,180,140,0.6)', borderRadius: '8px' }} />

      {/* Trees decoration */}
      {[{x:8,y:45},{x:15,y:55},{x:85,y:48},{x:90,y:58},{x:5,y:70},{x:93,y:65}].map((t,i) => (
        <div key={i} className="absolute" style={{ left: `${t.x}%`, top: `${t.y}%` }}>
          <div style={{ width: 24, height: 30, background: '#1a6b1a', borderRadius: '50% 50% 30% 30%', marginLeft: -12 }} />
          <div style={{ width: 6, height: 14, background: '#5D4037', marginLeft: -3 }} />
        </div>
      ))}

      {/* Hub sign */}
      <div className="absolute" style={{ left: '50%', top: '22%', transform: 'translateX(-50%)' }}>
        <div className="bg-amber-800 text-amber-100 font-bold text-sm px-4 py-2 rounded-lg shadow-lg border-2 border-amber-600">
          🏘️ Adeline Hub
        </div>
      </div>

      {/* Adeline NPC */}
      <AdelineNPC
        x={ADELINE_X}
        y={ADELINE_Y}
        onChat={onChatAdeline}
      />

      {/* Room portals */}
      {HUB_PORTALS.map(portal => (
        <RoomPortal
          key={portal.id}
          portal={portal}
          isNearby={nearbyPortal?.id === portal.id}
          onEnter={() => onEnterRoom(portal.id)}
        />
      ))}

      {/* Player character */}
      <div
        className="absolute transition-none"
        style={{
          left: `${player.x}%`,
          top: `${player.y}%`,
          transform: 'translate(-50%, -50%)',
          filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.4))',
          zIndex: 20
        }}
      >
        <AvatarRenderer avatar={avatarData} size={56} />
        <p className="text-white text-xs font-bold text-center mt-1 drop-shadow bg-black/40 rounded-full px-2">{playerName}</p>
      </div>

      {/* Controls hint */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/50 text-white text-xs px-3 py-1.5 rounded-full">
        WASD / Arrow keys to move · E to enter
      </div>

      {/* Chat nudge when near Adeline */}
      {nearAdeline && (
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 bg-amber-500 text-white text-xs font-bold px-4 py-2 rounded-full shadow-lg animate-bounce">
          Press E to talk to Adeline
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/world/HubWorld.tsx
git commit -m "feat: add 2D HubWorld with WASD movement, NPC, portals, proximity detection"
```

---

## Task 8: Math Mines Room

**Files:**
- Create: `src/components/rooms/MathMines.tsx`

- [ ] **Step 1: Create `src/components/rooms/MathMines.tsx`**

```typescript
import { useState, useEffect } from 'react'
import { AvatarData } from '../../types/game'

interface Props {
  playerName: string
  avatarData: AvatarData
  geminiApiKey?: string
  onXpEarned: (amount: number) => void
  onCoinsEarned: (amount: number) => void
}

interface Quest {
  question: string
  answer: string
  hint: string
  xpReward: number
  coinReward: number
}

// Fallback quests if Gemini is unavailable
const FALLBACK_QUESTS: Quest[] = [
  { question: "Farmer Adeline has 3 rows of corn with 7 plants in each row. How many corn plants does she have?", answer: "21", hint: "Try 3 × 7", xpReward: 25, coinReward: 5 },
  { question: "You need to can 48 jars of tomatoes in groups of 6. How many groups is that?", answer: "8", hint: "Try 48 ÷ 6", xpReward: 25, coinReward: 5 },
  { question: "The sheep produce 5 pounds of wool each week. How much wool in 4 weeks?", answer: "20", hint: "Try 5 × 4", xpReward: 30, coinReward: 8 },
  { question: "You have 100 square feet of garden. You use 35 for tomatoes and 28 for squash. How much is left?", answer: "37", hint: "100 - 35 - 28", xpReward: 35, coinReward: 10 },
]

export default function MathMines({ playerName, onXpEarned, onCoinsEarned }: Props) {
  const [quest, setQuest] = useState<Quest | null>(null)
  const [userAnswer, setUserAnswer] = useState('')
  const [feedback, setFeedback] = useState<'correct' | 'wrong' | null>(null)
  const [showHint, setShowHint] = useState(false)
  const [questIndex, setQuestIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [streak, setStreak] = useState(0)

  useEffect(() => {
    loadQuest()
  }, [questIndex])

  async function loadQuest() {
    setLoading(true)
    setFeedback(null)
    setUserAnswer('')
    setShowHint(false)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create ONE math word problem for a homeschool student. It should involve real-world homesteading, farming, cooking, or building. Make it fun and short (2 sentences max). Also provide: the numeric answer, a one-sentence hint, and reward values (xpReward between 20-50, coinReward between 5-15). Respond ONLY with valid JSON in this exact format: {"question":"...","answer":"...","hint":"...","xpReward":25,"coinReward":8}`,
          history: []
        })
      })
      const data = await response.json()
      const parsed = JSON.parse(data.reply.replace(/```json|```/g, '').trim())
      if (parsed.question && parsed.answer) {
        setQuest(parsed)
      } else {
        throw new Error('Invalid format')
      }
    } catch {
      setQuest(FALLBACK_QUESTS[questIndex % FALLBACK_QUESTS.length])
    } finally {
      setLoading(false)
    }
  }

  function checkAnswer() {
    if (!quest) return
    const correct = userAnswer.trim().replace(/[^0-9.]/g, '') === quest.answer.replace(/[^0-9.]/g, '')
    setFeedback(correct ? 'correct' : 'wrong')
    if (correct) {
      const bonus = streak >= 2 ? Math.round(quest.xpReward * 0.5) : 0
      onXpEarned(quest.xpReward + bonus)
      onCoinsEarned(quest.coinReward)
      setStreak(s => s + 1)
    } else {
      setStreak(0)
    }
  }

  function nextQuest() {
    setQuestIndex(i => i + 1)
  }

  return (
    <div className="h-full flex flex-col" style={{ background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)' }}>

      {/* Room header */}
      <div className="flex items-center gap-3 p-4 border-b border-white/10">
        <span className="text-3xl">⛏️</span>
        <div>
          <h2 className="text-white font-bold text-lg">Math Mines</h2>
          <p className="text-blue-300 text-xs">Dig for answers, {playerName}!</p>
        </div>
        {streak >= 2 && (
          <div className="ml-auto bg-amber-500/20 border border-amber-400 text-amber-300 text-xs font-bold px-3 py-1 rounded-full">
            🔥 {streak} streak!
          </div>
        )}
      </div>

      {/* Quest area */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-6">

        {loading ? (
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-blue-300 text-sm">Adeline is preparing your quest...</p>
          </div>
        ) : quest ? (
          <>
            {/* Quest card */}
            <div className="w-full max-w-md bg-white/10 backdrop-blur rounded-2xl p-6 space-y-4 border border-white/20">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-sm">⚡</span>
                </div>
                <p className="text-white text-base leading-relaxed">{quest.question}</p>
              </div>

              {showHint && (
                <div className="bg-amber-500/20 border border-amber-400/40 rounded-xl p-3">
                  <p className="text-amber-300 text-sm">💡 Hint: {quest.hint}</p>
                </div>
              )}
            </div>

            {/* Answer input */}
            {feedback === null && (
              <div className="w-full max-w-md space-y-3">
                <input
                  type="text"
                  value={userAnswer}
                  onChange={e => setUserAnswer(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && checkAnswer()}
                  placeholder="Your answer..."
                  className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-xl text-white placeholder-white/40 text-center text-xl font-bold focus:outline-none focus:border-amber-400"
                  autoFocus
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => setShowHint(true)}
                    className="flex-1 py-2 bg-white/10 hover:bg-white/20 text-white/70 text-sm rounded-xl transition-all"
                  >
                    Need a hint?
                  </button>
                  <button
                    onClick={checkAnswer}
                    disabled={!userAnswer.trim()}
                    className="flex-1 py-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-white font-bold rounded-xl transition-all"
                  >
                    Submit →
                  </button>
                </div>
              </div>
            )}

            {/* Feedback */}
            {feedback === 'correct' && (
              <div className="w-full max-w-md bg-emerald-500/20 border border-emerald-400 rounded-2xl p-5 text-center space-y-3">
                <p className="text-4xl">🎉</p>
                <p className="text-emerald-300 font-bold text-lg">Correct!</p>
                <p className="text-white/70 text-sm">+{quest.xpReward} XP · +{quest.coinReward} AdeCoins</p>
                {streak >= 2 && <p className="text-amber-300 text-xs">🔥 Streak bonus! +{Math.round(quest.xpReward * 0.5)} XP</p>}
                <button
                  onClick={nextQuest}
                  className="w-full py-2 bg-emerald-500 hover:bg-emerald-400 text-white font-bold rounded-xl"
                >
                  Next Quest →
                </button>
              </div>
            )}

            {feedback === 'wrong' && (
              <div className="w-full max-w-md bg-red-500/20 border border-red-400 rounded-2xl p-5 text-center space-y-3">
                <p className="text-4xl">💪</p>
                <p className="text-red-300 font-bold">Not quite — try again!</p>
                <div className="flex gap-3">
                  <button
                    onClick={() => { setFeedback(null); setUserAnswer(''); setShowHint(true) }}
                    className="flex-1 py-2 bg-white/10 text-white rounded-xl text-sm"
                  >
                    Try Again
                  </button>
                  <button
                    onClick={nextQuest}
                    className="flex-1 py-2 bg-red-500/50 text-white rounded-xl text-sm"
                  >
                    Skip
                  </button>
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>

      {/* Ore decorations */}
      <div className="flex justify-center gap-6 p-4 border-t border-white/10">
        {['💎', '🪨', '⚡', '🥇', '💎'].map((ore, i) => (
          <span key={i} className="text-2xl opacity-40">{ore}</span>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/rooms/MathMines.tsx
git commit -m "feat: add MathMines room with Gemini-powered math quests and streak bonus"
```

---

## Task 9: Story Forest Room

**Files:**
- Create: `src/components/rooms/StoryForest.tsx`

- [ ] **Step 1: Create `src/components/rooms/StoryForest.tsx`**

```typescript
import { useState, useEffect } from 'react'
import { AvatarData } from '../../types/game'

interface Props {
  playerName: string
  avatarData: AvatarData
  onXpEarned: (amount: number) => void
  onCoinsEarned: (amount: number) => void
}

interface StoryQuest {
  passage: string
  question: string
  choices: string[]
  correctIndex: number
  explanation: string
  xpReward: number
  coinReward: number
}

const FALLBACK_QUESTS: StoryQuest[] = [
  {
    passage: "Early settlers had to preserve food before winter. They would smoke meats, dry fruits, and pickle vegetables in salt brine. A good harvest and careful preservation meant survival through the cold months.",
    question: "What is the main idea of this passage?",
    choices: [
      "Settlers enjoyed eating pickles",
      "Preserving food was essential for winter survival",
      "Salt was rare and valuable",
      "Settlers preferred smoked meat over fresh meat"
    ],
    correctIndex: 1,
    explanation: "The passage focuses on how preservation was necessary for surviving winter — not just one method or preference.",
    xpReward: 30,
    coinReward: 8
  },
  {
    passage: "Benjamin Franklin once wrote: 'An investment in knowledge pays the best interest.' He believed that reading and learning were more valuable than gold because knowledge cannot be stolen or lost to fire.",
    question: "According to Franklin, why is knowledge more valuable than gold?",
    choices: [
      "Knowledge is easier to carry",
      "Gold can rust and tarnish",
      "Knowledge cannot be stolen or destroyed",
      "Franklin owned no gold"
    ],
    correctIndex: 2,
    explanation: "Franklin specifically said knowledge cannot be stolen or lost to fire — those are the reasons he valued it above gold.",
    xpReward: 30,
    coinReward: 8
  }
]

export default function StoryForest({ playerName, onXpEarned, onCoinsEarned }: Props) {
  const [quest, setQuest] = useState<StoryQuest | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [questIndex, setQuestIndex] = useState(0)

  useEffect(() => {
    loadQuest()
  }, [questIndex])

  async function loadQuest() {
    setLoading(true)
    setSelected(null)
    setRevealed(false)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create a short reading comprehension quest for a homeschool student. Write a 2-3 sentence passage about history, nature, homesteading, faith, or literature. Then write a multiple-choice question with 4 choices. Respond ONLY with valid JSON: {"passage":"...","question":"...","choices":["...","...","...","..."],"correctIndex":0,"explanation":"...","xpReward":30,"coinReward":8}`,
          history: []
        })
      })
      const data = await response.json()
      const parsed = JSON.parse(data.reply.replace(/```json|```/g, '').trim())
      if (parsed.passage && parsed.choices?.length === 4) {
        setQuest(parsed)
      } else {
        throw new Error('Invalid format')
      }
    } catch {
      setQuest(FALLBACK_QUESTS[questIndex % FALLBACK_QUESTS.length])
    } finally {
      setLoading(false)
    }
  }

  function selectAnswer(index: number) {
    if (revealed) return
    setSelected(index)
  }

  function checkAnswer() {
    if (selected === null || !quest) return
    setRevealed(true)
    if (selected === quest.correctIndex) {
      onXpEarned(quest.xpReward)
      onCoinsEarned(quest.coinReward)
    }
  }

  const isCorrect = revealed && selected === quest?.correctIndex

  return (
    <div className="h-full flex flex-col" style={{ background: 'linear-gradient(180deg, #0a2e0a 0%, #1a4a1a 40%, #0d3b0d 100%)' }}>

      {/* Room header */}
      <div className="flex items-center gap-3 p-4 border-b border-white/10">
        <span className="text-3xl">🌲</span>
        <div>
          <h2 className="text-white font-bold text-lg">Story Forest</h2>
          <p className="text-green-300 text-xs">Where words grow wild, {playerName}!</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-5">

        {loading ? (
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-green-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-green-300 text-sm">Adeline is opening a story scroll...</p>
          </div>
        ) : quest ? (
          <>
            {/* Passage card */}
            <div className="w-full max-w-lg bg-amber-50/10 backdrop-blur rounded-2xl p-5 border border-amber-200/20">
              <p className="text-xs text-amber-300 font-semibold uppercase tracking-wider mb-2">📜 Read this passage</p>
              <p className="text-white/90 text-sm leading-relaxed">{quest.passage}</p>
            </div>

            {/* Question */}
            <div className="w-full max-w-lg">
              <p className="text-white font-semibold text-sm mb-3">{quest.question}</p>
              <div className="space-y-2">
                {quest.choices.map((choice, i) => {
                  let style = 'bg-white/10 border border-white/20 text-white hover:bg-white/20'
                  if (selected === i && !revealed) style = 'bg-green-600/40 border border-green-400 text-white'
                  if (revealed && i === quest.correctIndex) style = 'bg-emerald-500/30 border-2 border-emerald-400 text-emerald-200'
                  if (revealed && selected === i && i !== quest.correctIndex) style = 'bg-red-500/30 border-2 border-red-400 text-red-200'
                  return (
                    <button
                      key={i}
                      onClick={() => selectAnswer(i)}
                      className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all ${style}`}
                    >
                      <span className="font-bold mr-2">{String.fromCharCode(65 + i)}.</span>
                      {choice}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Action / feedback */}
            {!revealed ? (
              <button
                onClick={checkAnswer}
                disabled={selected === null}
                className="w-full max-w-lg py-3 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white font-bold rounded-xl transition-all"
              >
                Check Answer →
              </button>
            ) : (
              <div className={`w-full max-w-lg rounded-2xl p-4 space-y-2 ${isCorrect ? 'bg-emerald-500/20 border border-emerald-400' : 'bg-red-500/20 border border-red-400'}`}>
                <p className={`font-bold ${isCorrect ? 'text-emerald-300' : 'text-red-300'}`}>
                  {isCorrect ? '🎉 Well read!' : '📚 Good try!'}
                </p>
                <p className="text-white/80 text-sm">{quest.explanation}</p>
                {isCorrect && <p className="text-amber-300 text-xs">+{quest.xpReward} XP · +{quest.coinReward} AdeCoins</p>}
                <button
                  onClick={() => setQuestIndex(i => i + 1)}
                  className={`w-full py-2 rounded-xl text-white font-semibold mt-2 ${isCorrect ? 'bg-emerald-500' : 'bg-white/20'}`}
                >
                  Next Story →
                </button>
              </div>
            )}
          </>
        ) : null}
      </div>

      {/* Forest floor decoration */}
      <div className="flex justify-center gap-4 p-3 border-t border-white/10">
        {['🍄', '🌿', '🦋', '🌸', '🍃'].map((e, i) => (
          <span key={i} className="text-xl opacity-40">{e}</span>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/rooms/StoryForest.tsx
git commit -m "feat: add StoryForest room with Gemini reading comprehension quests"
```

---

## Task 10: Wire GameShell — Orchestrate Full Game Flow

**Files:**
- Modify: `src/pages/GameShell.tsx`

This is the main orchestrator. It manages: avatar builder (first time) → hub world → rooms → Adeline chat.

- [ ] **Step 1: Replace `src/pages/GameShell.tsx` entirely**

```typescript
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { AvatarData, RoomId, DEFAULT_AVATAR } from '../types/game'
import AvatarBuilder from '../components/avatar/AvatarBuilder'
import GameHUD from '../components/hud/GameHUD'
import HubWorld from '../components/world/HubWorld'
import MathMines from '../components/rooms/MathMines'
import StoryForest from '../components/rooms/StoryForest'
import { supabase } from '../lib/supabase'

type GameScreen = 'avatar_builder' | 'hub' | 'room' | 'adeline_chat'

function parseAvatar(data: Record<string, unknown>): AvatarData | null {
  if (!data || !data.skinTone) return null
  return data as unknown as AvatarData
}

export default function GameShell() {
  const { activeChild, guestSession, signOut, parentAccount } = useAuth()
  const navigate = useNavigate()

  // Determine initial avatar from stored data
  const storedAvatar = activeChild?.avatar_data ? parseAvatar(activeChild.avatar_data) : null
  const guestAvatarRaw = guestSession?.avatarData
  const guestAvatar = guestAvatarRaw && Object.keys(guestAvatarRaw).length > 0
    ? parseAvatar(guestAvatarRaw as Record<string, unknown>)
    : null

  const hasAvatar = storedAvatar !== null || guestAvatar !== null
  const [screen, setScreen] = useState<GameScreen>(hasAvatar ? 'hub' : 'avatar_builder')
  const [avatarData, setAvatarData] = useState<AvatarData>(storedAvatar ?? guestAvatar ?? DEFAULT_AVATAR)
  const [currentRoom, setCurrentRoom] = useState<RoomId | null>(null)
  const [localXP, setLocalXP] = useState(activeChild?.xp ?? guestSession?.xp ?? 0)
  const [localCoins, setLocalCoins] = useState(activeChild?.ade_coins ?? guestSession?.adeCoins ?? 0)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMessages, setChatMessages] = useState<{ text: string; fromAdeline: boolean }[]>([
    { text: "Welcome to Adeline World! What would you like to explore today?", fromAdeline: true }
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)

  const playerName = activeChild?.display_name ?? guestSession?.displayName ?? 'Explorer'
  const isGuest = !activeChild && !!guestSession

  async function saveAvatar(avatar: AvatarData) {
    setAvatarData(avatar)
    if (activeChild) {
      await supabase
        .from('aw_student_profiles')
        .update({ avatar_data: avatar as unknown as Record<string, unknown> })
        .eq('id', activeChild.id)
    } else if (guestSession) {
      const updated = { ...guestSession, avatarData: avatar }
      localStorage.setItem('adeline_guest', JSON.stringify(updated))
    }
    setScreen('hub')
  }

  async function addXP(amount: number) {
    const newXP = localXP + amount
    setLocalXP(newXP)
    if (activeChild) {
      await supabase
        .from('aw_student_profiles')
        .update({ xp: newXP })
        .eq('id', activeChild.id)
    }
  }

  async function addCoins(amount: number) {
    const newCoins = localCoins + amount
    setLocalCoins(newCoins)
    if (activeChild) {
      await supabase
        .from('aw_student_profiles')
        .update({ ade_coins: newCoins })
        .eq('id', activeChild.id)
    }
  }

  const enterRoom = useCallback((roomId: RoomId) => {
    setCurrentRoom(roomId)
    setScreen('room')
  }, [])

  function exitRoom() {
    setCurrentRoom(null)
    setScreen('hub')
  }

  async function sendChatMessage() {
    if (!chatInput.trim() || chatLoading) return
    const userMsg = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { text: userMsg, fromAdeline: false }])
    setChatLoading(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, history: [] })
      })
      const data = await res.json()
      setChatMessages(prev => [...prev, { text: data.reply, fromAdeline: true }])
    } catch {
      setChatMessages(prev => [...prev, { text: "My thoughts got a little tangled — try again!", fromAdeline: true }])
    } finally {
      setChatLoading(false)
    }
  }

  async function handleSignOut() {
    await signOut()
    navigate('/')
  }

  const roomLabel = currentRoom === 'math_mines' ? '⛏️ Math Mines' : currentRoom === 'story_forest' ? '🌲 Story Forest' : undefined

  // Synthesize player-like objects for HUD (which expects StudentProfile shape)
  const hudPlayer = activeChild
    ? { ...activeChild, xp: localXP, ade_coins: localCoins }
    : null
  const hudGuest = guestSession
    ? { ...guestSession, xp: localXP, adeCoins: localCoins }
    : null

  return (
    <div className="w-screen h-screen overflow-hidden relative">

      {/* Avatar Builder */}
      {screen === 'avatar_builder' && (
        <AvatarBuilder
          initialAvatar={storedAvatar ?? guestAvatar ?? undefined}
          playerName={playerName}
          onSave={saveAvatar}
        />
      )}

      {/* Game (Hub or Room) */}
      {(screen === 'hub' || screen === 'room') && (
        <>
          <GameHUD
            player={hudPlayer}
            guestSession={hudGuest}
            avatarData={avatarData}
            roomLabel={roomLabel}
            onExitRoom={screen === 'room' ? exitRoom : undefined}
            onSignOut={handleSignOut}
          />

          <div className="w-full h-full pt-16">
            {screen === 'hub' && (
              <HubWorld
                avatarData={avatarData}
                playerName={playerName}
                onEnterRoom={enterRoom}
                onChatAdeline={() => setChatOpen(true)}
              />
            )}
            {screen === 'room' && currentRoom === 'math_mines' && (
              <MathMines
                playerName={playerName}
                avatarData={avatarData}
                onXpEarned={addXP}
                onCoinsEarned={addCoins}
              />
            )}
            {screen === 'room' && currentRoom === 'story_forest' && (
              <StoryForest
                playerName={playerName}
                avatarData={avatarData}
                onXpEarned={addXP}
                onCoinsEarned={addCoins}
              />
            )}
          </div>

          {/* Guest nudge banner */}
          {isGuest && (
            <div className="fixed bottom-4 right-4 bg-amber-500 text-white text-xs font-semibold px-4 py-2 rounded-2xl shadow-lg max-w-xs">
              💾 Guest mode — progress not saved to cloud.{' '}
              <button onClick={handleSignOut} className="underline">Create account</button>
            </div>
          )}
        </>
      )}

      {/* Adeline Chat Modal */}
      {chatOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-3xl overflow-hidden shadow-2xl">
            <div className="bg-amber-600 px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-white/50">
                  <img src="/adeline_portrait.png" alt="Adeline" className="w-full h-full object-cover" />
                </div>
                <div>
                  <p className="text-white font-bold">Adeline</p>
                  <p className="text-amber-200 text-xs">Your learning guide</p>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} className="text-white/80 hover:text-white text-xl">✕</button>
            </div>

            <div className="h-64 overflow-y-auto p-4 space-y-3 bg-amber-50/30">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.fromAdeline ? '' : 'justify-end'}`}>
                  <div className={`max-w-[85%] px-4 py-2 rounded-2xl text-sm ${
                    msg.fromAdeline
                      ? 'bg-white text-slate-800 border border-amber-100'
                      : 'bg-amber-600 text-white'
                  }`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex gap-1 items-center px-4 py-2 bg-white rounded-2xl w-fit">
                  <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              )}
            </div>

            <div className="p-4 border-t border-amber-100 flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendChatMessage()}
                placeholder="Ask Adeline anything..."
                className="flex-1 px-3 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:border-amber-400"
              />
              <button
                onClick={sendChatMessage}
                disabled={!chatInput.trim() || chatLoading}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-xl text-sm font-semibold"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/GameShell.tsx
git commit -m "feat: wire GameShell - avatar builder first, hub world, rooms, Adeline chat"
```

---

## Task 11: Science Lab Room

**Files:**
- Create: `src/components/rooms/ScienceLab.tsx`
- Modify: `src/types/game.ts` — add `'science_lab'` to RoomId and HUB_PORTALS
- Modify: `src/pages/GameShell.tsx` — add ScienceLab route

- [ ] **Step 1: Add `'science_lab'` to `src/types/game.ts`**

Change the RoomId type:
```typescript
export type RoomId = 'math_mines' | 'story_forest' | 'science_lab' | 'homestead_farm' | 'truth_archive'
```

Add to HUB_PORTALS array (after the story_forest entry):
```typescript
  {
    id: 'science_lab',
    label: 'Science Lab',
    description: 'Discover how creation works',
    x: 50,
    y: 20,
    color: '#0e7490',
    emoji: '🔬'
  },
  {
    id: 'homestead_farm',
    label: 'Homestead Farm',
    description: 'Grow, raise, build, and sell',
    x: 18,
    y: 65,
    color: '#65a30d',
    emoji: '🌾'
  },
  {
    id: 'truth_archive',
    label: 'Truth Archive',
    description: 'Primary sources, real history',
    x: 82,
    y: 65,
    color: '#92400e',
    emoji: '📜'
  },
```

- [ ] **Step 2: Create `src/components/rooms/ScienceLab.tsx`**

```typescript
import { useState, useEffect } from 'react'

interface Props {
  playerName: string
  onXpEarned: (amount: number) => void
  onCoinsEarned: (amount: number) => void
}

interface Experiment {
  scenario: string
  question: string
  choices: string[]
  correctIndex: number
  explanation: string
  xpReward: number
  coinReward: number
}

const FALLBACK_EXPERIMENTS: Experiment[] = [
  {
    scenario: "You plant two identical tomato seedlings. One gets 6 hours of sunlight daily, the other gets 1 hour. After 3 weeks, the first plant is tall and flowering. The second is small and pale.",
    question: "What does this experiment show?",
    choices: [
      "Tomatoes prefer cool weather",
      "Plants need sunlight to grow well",
      "Watering is more important than sunlight",
      "Both plants will eventually look the same"
    ],
    correctIndex: 1,
    explanation: "The only difference between the plants was sunlight. Since the plant with more sun grew better, we can conclude sunlight is essential for healthy growth — this is how God designed photosynthesis to work.",
    xpReward: 30,
    coinReward: 8
  },
  {
    scenario: "When you mix baking soda and vinegar, the mixture bubbles rapidly and the container feels colder. The bubbles are carbon dioxide gas escaping.",
    question: "What type of reaction is this?",
    choices: [
      "A physical change — no new substance was made",
      "A chemical reaction — new substances were created",
      "The baking soda just dissolved in vinegar",
      "Heat caused the bubbling"
    ],
    correctIndex: 1,
    explanation: "A chemical reaction occurred: the baking soda (sodium bicarbonate) and vinegar (acetic acid) reacted to form carbon dioxide gas, water, and sodium acetate — entirely new substances.",
    xpReward: 35,
    coinReward: 10
  },
]

export default function ScienceLab({ playerName, onXpEarned, onCoinsEarned }: Props) {
  const [experiment, setExperiment] = useState<Experiment | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [questIndex, setQuestIndex] = useState(0)

  useEffect(() => { loadExperiment() }, [questIndex])

  async function loadExperiment() {
    setLoading(true)
    setSelected(null)
    setRevealed(false)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create a science observation or experiment scenario for a homeschool student. Base it on creation science, nature, farming, chemistry with household items, or animal biology. Write 2-3 sentences describing what happens, then a multiple-choice question with 4 options. Include a faith-friendly explanation grounded in how God designed creation. Respond ONLY with valid JSON: {"scenario":"...","question":"...","choices":["...","...","...","..."],"correctIndex":0,"explanation":"...","xpReward":30,"coinReward":8}`,
          history: []
        })
      })
      const data = await res.json()
      const parsed = JSON.parse(data.reply.replace(/```json|```/g, '').trim())
      if (parsed.scenario && parsed.choices?.length === 4) setExperiment(parsed)
      else throw new Error('bad format')
    } catch {
      setExperiment(FALLBACK_EXPERIMENTS[questIndex % FALLBACK_EXPERIMENTS.length])
    } finally {
      setLoading(false)
    }
  }

  function check() {
    if (selected === null || !experiment) return
    setRevealed(true)
    if (selected === experiment.correctIndex) {
      onXpEarned(experiment.xpReward)
      onCoinsEarned(experiment.coinReward)
    }
  }

  const isCorrect = revealed && selected === experiment?.correctIndex

  return (
    <div className="h-full flex flex-col" style={{ background: 'linear-gradient(180deg, #0c1a2e 0%, #0e3a4a 50%, #0a2535 100%)' }}>
      <div className="flex items-center gap-3 p-4 border-b border-white/10">
        <span className="text-3xl">🔬</span>
        <div>
          <h2 className="text-white font-bold text-lg">Science Lab</h2>
          <p className="text-cyan-300 text-xs">Discover God's design, {playerName}!</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-5 overflow-y-auto">
        {loading ? (
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-cyan-300 text-sm">Preparing your experiment...</p>
          </div>
        ) : experiment ? (
          <>
            <div className="w-full max-w-lg bg-cyan-900/30 backdrop-blur rounded-2xl p-5 border border-cyan-400/20">
              <p className="text-xs text-cyan-300 font-semibold uppercase tracking-wider mb-2">🧪 Observe</p>
              <p className="text-white/90 text-sm leading-relaxed">{experiment.scenario}</p>
            </div>

            <div className="w-full max-w-lg">
              <p className="text-white font-semibold text-sm mb-3">{experiment.question}</p>
              <div className="space-y-2">
                {experiment.choices.map((choice, i) => {
                  let cls = 'bg-white/10 border border-white/20 text-white hover:bg-white/20'
                  if (selected === i && !revealed) cls = 'bg-cyan-600/40 border border-cyan-400 text-white'
                  if (revealed && i === experiment.correctIndex) cls = 'bg-emerald-500/30 border-2 border-emerald-400 text-emerald-200'
                  if (revealed && selected === i && i !== experiment.correctIndex) cls = 'bg-red-500/30 border-2 border-red-400 text-red-200'
                  return (
                    <button key={i} onClick={() => !revealed && setSelected(i)}
                      className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all ${cls}`}>
                      <span className="font-bold mr-2">{String.fromCharCode(65+i)}.</span>{choice}
                    </button>
                  )
                })}
              </div>
            </div>

            {!revealed ? (
              <button onClick={check} disabled={selected === null}
                className="w-full max-w-lg py-3 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold rounded-xl">
                Submit Observation →
              </button>
            ) : (
              <div className={`w-full max-w-lg rounded-2xl p-4 space-y-2 ${isCorrect ? 'bg-emerald-500/20 border border-emerald-400' : 'bg-red-500/20 border border-red-400'}`}>
                <p className={`font-bold ${isCorrect ? 'text-emerald-300' : 'text-red-300'}`}>{isCorrect ? '🎉 Great observation!' : '🔭 Good try!'}</p>
                <p className="text-white/80 text-sm">{experiment.explanation}</p>
                {isCorrect && <p className="text-amber-300 text-xs">+{experiment.xpReward} XP · +{experiment.coinReward} AdeCoins</p>}
                <button onClick={() => setQuestIndex(i => i + 1)}
                  className={`w-full py-2 rounded-xl text-white font-semibold mt-2 ${isCorrect ? 'bg-emerald-500' : 'bg-white/20'}`}>
                  Next Experiment →
                </button>
              </div>
            )}
          </>
        ) : null}
      </div>

      <div className="flex justify-center gap-4 p-3 border-t border-white/10">
        {['🧬','⚗️','🔭','🌡️','💧'].map((e,i) => <span key={i} className="text-xl opacity-40">{e}</span>)}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add ScienceLab to GameShell imports and room render**

In `src/pages/GameShell.tsx`, add:
```typescript
import ScienceLab from '../components/rooms/ScienceLab'
```

In the room render section, after the story_forest block:
```typescript
            {screen === 'room' && currentRoom === 'science_lab' && (
              <ScienceLab
                playerName={playerName}
                onXpEarned={addXP}
                onCoinsEarned={addCoins}
              />
            )}
```

Also update `roomLabel` to include the new rooms:
```typescript
  const roomLabel =
    currentRoom === 'math_mines'    ? '⛏️ Math Mines' :
    currentRoom === 'story_forest'  ? '🌲 Story Forest' :
    currentRoom === 'science_lab'   ? '🔬 Science Lab' :
    currentRoom === 'homestead_farm'? '🌾 Homestead Farm' :
    currentRoom === 'truth_archive' ? '📜 Truth Archive' : undefined
```

- [ ] **Step 4: Commit**

```bash
git add src/types/game.ts src/components/rooms/ScienceLab.tsx src/pages/GameShell.tsx
git commit -m "feat: add Science Lab room with creation science experiments"
```

---

## Task 12: Homestead Farm Room

**Files:**
- Create: `src/components/rooms/HomesteadFarm.tsx`
- Modify: `src/pages/GameShell.tsx` — add HomesteadFarm route

- [ ] **Step 1: Create `src/components/rooms/HomesteadFarm.tsx`**

```typescript
import { useState, useEffect } from 'react'

interface Props {
  playerName: string
  onXpEarned: (amount: number) => void
  onCoinsEarned: (amount: number) => void
}

interface FarmTask {
  scenario: string
  challenge: string
  choices: string[]
  correctIndex: number
  explanation: string
  xpReward: number
  coinReward: number
}

const FALLBACK_TASKS: FarmTask[] = [
  {
    scenario: "Your family wants to sell eggs at the farmer's market. You have 4 hens. Each hen lays about 5 eggs per week. Eggs sell for $0.50 each.",
    challenge: "How much money could you earn in one week?",
    choices: ["$5.00", "$8.00", "$10.00", "$20.00"],
    correctIndex: 2,
    explanation: "4 hens × 5 eggs = 20 eggs per week. 20 eggs × $0.50 = $10.00. Running a farm stand teaches you real math AND entrepreneurship!",
    xpReward: 30,
    coinReward: 10
  },
  {
    scenario: "Your garden has 3 rows of tomatoes. Each row has 8 plants. You want to can all your tomatoes. Each plant gives about 10 tomatoes and each jar needs 6 tomatoes.",
    challenge: "How many jars can you fill?",
    choices: ["24 jars", "40 jars", "48 jars", "30 jars"],
    correctIndex: 1,
    explanation: "3 rows × 8 plants = 24 plants. 24 plants × 10 tomatoes = 240 tomatoes. 240 ÷ 6 = 40 jars. Preserving your harvest is a real survival skill!",
    xpReward: 35,
    coinReward: 12
  },
]

export default function HomesteadFarm({ playerName, onXpEarned, onCoinsEarned }: Props) {
  const [task, setTask] = useState<FarmTask | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [questIndex, setQuestIndex] = useState(0)

  useEffect(() => { loadTask() }, [questIndex])

  async function loadTask() {
    setLoading(true)
    setSelected(null)
    setRevealed(false)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create a practical homesteading challenge for a homeschool student. It should involve farming, animals (chickens, sheep, horses, cows), gardening, canning/preserving food, building, selling at a farm stand, or off-grid living. Include real math or decision-making. Write 2 sentences setting the scene, then a multiple-choice question with 4 options. Respond ONLY with valid JSON: {"scenario":"...","challenge":"...","choices":["...","...","...","..."],"correctIndex":0,"explanation":"...","xpReward":30,"coinReward":10}`,
          history: []
        })
      })
      const data = await res.json()
      const parsed = JSON.parse(data.reply.replace(/```json|```/g, '').trim())
      if (parsed.scenario && parsed.choices?.length === 4) setTask(parsed)
      else throw new Error('bad format')
    } catch {
      setTask(FALLBACK_TASKS[questIndex % FALLBACK_TASKS.length])
    } finally {
      setLoading(false)
    }
  }

  function check() {
    if (selected === null || !task) return
    setRevealed(true)
    if (selected === task.correctIndex) {
      onXpEarned(task.xpReward)
      onCoinsEarned(task.coinReward)
    }
  }

  const isCorrect = revealed && selected === task?.correctIndex

  return (
    <div className="h-full flex flex-col" style={{ background: 'linear-gradient(180deg, #1a2e0a 0%, #2d4a1a 40%, #3d5c1e 100%)' }}>
      <div className="flex items-center gap-3 p-4 border-b border-white/10">
        <span className="text-3xl">🌾</span>
        <div>
          <h2 className="text-white font-bold text-lg">Homestead Farm</h2>
          <p className="text-lime-300 text-xs">Grow, raise, build, sell — {playerName}!</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-5 overflow-y-auto">
        {loading ? (
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-lime-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-lime-300 text-sm">Adeline is checking the farm...</p>
          </div>
        ) : task ? (
          <>
            <div className="w-full max-w-lg bg-lime-900/30 backdrop-blur rounded-2xl p-5 border border-lime-400/20">
              <p className="text-xs text-lime-300 font-semibold uppercase tracking-wider mb-2">🐓 Farm Scene</p>
              <p className="text-white/90 text-sm leading-relaxed">{task.scenario}</p>
            </div>

            <div className="w-full max-w-lg">
              <p className="text-white font-semibold text-sm mb-3">{task.challenge}</p>
              <div className="space-y-2">
                {task.choices.map((choice, i) => {
                  let cls = 'bg-white/10 border border-white/20 text-white hover:bg-white/20'
                  if (selected === i && !revealed) cls = 'bg-lime-600/40 border border-lime-400 text-white'
                  if (revealed && i === task.correctIndex) cls = 'bg-emerald-500/30 border-2 border-emerald-400 text-emerald-200'
                  if (revealed && selected === i && i !== task.correctIndex) cls = 'bg-red-500/30 border-2 border-red-400 text-red-200'
                  return (
                    <button key={i} onClick={() => !revealed && setSelected(i)}
                      className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all ${cls}`}>
                      <span className="font-bold mr-2">{String.fromCharCode(65+i)}.</span>{choice}
                    </button>
                  )
                })}
              </div>
            </div>

            {!revealed ? (
              <button onClick={check} disabled={selected === null}
                className="w-full max-w-lg py-3 bg-lime-600 hover:bg-lime-500 disabled:opacity-50 text-white font-bold rounded-xl">
                Work It Out →
              </button>
            ) : (
              <div className={`w-full max-w-lg rounded-2xl p-4 space-y-2 ${isCorrect ? 'bg-emerald-500/20 border border-emerald-400' : 'bg-red-500/20 border border-red-400'}`}>
                <p className={`font-bold ${isCorrect ? 'text-emerald-300' : 'text-red-300'}`}>{isCorrect ? '🎉 Great farming!' : '🌱 Keep growing!'}</p>
                <p className="text-white/80 text-sm">{task.explanation}</p>
                {isCorrect && <p className="text-amber-300 text-xs">+{task.xpReward} XP · +{task.coinReward} AdeCoins</p>}
                <button onClick={() => setQuestIndex(i => i + 1)}
                  className={`w-full py-2 rounded-xl text-white font-semibold mt-2 ${isCorrect ? 'bg-emerald-500' : 'bg-white/20'}`}>
                  Next Task →
                </button>
              </div>
            )}
          </>
        ) : null}
      </div>

      <div className="flex justify-center gap-4 p-3 border-t border-white/10">
        {['🐔','🐑','🥕','🍅','🥚'].map((e,i) => <span key={i} className="text-xl opacity-40">{e}</span>)}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add HomesteadFarm to `src/pages/GameShell.tsx`**

Add import:
```typescript
import HomesteadFarm from '../components/rooms/HomesteadFarm'
```

Add room render block after the science_lab block:
```typescript
            {screen === 'room' && currentRoom === 'homestead_farm' && (
              <HomesteadFarm
                playerName={playerName}
                onXpEarned={addXP}
                onCoinsEarned={addCoins}
              />
            )}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/rooms/HomesteadFarm.tsx src/pages/GameShell.tsx
git commit -m "feat: add Homestead Farm room with real-world farming and market challenges"
```

---

## Task 13: Truth Archive Room

**Files:**
- Create: `src/components/rooms/TruthArchive.tsx`
- Modify: `src/pages/GameShell.tsx` — add TruthArchive route

- [ ] **Step 1: Create `src/components/rooms/TruthArchive.tsx`**

```typescript
import { useState, useEffect } from 'react'

interface Props {
  playerName: string
  onXpEarned: (amount: number) => void
  onCoinsEarned: (amount: number) => void
}

interface HistoryQuest {
  source: string        // the "primary source" excerpt or paraphrase
  sourceLabel: string   // e.g. "From a letter by Frederick Douglass, 1845"
  question: string
  choices: string[]
  correctIndex: number
  explanation: string
  followMoney?: string  // optional "who profits?" insight
  xpReward: number
  coinReward: number
}

const FALLBACK_QUESTS: HistoryQuest[] = [
  {
    source: `"I have no accurate knowledge of my age, never having seen any authentic record containing it. By far the larger part of the slaves know as little of their ages as horses know of theirs."`,
    sourceLabel: "Frederick Douglass — Narrative of the Life of Frederick Douglass, 1845",
    question: "Why did enslaved people often not know their own ages?",
    choices: [
      "They didn't care about birthdays",
      "Enslavers deliberately withheld basic personal information as a tool of control",
      "Record-keeping was too expensive",
      "It was a cultural tradition to not track ages"
    ],
    correctIndex: 1,
    explanation: "Douglass explains that keeping enslaved people ignorant of even basic facts about themselves — like their own birthday — was a deliberate strategy to strip away identity and humanity.",
    followMoney: "Enslavers profited from keeping people in ignorance. An enslaved person who didn't know their own history had fewer tools to resist or escape.",
    xpReward: 40,
    coinReward: 12
  },
  {
    source: `"We hold these truths to be self-evident, that all men are created equal, that they are endowed by their Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of Happiness."`,
    sourceLabel: "Declaration of Independence — Thomas Jefferson, July 4, 1776",
    question: "What does 'unalienable Rights' mean in this context?",
    choices: [
      "Rights that can be taken away by the government",
      "Rights that only apply to property owners",
      "Rights that cannot be taken away because they come from God, not government",
      "Rights granted by a king or queen"
    ],
    correctIndex: 2,
    explanation: "The founders argued that rights like life and liberty come from the Creator — not from any human government. That means no government has the authority to take them away. This is a foundational idea still argued about today.",
    followMoney: "Ask: if all men are created equal, who was excluded in 1776? Enslaved people, women, and those without property couldn't vote. The gap between the ideal and the reality is where history gets honest.",
    xpReward: 35,
    coinReward: 10
  },
]

export default function TruthArchive({ playerName, onXpEarned, onCoinsEarned }: Props) {
  const [quest, setQuest] = useState<HistoryQuest | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [showFollowMoney, setShowFollowMoney] = useState(false)
  const [loading, setLoading] = useState(true)
  const [questIndex, setQuestIndex] = useState(0)

  useEffect(() => { loadQuest() }, [questIndex])

  async function loadQuest() {
    setLoading(true)
    setSelected(null)
    setRevealed(false)
    setShowFollowMoney(false)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create a primary source history question for a homeschool student. Use a real quote or paraphrase from an actual historical document, letter, speech, or record (label the source). The content should be honest and unfiltered — never sanitize history. Include a "follow the money" or "who profits?" insight when relevant. Topics: American founding, civil rights, westward expansion, Biblical history, colonial life, or world history. Respond ONLY with valid JSON: {"source":"...","sourceLabel":"...","question":"...","choices":["...","...","...","..."],"correctIndex":0,"explanation":"...","followMoney":"...","xpReward":35,"coinReward":10}`,
          history: []
        })
      })
      const data = await res.json()
      const parsed = JSON.parse(data.reply.replace(/```json|```/g, '').trim())
      if (parsed.source && parsed.choices?.length === 4) setQuest(parsed)
      else throw new Error('bad format')
    } catch {
      setQuest(FALLBACK_QUESTS[questIndex % FALLBACK_QUESTS.length])
    } finally {
      setLoading(false)
    }
  }

  function check() {
    if (selected === null || !quest) return
    setRevealed(true)
    if (selected === quest.correctIndex) {
      onXpEarned(quest.xpReward)
      onCoinsEarned(quest.coinReward)
    }
  }

  const isCorrect = revealed && selected === quest?.correctIndex

  return (
    <div className="h-full flex flex-col" style={{ background: 'linear-gradient(180deg, #1a0e05 0%, #2d1a08 50%, #3d240a 100%)' }}>
      <div className="flex items-center gap-3 p-4 border-b border-white/10">
        <span className="text-3xl">📜</span>
        <div>
          <h2 className="text-white font-bold text-lg">Truth Archive</h2>
          <p className="text-amber-300 text-xs">Primary sources only, {playerName}. No sanitizing.</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-5 overflow-y-auto">
        {loading ? (
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-amber-300 text-sm">Adeline is opening the archives...</p>
          </div>
        ) : quest ? (
          <>
            {/* Primary source card */}
            <div className="w-full max-w-lg bg-amber-950/60 backdrop-blur rounded-2xl p-5 border border-amber-600/40">
              <p className="text-xs text-amber-400 font-semibold uppercase tracking-wider mb-2">📖 Primary Source</p>
              <blockquote className="text-amber-100 text-sm leading-relaxed italic border-l-2 border-amber-500 pl-3">
                "{quest.source}"
              </blockquote>
              <p className="text-amber-500 text-xs mt-2">— {quest.sourceLabel}</p>
            </div>

            {/* Question */}
            <div className="w-full max-w-lg">
              <p className="text-white font-semibold text-sm mb-3">{quest.question}</p>
              <div className="space-y-2">
                {quest.choices.map((choice, i) => {
                  let cls = 'bg-white/10 border border-white/20 text-white hover:bg-white/20'
                  if (selected === i && !revealed) cls = 'bg-amber-700/40 border border-amber-400 text-white'
                  if (revealed && i === quest.correctIndex) cls = 'bg-emerald-500/30 border-2 border-emerald-400 text-emerald-200'
                  if (revealed && selected === i && i !== quest.correctIndex) cls = 'bg-red-500/30 border-2 border-red-400 text-red-200'
                  return (
                    <button key={i} onClick={() => !revealed && setSelected(i)}
                      className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all ${cls}`}>
                      <span className="font-bold mr-2">{String.fromCharCode(65+i)}.</span>{choice}
                    </button>
                  )
                })}
              </div>
            </div>

            {!revealed ? (
              <button onClick={check} disabled={selected === null}
                className="w-full max-w-lg py-3 bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-white font-bold rounded-xl">
                Submit Answer →
              </button>
            ) : (
              <div className={`w-full max-w-lg rounded-2xl p-4 space-y-3 ${isCorrect ? 'bg-emerald-500/20 border border-emerald-400' : 'bg-red-500/20 border border-red-400'}`}>
                <p className={`font-bold ${isCorrect ? 'text-emerald-300' : 'text-red-300'}`}>{isCorrect ? '🎉 You read the source!' : '📚 Read it again!'}</p>
                <p className="text-white/80 text-sm">{quest.explanation}</p>
                {isCorrect && <p className="text-amber-300 text-xs">+{quest.xpReward} XP · +{quest.coinReward} AdeCoins</p>}

                {quest.followMoney && (
                  <button onClick={() => setShowFollowMoney(v => !v)}
                    className="text-xs text-amber-400 underline">
                    💰 Follow the money →
                  </button>
                )}
                {showFollowMoney && quest.followMoney && (
                  <div className="bg-amber-900/40 border border-amber-600/40 rounded-xl p-3">
                    <p className="text-amber-200 text-xs">{quest.followMoney}</p>
                  </div>
                )}

                <button onClick={() => setQuestIndex(i => i + 1)}
                  className={`w-full py-2 rounded-xl text-white font-semibold mt-1 ${isCorrect ? 'bg-emerald-500' : 'bg-white/20'}`}>
                  Next Source →
                </button>
              </div>
            )}
          </>
        ) : null}
      </div>

      <div className="flex justify-center gap-4 p-3 border-t border-white/10">
        {['📜','🖋️','🗺️','⚖️','🏛️'].map((e,i) => <span key={i} className="text-xl opacity-40">{e}</span>)}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add TruthArchive to `src/pages/GameShell.tsx`**

Add import:
```typescript
import TruthArchive from '../components/rooms/TruthArchive'
```

Add room render block:
```typescript
            {screen === 'room' && currentRoom === 'truth_archive' && (
              <TruthArchive
                playerName={playerName}
                onXpEarned={addXP}
                onCoinsEarned={addCoins}
              />
            )}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/rooms/TruthArchive.tsx src/pages/GameShell.tsx
git commit -m "feat: add Truth Archive room with primary source history and follow-the-money lens"
```

---

## Task 14: Smoke Test + Push

- [ ] **Step 1: Kill any existing dev server and restart fresh**

```bash
# Kill existing server on port 3000 (Windows)
npx kill-port 3000 2>/dev/null || true
npm run dev
```

Expected: `Server running on http://0.0.0.0:3000`

- [ ] **Step 2: Test new user flow (Avatar Builder)**

1. Open `http://localhost:3000`
2. Click "Play as Guest" → enter name → click "Play as Guest →"
3. Should see **AvatarBuilder** (purple gradient, "Build Your Avatar")
4. Click through all 5 tabs (Skin, Hair, Eyes, Outfit, Extra) — each should show options
5. Make some choices → avatar preview should update live
6. Click "Enter Adeline World! →"
7. Should see **HubWorld** (green world, path, portals, Adeline portrait, player avatar moving)

Expected: Avatar matches what you built ✓

- [ ] **Step 3: Test player movement**

1. In hub world, press WASD or Arrow keys
2. Player avatar should move around the world
3. Walking near Math Mines portal (left side) should show "Press E to enter →" prompt
4. Press E → should enter Math Mines room
5. Math Mines should show a math question (or fallback question if Gemini is slow)

Expected: Math question appears, submit an answer, get XP feedback ✓

- [ ] **Step 4: Test Story Forest**

1. Press "← Hub" button to return to hub
2. Walk right toward Story Forest portal
3. Press E → should enter Story Forest
4. Reading passage + 4 multiple choice options appear
5. Select an answer → click "Check Answer" → feedback appears

Expected: Story quest works ✓

- [ ] **Step 5: Test Adeline chat**

1. Return to hub, walk toward Adeline (center of world)
2. Click on Adeline's portrait OR press E when close
3. Chat modal opens with Adeline's greeting
4. Type a message → send → Adeline responds (Gemini-powered)

Expected: Chat works ✓

- [ ] **Step 6: Test HUD**

Verify throughout:
- Top-left: small avatar + player name + XP bar
- Top-right: coin count
- XP increases when completing quests
- Coins increase when completing quests

Expected: HUD updates live ✓

- [ ] **Step 7: Final commit and push**

```bash
git add -A
git status  # should show nothing new
git log --oneline -12
git push origin adeline-world-plan-1
```

Expected: Branch pushed to GitHub ✓

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Avatar builder (kid avatars) — Tasks 2, 3
- ✅ Adeline fixed NPC avatar (portrait photo) — Task 5
- ✅ Hub world 2D scene — Task 7
- ✅ 5 Game Rooms (Math Mines, Story Forest, Science Lab, Homestead Farm, Truth Archive) — Tasks 8, 9, 11, 12, 13
- ✅ Adeline as NPC in hub — Task 5, 7
- ✅ In-game HUD (XP, AdeCoins, room label) — Task 4
- ✅ Quest system powered by Gemini — Tasks 8, 9
- ✅ Avatar saved to Supabase (auth users) / localStorage (guests) — Task 10
- ✅ XP + AdeCoins earned and persisted — Task 10
- ✅ Adeline companion chat — Task 10
- ✅ Guest nudge to create account — Task 10

**Type consistency:**
- `AvatarData` defined in `game.ts` Task 1, used in Tasks 2, 3, 4, 5, 7, 8, 9, 10 ✅
- `RoomId` defined in `game.ts`, used in Tasks 6, 7, 10 ✅
- `HUB_PORTALS` defined in `game.ts`, used in Task 7 ✅
- `DEFAULT_AVATAR` defined in `game.ts`, used in Task 10 ✅
- `getOutfit()` defined in `avatarLayers.ts`, used in `AvatarRenderer.tsx` ✅
- `supabase` from `lib/supabase.ts` used in Task 10 ✅
- `useAuth()` from Plan 1 `AuthContext.tsx` used in Task 10 ✅
