# @adeline/core

Shared TypeScript package for the **Dear Adeline 2.0** Truth-First K-12 AI Mentor ecosystem.

## What Lives Here

| Module | Purpose |
|--------|---------|
| `enums/tracks` | The 8-Track Constitution — curriculum domain identifiers |
| `schemas/lessonBlock` | Zod schema for structured lesson content |
| `schemas/studentProfile` | Zod schema for learner context (incl. `isHomestead`) |
| `schemas/evidence` | Zod schema + 0.85 Witness Protocol threshold logic |

## The 8-Track Constitution

1. God's Creation & Science
2. Health / Naturopathy
3. Homesteading & Stewardship
4. Government / Economics
5. Justice / Change-making
6. Discipleship & Discernment
7. Truth-Based History
8. English Language & Literature

## Install

```bash
# From within the monorepo (Docker handles this automatically)
npm install
npm run build
```

## Used By

- `adeline-brain` — Python agents import JSON schema equivalents
- `adeline-ui` — Next.js imports types directly via workspace symlink
