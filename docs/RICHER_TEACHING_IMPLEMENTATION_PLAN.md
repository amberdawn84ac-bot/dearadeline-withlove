# Richer teaching: foundation and implementation plan

Prepared October 20, 2026. Application baseline: main
`33f35dea6e43284010a4e020fc146ba73168c8fa`.

## Outcome and scope

When a learner asks to explore a topic, Dear Adeline should build an accurate,
visually understandable experience with meaningful things to inspect, change,
make, explain and revisit. Changing the learner must change concept selection,
representation, pacing, support and responsibility, not only vocabulary. Adeline
guides the actual experience on screen and responds to the learner's work.

Keep the existing repository, React/Next frontend, Railway Python backend,
authentication, canonical store, evidence ledger, learning plan, ten tracks and
Adeline persona. Use Explore language. Daily Bread remains a distinct Bible
experience. Do not revive the archived world prototype, add a second student
identity, overwrite existing lessons, or create a competing credit system.

This document is the forward implementation plan for richer teaching. Older
implementation reports remain historical records; their feature counts are not
the current acceptance checklist. The broader separate-game vision in
PLATFORM_NORTH_STAR.md is not a prerequisite for improving this existing app.

## What is already present

Code presence is separate from proof of production behavior or learning outcomes.

| Area | Current foundation | Remaining work |
| --- | --- | --- |
| Dependencies | React 19, Next 16, Tailwind 4; pinned pnpm/Node and Python graph | Keep reproducible builds; evaluate SDK peers when actually adding them |
| Authoring | Goal/evidence-first blueprint, teaching design, scene purposes, per-scene generation, retries and saved checkpoints | Explicit learner profile, visual briefs, quality review and durable job execution |
| Reuse identity | Level, targets, learning need and authoring revision included | Structured profiles and support conditions; tested cache invalidation as contracts change |
| Interactions | Three numerical models; sorting; water heating; mass balance; linked diagrams; molecule composition | More reusable mechanisms, richer games, visual explanation and transfer tasks across subjects |
| Narration | Device speech; one part at a time; pause/resume/stop; section and diagram-node focus | Typed actions targeting real visual objects and controls; interruptible demonstration; optional durable audio |
| Sources | Rights-aware routing and attached text/link/image cards | Read and ground exact claims; real scene-specific media selection and usable source workspaces |
| Learner evidence | Prediction before reveal; recorded trials; server-recomputed outputs; saved responses and coaching context | More artifact types, explicit assistance reporting, interrupted/offline recovery and full authenticated acceptance |
| Review and next work | Assessment against supplied targets, skill states, diagnosed practice, plan-cache invalidation | Live-model calibration, independent transfer/retention, complete gap visibility, review scheduler |
| Credit | Parent-defined course scopes, evidence readiness and transactional parent-approved awards | Signed-in acceptance, evidence revision/revocation handling and clear parent explanations |
| Family | Differentiated roles and learner-specific records | Reliable shared-session coordination, individual readiness, no duplicate family work or sibling evidence leakage |
| Visual delivery | Responsive prose, native controls and simple model illustrations | Rich slide compositions, source annotations, accessible charts and mobile visual layouts |

Current implementation evidence is in `OPENMAIC_SKILL_APPLICATION.md`,
`INTERACTIVE_CLASSROOM_MODELS.md` and `LEARNING_LOOP.md`. Existing tests do not
establish complete K–12 mapping or that live AI assessments are educationally sound.

## Foundation delivered with this plan

`app/curriculum/runtime_capabilities.py` supplies a fresh, JSON-safe authoring
catalog of installed scene types, eight mechanisms, narration, saved evidence
and unavailable features. It derives supported enum values from actual schemas,
rejects a catalog/schema mismatch and fingerprints the capability descriptions
plus the scene schema.

- Planning and scene-generation contexts receive the catalog. New planned records
  retain its snapshot. The catalog is teacher-side infrastructure, not student UI.
- New canonical identities include the fingerprint. New requests cannot silently
  reuse content authored for a different capability contract.
- Existing saved plan-item IDs and document format remain unchanged. Existing
  request comparison and reopening behavior remain in place; no wipe or migration.
- A dedicated regression checks catalog isolation, cache separation and planning
  context. Scene checkpoint tests check delivery context. The learning-loop CI
  job includes this regression and now installs the committed Python lockfile.

