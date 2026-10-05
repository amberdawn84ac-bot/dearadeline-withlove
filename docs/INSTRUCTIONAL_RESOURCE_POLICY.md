# Need-first instructional resources

Every authenticated Space conversation turn can now select a teaching move
before the teaching response. The saved canonical activity fixes the target;
the planner must copy its block identity and objective. This is an extension of
the existing Space and resource router, not a second curriculum generator.

The planner receives the current activity/lesson, speaker depth, family roles,
evaluated skill records, recent conversation and outside-resource catalog.
Grades and BKT probabilities are not mastery evidence. Unverified understanding
is not a diagnosed misconception. The planner chooses one route:

| Route | Action |
| --- | --- |
| none | Teach, converse, diagnose, or move forward without an artifact. |
| real_world | Make a brief observation/investigation guide; check material availability. |
| existing | Select up to two identifiers from the existing resource catalog. |
| generate | Make a resource for a specific instructional need. |

The separate maker receives the decision contract and the same saved context.
It produces direct teaching, materials, steps, and an evidence prompt. Available
moves include comparison, worked examples, retrieval, guided practice, labs,
evidence reasoning, vocabulary/reading support, extensions, and performance tasks.
`resource_toolbox.py` defines each move's meaning, when to use/avoid it, required
components, success check, exit rule and maximum duration. Both planner and maker
receive the relevant contracts. Guided practice models a task, fades help, and
checks a fresh independent attempt. Vocabulary support requires an identified
obstructing term; an uncertain language-versus-concept barrier calls for a
diagnostic question, not a vocabulary packet. Output is a student-facing resource inside Adeline's chat. Structured science
labs also provide an editable notebook, measurement table, optional graph from
entered measurements, and claim/evidence/reasoning fields. This implementation
does not create slide decks, downloadable worksheets, or third-party Diffit resources.
Simulated data must be labeled, source ids must belong to supplied context, and
unknown crime evidence is not used for a household experiment.

Planning and making each have a twelve-second timeout. On failure, the saved
activity and original teaching path remain available. Resources do not select
new curriculum targets, modify shared canonical facts, or award mastery. A new
generated intervention holds the current activity until a later response. The
next teaching turn sees the previous resource and interprets its evidence prompt,
while the canonical activity still defines the advancement requirements.

The decision and resource are committed with the assistant message under the
existing session lock/version check. Resource-bearing messages survive ordinary
chat trimming and are rendered again on reopening. A replacement experience
still follows the existing session reset behavior; this is not a cross-revision
resource archive. No new database schema or provider credentials are required.

This decision step runs on conversation turns, including the first learner
response. Opening a page alone does not invoke a model or generate resources.
The existing canonical author still prepares the initial saved experience.

## Validation and release

Regression coverage includes separate planning/making, all four routes, unknown
target/source rejection, provider failure recovery, no advancement when a new
resource is issued, retained resource history, and reopening in the chat UI.
Run the focused Python suites, UI chat/schema tests, and UI TypeScript check.
Live teaching quality, response latency, and real database/browser operation
remain release verification steps. The earlier unified-curriculum migration on
main still has its own staging/release requirements.

## Shared subject philosophy

`app/curriculum/teaching_policy.py` contains the shared policy used by the
canonical author, adaptation editor, instructional resource planner/maker,
investigation planner, and Space evidence evaluator. Reviewed against Campfire's
published subject approaches at https://campfirecurriculums.com/high-school-themed-studies/
on October 5, 2026, it translates the philosophy into original operational rules:
science builds and revisits foundations; history weighs source provenance and
conflicting evidence; ELA uses recurring, purposeful reading and language work.
User requirements retain priority. Existing learner evidence determines support;
completed activities alone do not award mastery. Prompt instructions guide model
behavior and still need review of real generated materials.

## Science notebooks and coordinated sessions

A generated `science_lab` supplies a validated blank notebook specification.
The learner can save unfinished work and reopen it in the same Space. The server
validates that the notebook belongs to that session and checks measurement columns
and finite numbers. Drafts and revisions to earlier activities cannot advance
the current activity. Graphs use entered measurements, never invented results.

Parents can preview two to ten coordinated sessions through Plan a unit, edit
them, then use the existing Queue unit flow. The planner supplies a shared
question, ordered tasks, evidence requirements and resource suggestions. The
existing canonical author builds each experience. Earlier sessions' saved lab
notebooks and learner responses provide context for the same learner in later
sessions; siblings' evidence is not cross-credited. A session may span multiple
days. Advancement remains the existing explicit completion flow.

## Exact skill sequencing and mini-units

Sequential math/literacy work retains its concept or standard ID, working level,
readiness and prerequisites when it is projected into a separate Today card.
The single canonical author receives current targets and an explicit fit rule.
A mini-unit must bind the exact target to a real lesson and independent
demonstration block; an unrelated or unbound draft enters the author's repair
loop instead of becoming a ready learner experience. Mini-unit cache identity
includes target and level, while shared family canonicals remain shared.

The Space teacher sees the bound evidence requirements. Correct independent
responses on those blocks record the exact skill in StudentSkillState. Guided
responses, teaching-block acknowledgments, partial responses and unrelated
lesson scores do not award that skill. Bound progression work is not credited
by a nearest-topic standards search. Server-side opening checks reject stale
readiness claims. Concept prerequisites and placed/verified standards sequences
use evaluated skill state, not BKT estimates or a sibling's performance.

This does not invent missing prerequisite edges or certify unmapped sequences.
Older probability/legacy mastery records alone no longer unlock the next skill;
existing evaluated evidence remains authoritative. Tests cover inside/outside
unit routing, target preservation, author binding, partial/independent evidence,
stale requests and the actual concept-prerequisite SQL in GitHub Postgres.
Live model quality and the deployed browser flow still need hands-on review.
