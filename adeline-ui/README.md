# adeline-ui

The **Experience Layer** of Dear Adeline 2.0. A Next.js 14 App Router application with Sketchnote theme.

## Design System

| Token | Hex | Role |
|-------|-----|------|
| `papaya` | `#BD6809` | Primary accent, CTAs, highlights |
| `paradise` | `#9A3F4A` | Secondary, headings, active states |
| `fuschia` | `#3D1419` | Deep background, borders, text on light |

## Key Components

- **`GenUIRenderer`** — Dynamically renders lesson blocks based on `blockType` (NARRATIVE, QUESTION, ACTIVITY, SKETCHNOTE, RESEARCH_MISSION, SCRIPTURE, DEFINITION)
- **`TrackBadge`** — Displays which of the 8 Tracks a block belongs to
- **`WitnessAlert`** — Shown when a RESEARCH_MISSION block is returned (ARCHIVE_SILENT fired)

## API Integration

Fetches from `adeline-brain` via type-safe REST using `fetch` with shared types from `@adeline/core`.

Base URL configured via `NEXT_PUBLIC_BRAIN_URL` env var (default: `http://adeline-brain:8000`).
