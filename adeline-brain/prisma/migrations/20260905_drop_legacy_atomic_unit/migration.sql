-- AtomicUnit ("Atomic Learning Unit") was legacy architecture from before the
-- canonical-author pipeline existed. Never read or written by any live code
-- path (canonical_author.py, spaces.py, experience_builder.py all use
-- unit_plan.lessons[]/essential_concepts[] instead) — confirmed via repo-wide
-- search before dropping. ComponentInteractionLog, created alongside it in
-- the same original manual migration, is unrelated and still live; not touched.
DROP TABLE IF EXISTS "AtomicUnit";
