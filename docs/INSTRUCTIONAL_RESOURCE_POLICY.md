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
diagnostic question, not a vocabulary packet. Output
is a student-facing text resource inside Adeline's chat; this implementation does
not create slide decks, downloadable worksheets, or third-party Diffit resources.
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
