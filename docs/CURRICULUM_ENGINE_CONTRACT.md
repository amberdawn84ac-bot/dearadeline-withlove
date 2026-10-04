# Dear Adeline curriculum engine

Dear Adeline has one shared reality and many learners. The canonical defines
shared content. Curriculum state selects work the learner is ready to do.
Adaptation selects participation. Evaluated evidence determines demonstrations.

## Authorities

- `FamilyUnit` is a context containing ordered `FamilyUnitExperience` records.
- `FamilyUnitQueue` has at most one active row per household, enforced by a
  PostgreSQL partial unique index. Neither calendar dates nor Today reads advance it.
- `/curriculum/households/{id}/units` queues an explicit list of experiences.
  The historical queue endpoint is a compatibility wrapper into this same store.
- `CanonicalLesson` remains the shared content store. A unit may reference many
  canonicals; a canonical is reusable by multiple households.
- `canonical_author.py` is the family authoring contract. Repository canonicals
  are implementations of that contract, not a second generative pipeline.
- The five semantic stages are READ, EXPLORE, WRITE, APPLY, EXPERIENCE in that
  order. They refer to rendering blocks, which do not determine stage membership.
- `curriculum_state.py` reads evidence-backed skill state and legacy standards/
  BKT signals. BKT probabilities remain scheduling signals, separate from proof.
- `StudentCharacter` belongs to the student. Name, identity and role preferences
  do not enter canonical truth, source or measurement fields.
- `EvidenceAttempt` and `EvidenceEvaluation` form an append-only ledger.
  Corrections create child attempts. Canonical revision changes invalidate only
  cached adaptations, not attempts, evaluations, journal or Space records.
- `StudentSkillState` changes through evidence evaluation. Opening a page,
  finishing navigation, or completing a unit never awards mastery.
- Portfolio is a projection of attempts and reviews. Timeline cards reference
  actual attempts with dates, sources, missing perspectives and uncertainty.

## Selection rules

Math and reading use the next ordered target. An exact skill identity plus a
concrete task and reviewable evidence is required to attach that target to the
family experience. Otherwise the existing individual skill path remains.
Keyword overlap, theme similarity and whole-subject similarity do not align skills.
Locked skills cannot attach. History and other open disciplines may select an
appropriate year skill with the same explicit demonstration requirement.

Science foundations follow transitive prerequisite edges, ordered from deepest
foundation to the target. Secure/demonstrated foundations become REVIEW,
developing ones REINFORCE, and absent demonstrations TEACH. A mastered foundation
is not removed from the path. Unknown graph edges are not invented by an author.

Apply review and stretch visibility use evidence state. Grade determines the
responsibility band, not whether understanding has been demonstrated.

## Progression and review

A parent explicitly confirms completion of each current family experience.
Only after all experiences are complete can the parent advance the unit.
Advancement locks the household, completes the identified queue row, and
activates the next queued row in one transaction. Retrying a completed unit's
advance cannot advance another unit. These actions never evaluate mastery.

Manual evidence evaluation requires a verified parent or administrator with
access to the child. A student cannot self-award mastery. Space/journal reviews
preserve their evidence in the same ledger before recording skill-state changes.
A Space completion without a correct demonstration does not increase BKT.

Real service claims require a recipient, need, deliverable, delivery method,
success signal and evidence requirement. This contract works across all ten
tracks. Faith is integrated where the subject bears on it; stage presence does
not imply that every experience needs a separate Scripture block.

## Additive migration and release

Apply `prisma/migrations/20261003_unified_curriculum/migration.sql` before starting
the new API. It merges unfinished legacy science/history rows by original creation
order with deterministic tie breakers. Existing canonical, journal and Space
records stay intact. Migrated entries retain their historical Space identifiers.
New forensic units contain ten separately addressable canonical experiences;
legacy forensic records keep their original whole-unit canonical.

Keep the legacy queue table/store during rollout. Production reads and writes use
the new unit store. Do not remove historical data during this release. Database
checks, status constraints and append-only triggers are SQL-owned invariants.

Required release verification: run the migration against a staging copy, test
concurrent enqueue/advance, open sibling experiences, save/reopen/revise notes,
review evidence, revise a canonical, and verify old evidence survives. Then deploy
API and UI together. Do not deploy the code before the schema migration.

The legacy BKT, standards and journal projections remain for compatibility; migrate
consumers through the curriculum-state service before removing their old interfaces.
Full staging/production verification is a release step, not proven by mocked tests.

## Validation for this implementation

Focused regression suites cover unit selection, one active lane, explicit skill
fits, ordered math exceptions, sibling participation, five stages, ten forensic
canonicals, character integrity, revision invalidation, Space evaluation, journal
portfolio, and evidence idempotency. TypeScript and lesson UI tests are required.
The migration has not been executed against a real PostgreSQL database in this
workspace; staging execution and browser verification remain required before release.