The catalog is not a plugin installer, arbitrary-code executor, browser feature
detector or claim that future features already work. Schemas and server-side
submission validation remain the enforcement boundary. Renderer parity becomes an
explicit release gate below.

## Architecture decisions

1. **Extend one lesson pipeline.** Keep blueprint → scene content → delivery →
   learner work → reviewed evidence → plan/course record. Separate content and
   teaching actions as authoring stages inside that pipeline, not independent apps.
2. **Reuse mature components at an adapter boundary.** Evaluate the upstream
   read-only renderer first. Keep our native document, source provenance and
   server-side evidence contracts authoritative. Do not fork the whole product
   or replace Python generation simply to display slides.
3. **Prefer typed, code-owned mechanisms.** Generate tasks/configuration around
   validated relationships. A novel simulation requires an implemented mechanism,
   domain checks and tests; a plausible animation alone is not a scientific model.
4. **Version content and capability separately from learner work.** Keep immutable
   evidence, submission idempotency, target mappings, evaluated revisions and
   parent decisions. A rendering upgrade must not silently regrade saved attempts.
5. **Progressive enhancement.** Every essential visual/action has a useful text or
   accessible control equivalent. Missing speech/media must not block learning.
6. **Use existing providers and jobs.** Keep configured Gemini/provider boundaries;
   no new keys or paid subscriptions assumed. Use the existing ARQ/Redis/Postgres
   infrastructure for durable work unless an evaluated limitation requires change.

### Upstream evaluation, pinned rather than assumed

Inspected upstream `THU-MAIC/OpenMAIC` at
`6e20534fe01e21c69363571b737e3a61f993b3f0` on October 20:

- `@openmaic/renderer` source version 0.1.16: read-only `SlideCanvas`, typed visual
  elements, effects, media slots; React >=18, Tailwind >=4 and `motion` >=11 peers.
- `@openmaic/generation` source version 0.3.22: generation contracts and packaged
  prompt assets. This is an integration candidate, not installed in our pipeline.
- Interactive DSL represents simulation, diagram, code, game, 3D and procedural
  widgets, commonly delivered as HTML in an iframe. Our player does not thereby
  gain those capabilities.
- The renderer package is MIT-licensed in the inspected manifest. Check the
  actual published artifact/version, notices and asset licenses before adoption.
- Optional renderer fonts reference an external host. Preserve Dear Adeline's
  existing fonts; do not introduce a silent external font dependency.

