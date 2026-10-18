# Dependency upgrade and Matter reference comparison

## Scope

Update the active `adeline-ui`, `adeline-core`, and Python backend in the existing
application. The archived `adeline-world` prototype is excluded from the workspace
and is not being revived. This change prepares the runtime for richer teaching;
it does not implement the OpenMAIC renderer or rebuild generated lessons.

## Updated foundation

- Next.js 16.4.2, React/React DOM 19.3.1, Tailwind 4.3.3 and its dedicated PostCSS
  plugin. Existing theme configuration remains explicitly loaded by `@config`.
- AI SDK 7 / React adapter 4, Zod 4.6.7, motion 14, current Supabase clients,
  React Flow, icons, testing libraries, Vitest 5 and tsup 9.
- Node 24 and pnpm 11.25.0 aligned in manifests, UI Dockerfile, and CI. Docker
  installs the committed pnpm lockfile with `--frozen-lockfile`.
- FastAPI 0.143.3, Pydantic 2.14.1, OpenAI 3.35.1, current LangChain adapters,
  SQLAlchemy 2.1.5 with its required asyncio extra, asyncpg 0.32, NumPy 2.5.4,
  authentication, PDF, logging, server and test packages.
- Python's full resolved graph is committed as `adeline-brain/requirements.lock`;
  Docker and the main backend test job install it. Refresh with
  `uv pip compile adeline-brain/requirements.txt --python-version 3.12 --output-file adeline-brain/requirements.lock`.
- Removed unused legacy `google-generativeai` and `pyttsx3` packages,
  `zod-to-json-schema` in favor of Zod's native exporter, redundant Autoprefixer,
  and the obsolete npm lockfile in the pnpm-managed shared package.
- Override vulnerable transitive EPUB/CSS packages: xmldom 0.8.15,
  source-map-js 1.2.2, postcss-selector-parser 7.1.6.

## Compatibility decisions

| Dependency | Decision | Reason |
| --- | --- | --- |
| TypeScript | Pin 5.9.3 | The tested declaration builder needs the compiler API that TypeScript 7 removed. Upgrade requires a deliberate compiler/build integration change. |
| Redis Python client | Use 5.3.1, constrain below 6 | ARQ 0.28 requires `redis<6`; the resolver rejects Redis 8. |
| Server Stripe SDK | Pin existing 14.25.0 | Latest major changes checkout parameters and subscription period fields. Do not change billing API behavior as an incidental teaching-platform upgrade. Browser Stripe packages are updated. |
| Prisma Python client | Keep 0.15.0 | No newer version was returned by the installed-package audit. No database migration or schema change is part of this upgrade. |
| Identifiers | Use Zod 4 GUID validation | Preserve the prior hexadecimal identifier contract, including historical seeded identifiers. Strict Zod 4 UUID validation rejects those previously accepted values. |

## Validation

- Production frontend build, TypeScript check, and shared declaration build pass.
- UI: 205 tests pass. Shared package: 42 tests pass.
- Backend: 203 focused tests pass (one self-skipped, one known priority test
  deselected). Checks cover exploration generation, materials, Daily Bread,
  search, reading sessions, authentication/privacy, book handling, PDF export,
  learning algorithms, rate limits, source routing, evidence, credit and journals.
- `pnpm peers check` and frozen install pass; `uv pip check` passes.
- npm and Python dependency audits report no known vulnerabilities in the audited
  active graphs. This is an advisory-database result, not a security guarantee.
- Local browser screenshot verification could not run because the Chromium
  download failed. Public production UI inspection is separate from automated
  tests. Authenticated learner-session visual verification remains outstanding.
- The full backend Ruff scan reports 1,240 existing findings on both the
  pre-upgrade baseline and upgraded tree. No broad lint-clean claim is made.
- These are focused backend checks, not a claim that the entire historical
  backend suite passes. One previously documented ZPD-priority test remains
  deselected; one algorithm test skips itself.

## The uploaded Matter exports

Read directly from both `.maic.zip` manifests, without changing the uploads:

| Reference | Third grade: Matter Magic | Eighth grade: Exploring Matter |
| --- | --- | --- |
| Scenes | 11 | 10 |
| Interactive scenes | 6 | 5 |
| Activities | Matter hunt, solids/liquids lab, invisible air, sorting, state changes, Matter Machine game | Particle motion, phase changes, atomic structure explorer, classification puzzle, conservation of mass |
| Audio clips | 59 | 56 |
| Teaching emphasis | Everyday observable objects, properties, air and changes | Particle models, atoms, elements/compounds/mixtures and conservation |

Both include actions that target visual elements or widget controls during
narration. The exports are references for behavior and differentiation, not
evidence that their science or executable activities have been independently
validated.

## Next implementation requirements

1. Include learner level in lesson identity and reuse. Current `classroom_slug`
   omits `level`; the lesson form defaults to family ages 11–16. Preserve saved
   work when changing identity/version rules.
2. Replace the three-model restriction with a typed interaction contract that
   can represent real simulations, diagrams and games. Validate both generated
   controls and the mechanism they teach.
3. Evaluate OpenMAIC's reusable renderer/generation components inside this app.
   Its renderer requires Tailwind 4; this upgrade supplies that prerequisite.
4. Connect speech to actual highlighting, annotations, reveals and widget state
   changes. The current scene action contract only carries speech.
5. Use skill-specific authoring requirements and acceptance checks: age-appropriate
   concept selection, source-grounded scenes, usable learner actions, supported
   attempts, fresh independent checks and honest saved evidence.
6. Compare a working Dear Adeline Matter exploration against both uploaded
   references. Preserve Adeline's persona and the ten tracks without forcing all
   ten into every lesson. Test activities, navigation, saved work after refresh,
   scientific accuracy and layout with actual rendered output.

Upstream code inspected at `THU-MAIC/OpenMAIC` commit
`3d6fe7b6b377f32574f1b4aba2a83d6ab9514a97`: DSL interactive/action contracts,
generation outline/scene code and templates, action engine, standalone interactive
player, and renderer dependency manifest. The uploaded design skills were also
compared with the present Dear Adeline contracts and player.
