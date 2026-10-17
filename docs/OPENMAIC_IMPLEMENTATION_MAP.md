# Fresh Dear Adeline classroom implementation

This supersedes the incremental lesson-preservation plan. Amber directed a clean
lesson-content reset on October 17, 2026, retaining the ten tracks and Adeline's
persona. Baseline inspected: `89ea173deee4baec64b89c0c82071dc7109306e8`.

## What is replaced

The lesson and Space pages now open the fresh classroom player. The old
`/experience/build` and `/brain/spaces` routers are no longer mounted. Repository
canonical fallback returns no lesson; old forensic topics no longer expand into
a hardcoded sequence. Background canonical replenishment is disabled regardless
of the prior environment setting. A new plan-cache namespace excludes old cached
learning plans. New classroom identity is `openmaic-classroom-v1`, distinct from
all previous lesson content and cache keys.

`20261017_reset_legacy_lessons/migration.sql` empties prior canonical lesson
content and old learner-adaptation content, marks old canonicals unavailable,
and deletes old Today plans. It does not delete accounts, standards, characters,
or the append-only learner evidence ledger. Historical Space transcripts are
not reachable through a legacy teaching endpoint. The migration runs through the
existing Prisma deploy sequence; it has NOT been executed against production in
this workspace. A staged migration and deploy are required to enact the wipe.

## New authoring and delivery

1. Choose a topic, starting track, learners and available materials.
2. Author a blueprint: enduring understanding, essential question, demonstration,
   integrated tracks, cast, scene list and a proposed deeper revisit.
3. Review the scene plan and choose Build. Reopening the plan restores its request.
4. Build one scene per model call, reading the preceding actual scenes. Persist
   each accepted scene as a checkpoint. Generation failure leaves an explicit
   failed state with saved scenes; Resume continues from the checkpoint.
5. Validate the complete scene list, order, types, cast, quizzes and interactive
   mechanisms before reporting ready. A shared canonical is reused across learners;
   per-canonical PostgreSQL advisory locks serialize planning/building.
6. Present one scene at a time with differentiated family participation, teacher
   and assistant dialogue, interactive activities, and server-saved responses.
7. A learner can ask Adeline a real question about the current scene. The model
   receives that scene, saved response, prior conversation and the shared persona.
   Dialogue is saved and restored. It does not silently award mastery.

Scene types implemented: explanatory slide, interactive numerical model, quiz,
and project. The first interactive models are proportional multiplication,
rectangle area, and mixture fraction, with validated bounds and units. A model
must fit the concept; other investigations use project scenes. This is an original
implementation of the uploaded approach, NOT a claim to include every OpenMAIC
SDK widget, arbitrary code execution, a slide editor, or 3D rendering.

Quiz answer keys remain server-side until a response is submitted. Question
options and keys are validated. Response writes use an idempotency key and a row
lock; reused keys with different work are rejected. Evidence is saved in the
existing append-only ledger. A saved response or completed page does not certify
mastery. Existing parent evidence review remains available.

Listen uses the device's speech-synthesis capability when available; it is not
pre-generated OpenMAIC audio or a cloned Adeline voice. Slides display explanation
and dialogue in responsive native React rather than a fixed-pixel SDK canvas.

## Adeline and ten tracks

The starting track is validated against the existing `Track` enum. Blueprint
integration accepts those same ten tracks; the requested track cannot be omitted.
All ten names reach every model call. Integration must serve the concept rather
than force all ten into every classroom.

`ADELINE_CLASSROOM_PERSONA` lives beside Adeline's existing persona and uses the
shared Scripture/original-language policy. Her constitutional voice remains warm,
sharp-witted, conversational, knowledgeable and candid. Biblical worldview,
sanctity of life, primary sources, incentives and discernment remain present.
No pet names, theatrical directions, busywork, formulaic praise or forced morals.
Direct instruction is allowed; missing knowledge is taught before application.

## Source package adaptations

| Packages | Application |
| --- | --- |
| understanding-by-design, curriculum-planner, spiral-curriculum | Goal/evidence-first blueprint, ordered scenes, proposed conceptual deepening. A cross-unit revisit scheduler is not yet implemented. |
| k12-core-literacy-planning | Observable tasks and differentiated family responsibility; Chinese standards/ideological categories are not imported. |
| zone-of-proximal-development, feynman-learning | Coach responds to actual work, teaches missing knowledge, models another case, invites explanation and fresh checks. No claimed ZPD score or automatic mastery. |
| workshop-style, vocational, lecture-style, deep-interactive | Select explanatory, practical, project and interactive formats by learning need. No fixed widget/page ratios. |
| learning-to-learn, social-emotional-learning | Recall, prediction, reflection and cooperation where useful; no forced personal disclosures or psychological diagnosis. |
| fact-check, deep-research | Source context from existing resource router; no fabricated citations or self-certified verification. Full inspected-source claim auditing remains outstanding. |
| stage-design, stage-dsl | Blueprint, cast, scene-by-scene persistence, complete-document validation and recovery. |
| slide-craft, slide-dsl, pro-editing, page-clone, style-clone, teacher-style-clone, pptx-import | Readability and separation of content/delivery. SDK pixel rules, deck editing/import, template cloning and teacher impersonation are not imported into this first classroom player. |
| openmaic | Architecture/setup reference. Existing Dear Adeline deployment/provider configuration is used; no local OpenMAIC installation is required. |

The package manifest records the 24 distinct uploaded skill hashes. These files
are design inputs, not evidence that an educational method has proven an outcome.

## Files and release checks

- `adeline-brain/app/curriculum/classroom.py`: typed classroom/scene contracts and
  blueprint/scene author instructions.
- `adeline-brain/app/api/classrooms.py`: authenticated planning, building,
  reopening, listing, responses and live scene conversation.
- `adeline-brain/app/agents/persona.py`: classroom identity and Scripture policy.
- `adeline-ui/src/lib/classroom-client.ts`: authenticated transport and ten-track labels.
- `adeline-ui/src/components/classroom/ClassroomPlayer.tsx`: new delivery surface.
- Existing lesson/Space route files: replaced with classroom plan/player/list.
- `adeline-brain/tests/test_classroom.py`: invariants, hidden keys, reset boundary,
  checkpoint building and honest failure handling.
- Classroom UI tests: server feedback, save-before-navigation and live conversation.

Run focused backend tests, UI tests, TypeScript, Python compilation and whitespace
checks before review. Before production: test the reset migration on a staging
copy, generate and inspect a classroom with the real configured model, exercise
four learners, verify persistence after restart, and confirm model/source latency.
The reset SQL passed a PostgreSQL WASM smoke test on synthetic tables, including
rerun idempotency and preservation of new classrooms/accounts/evidence/characters.
This does not replace staging against the complete schema. No live model classroom,
production database migration, browser visual inspection,
production deploy, or complete standards coverage audit is claimed by unit tests.

Validation recorded: 195 UI tests passed; TypeScript passed; 82 focused backend tests passed before the final persona-injection regression was added (that regression is also checked). Python compilation, targeted Ruff and whitespace checks passed.
