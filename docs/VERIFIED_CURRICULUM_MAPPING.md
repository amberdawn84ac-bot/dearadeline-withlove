# Reviewed prerequisite mapping

The bundled `adeline-brain/data/seeds/verified_standard_progressions.json` contains
30 reviewed instructional prerequisite relationships: 23 foundational ELA edges
and 7 mathematics edges. Each relationship uses existing compound standard IDs
and carries its source URL, source version, review date, and evidence location.

`VERIFIED` means the source supports this specific relationship and both local
standard identities were checked. It does not mean Oklahoma prescribes a single
teaching order. These are Adeline's reviewed instructional prerequisites.

## Source review, October 5, 2026

- Oklahoma's **2021 ELA Vertical Progressions, Grades PK–5**, printed pages
  5–14, supplies the aligned foundational literacy progressions and explicitly
  identifies sequential phonics/spelling skills. The shipped subset covers
  phoneme manipulation, print formation, phonics, syllable types, structural
  analysis, and spelling. Repeated reading/writing processes are not converted
  into blanket hard prerequisites.
- **OKMath Framework (2022 OAS-M)** objective pages 4.N.3.1, 6.N.1.1, and
  6.N.3.1 explicitly identify prior-knowledge or leads-to relationships. The
  shipped subset covers fraction models/equivalence, number-line understanding,
  ratios, and unit rates. The notes paraphrase the relationships; source teaching
  materials are not copied into student lessons.

## Runtime behavior

On startup, after the OAS catalog is seeded, the existing progression importer
validates and upserts this map. Missing catalog identities or a verified cycle
stop the import. Restarting does not duplicate edges. Existing reviewed mappings
outside this bundle are retained.

The planner follows reviewed prerequisites backward, including earlier grades,
and offers the unfinished foundations. It also includes earlier objectives
needed by existing within-grade progression lanes. Only that learner's evaluated
`demonstrated` or `secure` skill evidence opens a dependent objective. Developing
work and a sibling's evidence do not open it. The foundational mini-unit uses
its actual working level and the existing canonical lesson author.

## Coverage still requiring review

This is partial verified coverage, not a complete PK–12 prerequisite map.
Remaining mathematics branches, secondary literacy, and science relationships
still require individual source review. Existing placement metadata is not proof
of a verified prerequisite.

The earlier `Dear_Adeline_Oklahoma_2026_Science_Prerequisite_Graph.zip` was inspected.
Its rules and concept edges explicitly identify instructional inference. They
are not promoted to verified gates merely because the package cites an official
science PDF. Shared DCI/SEP/CCC labels alone are insufficient evidence for a
strict prerequisite.
