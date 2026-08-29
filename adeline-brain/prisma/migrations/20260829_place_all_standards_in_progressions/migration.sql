-- Every standard receives an explicit place in a progression. This does not
-- invent cross-lane prerequisites; VERIFIED relation rows remain the authority
-- for those additional locks.

ALTER TABLE "OASStandard"
    ADD COLUMN "progressionLane" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "progressionMode" TEXT NOT NULL DEFAULT 'OPEN',
    ADD COLUMN "progressionOrdinal" INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN "progressionSourceTitle" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "progressionSourceUrl" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "progressionSourceVersion" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "progressionEvidenceNote" TEXT NOT NULL DEFAULT '',
    ADD COLUMN "progressionReviewStatus" TEXT NOT NULL DEFAULT 'PLACED',
    ADD COLUMN "progressionParentId" TEXT,
    ADD COLUMN "progressionIsTerminal" BOOLEAN NOT NULL DEFAULT TRUE;

WITH placed AS (
    SELECT code,
           LOWER(track) || ':' || COALESCE(NULLIF(LOWER(REGEXP_REPLACE(strand, '[^a-zA-Z0-9]+', '-', 'g')), ''), 'core') AS lane,
           ROW_NUMBER() OVER (
               PARTITION BY track, COALESCE(NULLIF(strand, ''), 'core')
               ORDER BY grade,
                        CASE difficulty
                            WHEN 'EMERGING' THEN 0 WHEN 'DEVELOPING' THEN 1
                            WHEN 'EXPANDING' THEN 2 WHEN 'MASTERING' THEN 3 ELSE 4
                        END,
                        code
           ) AS ordinal
    FROM "OASStandard"
)
UPDATE "OASStandard" standard
SET "progressionLane" = placed.lane,
    "progressionOrdinal" = placed.ordinal,
    "progressionMode" = CASE
        WHEN standard.track IN ('ENGLISH_LITERATURE', 'APPLIED_MATHEMATICS') THEN 'SEQUENTIAL'
        WHEN standard.track IN ('CREATION_SCIENCE', 'HEALTH_NATUROPATHY', 'HOMESTEADING') THEN 'SCAFFOLDED'
        ELSE 'OPEN'
    END,
    "progressionSourceTitle" = CASE standard.subject
        WHEN 'English Language Arts' THEN 'Oklahoma ELA Vertical Progressions'
        WHEN 'Mathematics' THEN '2022 Oklahoma Academic Standards for Mathematics'
        WHEN 'Science' THEN 'Oklahoma Academic Standards for Science'
        WHEN 'Social Studies' THEN 'Oklahoma Academic Standards and Frameworks'
        WHEN 'Health' THEN 'Oklahoma Health Education Standards and Guidance'
        ELSE 'Dear Adeline Ten-Track Curriculum Constitution'
    END,
    "progressionSourceUrl" = CASE standard.subject
        WHEN 'English Language Arts' THEN 'https://oklahoma.gov/education/services/standards-learning/english-language-arts/standards.html'
        WHEN 'Mathematics' THEN 'https://oklahoma.gov/education/services/standards-learning/mathematics.html'
        WHEN 'Science' THEN 'https://oklahoma.gov/education/services/standards-learning/science.html'
        WHEN 'Health' THEN 'https://oklahoma.gov/education/services/standards-learning/safe-and-healthy-schools/health-education-resources.html'
        WHEN 'Social Studies' THEN 'https://oklahoma.gov/education/services/standards-learning/oklahoma-academic-standards.html'
        ELSE 'https://github.com/amberdawn84ac-bot/dearadeline-withlove'
    END,
    "progressionSourceVersion" = CASE standard.subject
        WHEN 'English Language Arts' THEN '2021'
        WHEN 'Mathematics' THEN '2022'
        WHEN 'Science' THEN '2020/2026'
        ELSE 'current catalog'
    END,
    "progressionEvidenceNote" = 'Placed by published grade, strand, and objective order. Placement orders the next target inside a lane; separately VERIFIED prerequisite edges govern cross-lane locks.',
    "progressionReviewStatus" = 'PLACED'
FROM placed
WHERE standard.code = placed.code;

UPDATE "OASStandard" parent
SET "progressionIsTerminal" = FALSE
WHERE parent.code LIKE '%_Standard %'
   OR EXISTS (
       SELECT 1 FROM "OASStandard" child
       WHERE child.subject = parent.subject
         AND child.grade = parent.grade
         AND child.code LIKE parent.code || '.%'
   );

UPDATE "OASStandard" child
SET "progressionParentId" = (
    SELECT candidate.code
    FROM "OASStandard" candidate
    WHERE candidate.subject = child.subject
      AND candidate.grade = child.grade
      AND child.code LIKE candidate.code || '.%'
    ORDER BY LENGTH(candidate.code) DESC
    LIMIT 1
);

CREATE INDEX "OASStandard_progressionLane_progressionOrdinal_idx"
    ON "OASStandard"("progressionLane", "progressionOrdinal");
