# Dear Adeline capability contract

This file is the honest boundary between product intent and verified behavior.
“Present” means code exists. “Verified” means an automated test proves the full
identity-to-record journey. A page rendering is not end-to-end verification.

| Capability promised by the repository | Current truth | Acceptance contract |
|---|---|---|
| One student identity across lessons, reading, projects, portfolio, mastery, and credits | Partial | One authenticated learner ID must survive every write and appear in the parent record. |
| Parent owns multiple learner profiles | Partial | Parent token can create/claim/list only its children; learner tokens cannot open parent records. |
| Siblings share one family investigation with different individual work | Partial | Same household/week resolves one canonical experience; adaptations, evidence, mastery, and credit remain learner-specific. |
| Exact-grade public-school-equivalent coverage | Present, not end-to-end verified | Every required concept is mastered or scheduled; no other learner's plan leaks into the profile. |
| Living adaptive plan | Partial | Completion, struggle, interests, placement, and review needs change the next selection without erasing requirements. |
| Today is the actionable view of the internal plan | Present | Today's experience resolves from the current plan and refreshes after reviewed evidence. |
| One canonical experience pipeline | In progress | No hard-coded lesson route, repository lesson, chat shortcut, or legacy generator may bypass the approved canonical store and adapter. |
| Experience-first learner presentation | In progress | Every experience has a meaningful invitation, action/creation, and reviewable demonstration; narrative is never the default container. |
| Resource Router with rights-aware use | Partial | Provider result includes item URL, rights, attribution, access mode, age/type match, and availability; unknown rights means link only. |
| Outside games and game-building tools tied to curriculum | Partial | The Resource Router selects an approved playable game or builder, preserves provider terms, and brings the resulting work back as learner-owned evidence. Dear Adeline does not synthesize a replacement game. |
| Evidence-based mastery | In progress | Reflection records exposure; artifacts, scored demonstrations, or reviewed observations advance proficiency. |
| Traceable credit and graduation records | Partial | Credit points to evaluated evidence and cannot be sealed by generation, elapsed time, keywords, or a completion click. |
| Portfolio of accomplishments | Partial | Artifact is retrievable, owned by the learner, linked to concepts and any resulting credit, and visible to the parent. |
| Reading Nook with working shelf and reader | Partial | Add → shelf → start → reader → progress → reflection → reviewed record succeeds with one learner identity. |
| Daily Bread as a distinct Bible lesson | Present, not end-to-end verified | Deep Dive opens as a lesson; source text is sanitized; original-language/source distinctions are retained; credit requires evidence. |
| Original-language Scripture discipline | Partial | Source text, translation, interpretation, tradition, and uncertainty remain distinguishable and citations are never invented. |
| Ten-track coverage | Present | Track enum is identical across core, Brain, planner, UI, games, transcript, and database. |
| Production auth hardening | Partial | Student, parent, and admin route matrix is integration-tested; every student-ID endpoint enforces ownership. |
| Production readiness | Not verified | CI builds both frontends and runs the unskipped critical journeys against migrated Postgres and Redis. |

## Release rule

README feature status may say **Verified** only when its acceptance contract has
an enabled CI test. Until then use **Partial**, **Prototype**, **Present**, or
**Planned**. This prevents documentation from becoming a second fictional app.
