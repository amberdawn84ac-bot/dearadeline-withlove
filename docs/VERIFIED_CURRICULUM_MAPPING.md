# Complete catalog and progression review — October 5, 2026

The catalog contains 4,129 stable identities. Every identity has a reviewed
placement and dependency disposition in `standard_progression_review.json`.
There are 2,861 current published standard records, 31 explicitly ordered local
literacy subskills, 70 locally authored contextual records, and retained
legacy/container/support records. Parent headings are not separate assignments.
Historical IDs, evidence and transcripts are preserved.

| Primary source | Published records checked |
| --- | ---: |
| 2021 Oklahoma ELA, PK–12 | 772 |
| 2022 Oklahoma mathematics, PK through Statistics/Precalculus | 649 |
| 2026 Oklahoma science, PK–12 and engineering | 245 |
| 2026 Oklahoma social studies | 1,025 |
| 2026 Oklahoma health education | 170 |

Each current source record carries its actual PDF page, publication version,
URL and SHA-256. The catalog includes missing Pre-K records and preserves old
compound IDs while correcting mathematics course placement: PA 8, A1 9, Geometry
and A2 10, PC and Statistics 11. These high-school grades are Adeline placement
defaults, not a claim that Oklahoma mandates those courses in those grades.
Course names remain recorded in grade-band metadata.

## What the relationship review means

The shipped graph contains 2,719 source-reviewed relationships: 865 hard
instructional dependencies and 1,854 flexible progressions. Each edge has exact
source-section/table provenance and a review date.

- Math `Prior Knowledge` sections supply reviewed instructional dependencies;
  `Leads to` links remain flexible. One obsolete/mistyped framework reference
  (`2.A.1.4`) is explicitly rejected rather than guessed.
- All three ELA vertical progression documents cover PK–12. Their aligned rows
  supply flexible connections because literacy is recursive. Foundational
  dependencies retain the earlier source review. Starred, explicitly sequential
  phonics/spelling lists become 31 separate local subskills with hard edges in
  the published letter order. Local subskills are not additional official OAS
  standards. The parent needs its own independent demonstration.
- Science's 42 DCI progression rows are reviewed against the 2026 PDF. A
  connection ships only when both current objectives contain the named DCI
  dimension. The resulting 369 science edges are flexible supports. A shared
  dimension does not prove a strict prerequisite. The earlier inferred science
  ZIP is not promoted into hard gates.
- Social studies, health and local contextual curriculum retain appropriate
  open/scaffolded selection. Numeric objective order is not a universal lesson
  order. Source identity verification and prerequisite verification are distinct.

Every assignable identity is explicitly classified as reviewed prerequisites,
flexible support, or diagnose foundations. Genuine roots and contextual studies
need not be given invented prerequisite edges to make the graph look connected.
`VERIFIED_IDENTITY` certifies the published identity/text; it does not claim that
every objective has an official mandatory prerequisite.

## Runtime

`build_progression_placements` consumes the exhaustive review file. Retained old
codes and support dimensions are available for historical records but excluded
from new standard assignments. No IDs or evidence rows are deleted.

After the catalog seed, startup validates and upserts the reviewed graph using
the existing importer. Known identities, provenance and acyclicity are checked
before the transaction commits. Restarting is idempotent.

The planner recursively offers unfinished earlier-grade foundations using
verified hard edges. Only that learner's `demonstrated`/`secure` evidence opens
an edge; developing work, navigation and sibling evidence do not. Published
numeric order supplies an organizational priority, never an implicit hard lock.
The existing canonical mini-unit author teaches the exact eligible skill when
it has no defensible family-unit fit.

The science experience builder passes assigned standards into the existing
foundation service. Reviewed support connections and their sources reach the
bridge as REVIEW, REINFORCE or TEACH according to the learner's own evidence.
Flexible support never blocks a shared investigation.

## Reproduce and validate

`python scripts/rebuild_verified_progressions.py --source-directory <saved-primary-sources> --science-directory <saved-dci-pages>`

The offline builder requires PyMuPDF and BeautifulSoup, the exact saved PDFs,
math HTML and DCI HTML/index. Extracted progression indices are bundled under
`data/seeds/progression_sources`. It never runs in application startup.

Focused tests check exhaustive catalog/source coverage, stable IDs, corrected
courses, ordered subskills, rejected references, absence of cycles, science
bridge provenance, idempotent Postgres import and learner-specific unlocking.
The dedicated `Verified curriculum progressions` workflow executes the real
Postgres test; a skipped local database test is not counted as a pass.

This review covers the subjects in Dear Adeline's existing curriculum catalog.
It does not claim to import every optional Oklahoma subject, such as all world
languages or every fine-arts discipline. Existing local creative-economy and
worldview records remain explicitly local.
