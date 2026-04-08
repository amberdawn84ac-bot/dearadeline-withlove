# Dear Adeline 2.0 — Windsurf Collaboration Rules (Softer, Production-Focused)

You are a careful, aligned coding partner helping ship Dear Adeline — a truth-first K-12 AI mentor for Christian homeschool families.

## Core Philosophy (Follow This Order)
1. **Hippocampus is the first source of truth** — Always check the pgvector corpus first for any lesson or Daily Bread request.
2. If a good match exists (even at softer thresholds per track), use it and cite it.
3. If match is weak or missing: 
   - Fall back to web search (Tavily).
   - Evaluate results for reliability.
   - Seed the best findings into Hippocampus (with clear metadata: source_type, confidence, date).
   - Then generate the response.
4. Never treat Hippocampus as the *only* source — it is the **preferred starting point**.

## Track-Aware Witness Protocol (Key Rule)
- **History-type tracks** (TRUTH_BASED_HISTORY, GOVERNMENT, JUSTICE): Strict Witness (0.82 cosine) — prioritize verified primary sources.
- **DISCIPLESHIP** (Daily Bread, scripture): Permissive (0.65 or bypass for Bible content). Always prefer Everett Fox style via Sefaria API when Bible references appear. Include Hebrew + rhythmic/literal rendering.
- **Other tracks** (Science, Homesteading, Math, Creative Economy, etc.): Medium threshold (~0.75). Allow web search + seeding when Hippocampus is thin.

## Safety & Production Rules
- Never break Supabase JWT auth in production (ADELINE_ENV=production). No demo IDs or header fallbacks.
- Respect the monorepo (pnpm workspaces: adeline-core, adeline-brain, adeline-ui).
- Preserve resilient DB pattern (`_get_conn()` / asyncpg with SSL).
- After any change to seeding, Witness, agents, or curriculum: remind me to re-run the seed scripts on Railway and redeploy brain + UI.
- Prefer small, testable changes. Always ask "Does this risk breaking lesson generation, dashboard, or seeding?" before big refactors.
- For Discipleship: Default to Sefaria fetch for Everett Fox (rhythmic, literal, Hebrew names like YHWH). Combine with context.

## Workflow
- When I ask to "fix X", first read the actual files (especially witness.py / protocols, mentor.py / agents, seed scripts, dashboard/page.tsx).
- Keep changes conservative and aligned with the 10-Track Constitution.
- Flag any potential breakage immediately.

Goal: Get this to a stable launch quickly while keeping the truth-first heart intact.