Source: [renderer README](https://github.com/THU-MAIC/OpenMAIC/blob/6e20534fe01e21c69363571b737e3a61f993b3f0/packages/@openmaic/renderer/README.md),
[renderer manifest](https://github.com/THU-MAIC/OpenMAIC/blob/6e20534fe01e21c69363571b737e3a61f993b3f0/packages/@openmaic/renderer/package.json),
[generation manifest](https://github.com/THU-MAIC/OpenMAIC/blob/6e20534fe01e21c69363571b737e3a61f993b3f0/packages/@openmaic/generation/package.json),
[interactive contract](https://github.com/THU-MAIC/OpenMAIC/blob/6e20534fe01e21c69363571b737e3a61f993b3f0/packages/@openmaic/dsl/src/interactive.ts).

## Implementation sequence

Each phase is a reviewable main-branch change with tests and a clear exit gate.
Do not count a proposed schema, unconnected component or passing build as the
finished experience. Estimates should follow the renderer trial, not invent
delivery dates before compatibility and model latency are measured.

### 1. Learner context and reference cases

**Changes:** Replace ambiguous level strings at the internal authoring boundary
with a versioned learner context: individual/family mode, declared grade, actual
subject working level, supplied targets, reviewed prerequisites, language/reading
support, input preferences and available time/materials. Do not diagnose ability
from grade. Keep an adapter for existing free-text requests and preserve original
values. Send the intended level/objective to ResourceQuery; it currently defaults
to grade 8 when the exploration route omits it. Make single-learner/family intent
explicit without requiring a questionnaire for each new topic.

Use only task-relevant learner information in model calls. Do not put names,
private work or assessed states into a globally shared canonical key. Separate
shareable lesson design from student-specific work and ephemeral adaptation.

**Files:** `api/classrooms.py`, `classroom-client.ts`, lesson opening page,
`select-planned-task.ts`, resource router, curriculum-state/learning-plan boundary.

**Gate:** Grade-three and grade-eight Matter requests have different scope,
representations and tasks. Siblings retain separate skill states. Saved old work
reopens. A deliberate family request shares facts but gives meaningful individual
responsibilities. Resource selection uses the actual audience. No invented official
standards or verified prerequisite relationships.

### 2. Visual scene contract and renderer trial

**Changes:** Trial the pinned read-only OpenMAIC renderer in an isolated adapter
inside the existing UI. Exercise text, image, shape, connecting line, table,
formula and chart with actual compiled Tailwind styles. Inspect server rendering,
dynamic loading, package size, font behavior and media slots. Add `motion` only if
needed by the chosen artifact; current `framer-motion` is not assumed to satisfy
that package name. Start without the editor or optional code/chart dependencies.

Define an additive, versioned `visual` payload for a scene, including stable
element IDs, captions/alt text, source IDs, relationships, highlights and a reading
equivalent. Validate geometry, text density, references and supported element types.
Translate that payload to the renderer's Slide shape through one adapter. Keep
existing prose scenes fully readable. Use responsive rearrangement or a reading
view on narrow screens; do not merely shrink a 1000 px slide until text is tiny.

**Files:** `curriculum/classroom.py`, new visual schema/adapter, classroom UI,
Tailwind sources, client contract and tests. Shared exports may live in core once
the contract settles. Do not duplicate handwritten contracts indefinitely.

**Gate:** A real visual explanation at 390 px and 1280 px, keyboard-readable text,
no clipped content, meaningful image alternatives, no raw markup/formulas or
unresolved asset placeholders. Old saved lessons still render. Record a measured
renderer decision and dependency/asset notices. If the trial fails the gate,
implement a smaller native visual adapter against the same document contract.

### 3. Coordinated teaching actions

**Changes:** Extend speech actions compatibly with a discriminated action model:
speak, focus an existing element/node, annotate, reveal, set supported widget
inputs, pause for learner action and clear emphasis. Generate actions after scene
content exists, supplying the inventory of real element IDs and allowed commands.
Validate target references and input bounds before persistence. A teacher demonstration
must be distinct from learner-recorded trials and may not overwrite their work.

Build one interruptible action executor with cancellation tokens, readiness/ack
handling, bounded waits and no replay of stale scene actions. Support stop, resume,
replay, mute and captions. Action pacing waits for actual learner participation
where intended; narration must not answer an independent check in advance.

**Files:** Speech/scene contracts, authoring endpoint, `ClassroomPlayer.tsx`,
`ActivityLab.tsx`, new action executor and deterministic playback tests.

**Gate:** Adeline demonstrates a supported control, highlights the exact object,
pauses, accepts a learner attempt and responds. Navigating away cancels speech
and effects. Replay cannot change saved evidence. Unavailable speech uses the same
text/action sequence. A generated action cannot target an absent object.

### 4. Reusable activities and games

**Changes:** Expand a mechanism registry by learning need, with control schema,
code-owned rules, representation, assessment limitations and persistence strategy
for each mechanism. First additions: observable-property/matter hunt; compressible
air volume/pressure demonstration with stated model assumptions; sequencing and
matching; expandable process/source diagrams; quantitative graph comparisons.
Then evaluate atomic structure, circuits, forces, ratios, timelines, language
editing and source-comparison mechanisms where curriculum demand warrants them.

Use the existing water/mass/composition models rather than replacing tested
physics with generated formulas. Generalize sorting only when multi-category or
ambiguous answers have a real validation contract. Create game loops around a
decision and its consequences, followed by explanation/transfer. Speed, points
or finishing a round do not establish mastery. Give untimed and keyboard options.
Let learners build or modify a model/game when that serves the learning goal.

Existing approved outside games may be linked or embedded only in a supported,
rights-aware mode, with a concrete task and a route back to evidence. Generated
game code remains out of scope until the separate isolation gate in phase 9.

**Gate per mechanism:** Explain what changes and why; test domain boundaries,
scientific/accounting invariants, save/reload, partial work, retries, touch and
keyboard input, reduced motion, and server recomputation or another explicit
validation strategy. Tests must fail on deliberately wrong outputs. No random
fact quiz disguised as a game or repeated controls with a different background.

### 5. Source, media and claim grounding

**Changes:** Introduce source-item and asset manifests with stable IDs, actual
retrieved content, origin, creator/date when known, retrieval time, rights,
attribution, permitted use, availability and supported claims. Separate discovery
links from inspected items. Scope source excerpts to particular scenes; store a
claim-to-source ledger and distinguish quoted text, paraphrase, inference and
illustration. Check high-impact claims and contradictions after scenes exist.

Add real image/map/document viewing with annotation and comparison. Preserve a
source record when an asset is resized or excerpted. Queue optional generated
illustrations/audio through existing provider configuration, with budget, retry,
storage, attribution where needed and visible failure fallback. Never generate
an illustration and label it historical photographic evidence. No external account
or new paid provider is assumed.

**Files:** resource router, scene materials, source manifest/store, media delivery,
authoring inputs, parent review and reading/source components.

**Gate:** Every displayed asset resolves, every direct quote matches its source,
every researched claim has the relevant inspected support, and unknown rights
stay link-only. Broken media does not produce a character claiming it is visible.
Test a primary-source lesson, a scientific model and a literature passage.

### 6. Adaptive teaching, gaps and revisits

**Changes:** Operationalize the teaching skills using actual work: a short initial
attempt; one observed difficulty; targeted explanation or another worked example;
guided practice; then a comparable fresh independent task. Allow already-capable
learners to bypass unneeded support. Record self-selected hints, model demonstrations,
coaching and answer exposure. Absence of recorded help is not proof of independence.

Use the existing reviewer/skill-state/plan projection. Add reviewer calibration
fixtures for right reasoning, plausible wrong reasoning, copied text, ambiguity,
prompt injection, unsupported target mappings and changing support conditions.
Use honest confidence/needs-review behavior, not a diagnostic ability score.
Preserve original work and parent overrides. A fresh successful task does not by
itself establish durable retention or a full standard.

Implement a review queue linked to the learner's existing plan: retention check,
transfer context, due reason, previous evidence and what the revisit adds.
Prioritize ordered math/reading gaps using verified prerequisites; when the family
unit has no genuine fit, author a separate coherent mini-unit through this same
pipeline. Show unmapped curriculum areas to the parent and queue mapping review.
Do not claim complete coverage until the target inventory and verified graph are
actually complete for the selected graduation/competency profile.

**Gate:** Struggle leads to useful practice; demonstrated readiness advances to
the next supported target; review becomes due and can be rescheduled without
duplicating family work. Parent overrides survive regeneration. No automatic
credit, invented prerequisite edges or unexplained skipped requirement.

### 7. Daily Bread and Reading Nook experiences

**Changes:** Adapt the same visual/task/action components to Daily Bread without
merging its source policy into generic lessons. Offer a brief invitation, passage,
word discovery, observation/application and conversation; deeper textual study
remains available on demand. Keep Hebrew/Aramaic/Greek source, close rendering,
published translation and interpretation visibly distinct. Compare named versions
only when their actual text is available. Do not substitute literal pictures for
poetic imagery or pretend disputed textual history is settled.

Reading Nook should retain working books, shelf and progress while adding contextual
word support, passage annotation, explanation and optional creative response.
Use the actual edition and passage position; source-linked quotations must match
the book. Assess a learner's response, never merely a finished book counter.

**Gate:** A child can read/listen, discover something, respond and reopen their
work. Deep source detail stays accessible. Books still open/add/restore progress.
Adeline answers a passage-specific question. Missing analysis never displays
authoring prompts. Scripture and literary interpretations retain uncertainty.

### 8. Family work, artifacts and academic records

**Changes:** Complete the authenticated shared-session flow with a common source
and phenomenon but individual attempts, scaffolds and evidence. Add versioned
artifact references for drawing, photo, file and optional recorded explanation,
with ownership, access, storage quotas, retrieval and deletion policies. Do not
claim media upload support before transport/storage/review are implemented.

Surface the existing saved-work → review → practice/next-target chain clearly.
Keep course-scope readiness and credit approval in the parent view. Review changes
to already-credited evidence through explicit superseding records and course
reconsideration, never by silently deleting a transcript entry or double counting
the same objective. Explain missing course evidence and the equivalency rationale.

**Gate:** Four authenticated learner accounts work on one family theme with
different tasks. Each can retrieve only appropriate work; the parent sees all four.
An unauthorized learner cannot approve credit. A parent-approved award references
real preserved evidence and appears once after retries. Re-evaluation does not
silently invalidate or duplicate a prior award. No invented grade letters or
claims of guaranteed institutional recognition.

### 9. Durable generation and production controls

**Changes:** Move process-local generation tasks to persisted jobs with ARQ workers,
idempotent scene work, lease/heartbeat, retry bounds and restart recovery. Keep
progress and cancellation visible; separate accepted scene checkpoints from draft
output. Enforce provider/token/media budgets and rate limits. Track timings,
failure causes, invalid output, source availability and save/review retries without
logging learner text or credentials by default.

For any future executable widgets: a separate evaluated isolation design, no
same-origin access or auth tokens, restricted network, resource/time limits,
sanitized imported assets, explicit typed messaging with origin/source validation,
and server-side evidence checks. Static script syntax validation alone is not a
sandbox. Code execution/3D are optional later mechanisms, not prerequisites for
strong teaching with native activities.

**Gate:** Stop a worker mid-generation and resume accepted work without duplicate
scenes or evidence. Exhaust budgets, reject malformed output, lose network and
restore service. Parent/student authorizations hold across all new endpoints.
Measure first usable view, interaction responsiveness, generation cost/latency and
mobile memory against a recorded baseline; set product budgets from measurements.

### 10. Authoring, import and refinement tools

**Changes:** Add parent/author preview and targeted scene editing before any full
deck editor. Revalidate actions and source references after edits. Regenerate
audio when speech changes; keep evidence bound to the scene revision attempted.
Later evaluate read-only `.maic` reference import and `.pptx` import with archive
size limits, path traversal protection, resource checks and license preservation.
Import should never execute uploaded scripts by default. Template/style adaptation
requires an actual supplied reference and preserves the teaching purpose.

**Gate:** Change one scene without losing other scenes or student work; preserve
original revision and invalidate stale media/actions. Imported content remains
inspectable and source-labelled. Optional author tools do not bloat learner routes.

### 11. Release and live acceptance

Use small, independently releasable phases on main. Keep new scene capabilities
disabled until API, schema, renderer, persistence and acceptance fixtures agree.
Make enablement an explicit server configuration/catalog decision; unsupported
capabilities must never enter the authoring catalog early. Preserve old-reader
support and document additive migrations before serving new writers.

Release evidence must include generated content review, mobile/desktop browser
runs, migrated database tests, auth/ownership checks, retries/restarts and both
production deployment IDs/commit SHAs. If any gate is incomplete, report its exact
scope rather than claiming parity or a finished end-to-end system. Roll back
enablement/readers safely; do not erase evidence to recover from a bad feature.

## Acceptance reference suite

Both uploaded lessons came from OpenMAIC, not Dear Adeline. Their shapes are
useful references; they are not vetted science or required templates. Previous
manifest inspection recorded 11 scenes/6 interactions/59 audio clips for Matter
Magic (third grade), and 10/5/56 for Exploring Matter (eighth grade). The raw ZIPs
were not re-executed during this planning pass. Recover them from Library for
the renderer/import trial and preserve their original bytes as reference inputs.

| Case | What must be demonstrated | What must not be inferred |
| --- | --- | --- |
| Matter, grade 3 | Observable properties, air taking space, sorting with reasons, age-appropriate state-change exploration and a fresh explanation | Tiny atoms lecture with simpler synonyms; a certificate proving mastery |
| Matter, grade 8 | Particle/atomic models with limits, composition/classification, phase-change energy and open/closed mass accounting | Eye-catching animation as proof of physics; all invisible things are gas |
| Same topic, family ages 11/13/14/16 | Shared facts/source, different depth and responsibilities, independent saved work | One child's successful answer establishes siblings' understanding |
| Sequential math gap | Verified target, relevant worked example, guided trial, fresh independent application and next plan target | Theme forces skipped prerequisites or unrelated ratio sliders |
| History/source investigation | Inspect actual items, compare creator/date/purpose/claims, mark inference and uncertainty | Invented historical quotes or a political conclusion baked into every answer |
| Literature/Reading Nook | Actual passage, usable book link, interpretation with evidence, creative or analytical response | A character announces examples or maps that never appear |
| Daily Bread | Source wording and labelled rendering, meaningful word/context discovery, response and conversation | Translation prompts as content or unsupported claims about translators' motives |
| Family record/credit | Evidence review changes appropriate next work; parent-approved course award once, with preserved support | Activity completion automatically grants mastery, a whole course or credit in every track |

Golden fixtures must test expected mechanisms, actions, evidence conditions and
truthfulness, not force identical generated prose. Add non-science cases early
so the architecture does not become a Matter-only demo. Test at least one provider
failure and one genuinely unsupported activity request in every authoring release.

## How the uploaded skills become implemented behavior

| Skill family | Required implementation | Acceptance evidence |
| --- | --- | --- |
| UbD, curriculum-planner, spiral-curriculum | Goal/evidence alignment, prerequisite-aware sequence, purposeful revisit queue | Initial task and final transfer serve same understanding; revisit has a new relationship/context |
| deep-interactive, workshop-style | Real manipulable mechanisms and short task briefs; varied purposeful modalities | Learner changes something consequential, observes it, explains and transfers |
| lecture-style | Visual argument/explanation when it suits the subject | Coherent evidence/logic without compulsory busywork |
| ZPD, Feynman, learning-to-learn | Actual attempts, limited help, explanation revision, analogy limits, fresh check, visible strategy | Saved original/revised learner words and assistance conditions; no invented progress |
| k12-core-literacy, social-emotional-learning | Authentic tasks and age-appropriate participation/cooperation | Evidence-linked work, useful peer critique, no forced emotional disclosure or ideological import |
| vocational | Real process, tools, safe decision checkpoints and completion checks | Proceed/recheck/stop decision plus measurable work; no simulated certification claim |
| stage-design, stage-dsl | Typed planning/content/actions, resumable scene jobs, valid references and source/media readiness | Complete persisted scenes, replay/restart tests and no missing promised materials |
| slide-craft, slide-dsl | Visual contract, legible composition, geometry, formulas, contrast and responsive equivalent | Browser review at phone/desktop sizes, accessible reading and tested formula/media rendering |
| deep-research, fact-check | Inspected-source ledger and focused post-generation claim checks | Relevant source actually supports the exact claim; conflicts and uncertainty retained |
| pro-editing, page/style/teacher-style clone | Revision-aware targeted edits and reference-based adaptation | Old attempts retained, no fabricated teacher imitation, actual reference drives changes |
| pptx-import, openmaic | Evaluated SDK/import adapter, artifact/license checks, package-boundary reuse | Compatible fixture rendering/import without a parallel app or automatic script execution |

Skills inform authoring decisions and checks; naming a skill in a prompt does not
implement its tools or demonstrate an educational outcome. Current source audit
and archive hashes are recorded in `OPENMAIC_SKILL_APPLICATION.md` and
`openmaic-source-manifest.json`.

## Test and completion policy

- Run capability/scene/interaction regressions on every contract change; keep
  hidden answers, immutable predictions, recomputation and idempotency covered.
- Run learning-loop SQL tests against the migrated engine; extend with production
  Postgres/Redis auth journeys. Controlled model fixtures are not live model QA.
- Run core/UI tests, type checking and production builds for affected UI releases.
  Inspect actual rendered scenes, not only DOM test assertions.
- Record baseline lint/test debt separately. Do not quietly skip new critical
  checks or label the complete repository clean because a targeted suite passes.
- Run the authenticated child/parent acceptance suite in a designated test family,
  with data that may be removed by its documented recovery path. Do not fabricate
  real children's evidence or award credits to their accounts for testing.
- Review lesson accuracy and grade differences with both reference lessons and
  non-science cases. Count a phase finished only when the connected behavior and
  its release gate are demonstrated and recorded.

## First three implementation changes after this foundation

1. Versioned learner context and source-grade propagation, reference fixture
   harness, plus privacy-safe cache rules and saved-document compatibility tests.
2. Pinned renderer adapter trial with a complete grade-three and grade-eight
   visual explanation, accessible reading view, media slots and measured costs.
3. Typed action executor connecting Adeline's narration to those exact visuals
   and current native activities, including cancel/replay and evidence protection.

These create one demonstrable vertical slice before expanding the activity
catalog. They do not postpone family records or credits indefinitely: phases
6–8 explicitly finish and verify those existing connections.

## Foundation verification record

October 20 local results: 72 backend regressions passed, including the PGlite SQL
learning loop, plan selection, old-document reopening, native model checks and
the new catalog/context tests; 223 UI tests and 42 shared-schema tests passed.
Shared declarations and UI TypeScript checks passed. Targeted Python import and
undefined-name checks, compilation and whitespace checks passed. Installs used
the committed pnpm and Python lockfiles. No dependency or database migration was
required for this foundation.

These results validate this small foundation change. They do not validate the
future phases, live model teaching quality, authenticated family flows or full
repository lint cleanliness. Deployment verification must identify the resulting
main commit separately from this pre-publication record.
