-- CanonicalLesson: one master lesson per (topic_slug, track)
-- Generated once at adult/HS depth, adapted per student at serve time.
CREATE TABLE "CanonicalLesson" (
    "id"          TEXT        NOT NULL,
    "topicSlug"   TEXT        NOT NULL,   -- sha256(topic.strip().lower() + ":" + track)
    "topic"       TEXT        NOT NULL,   -- original topic string
    "track"       "Track"     NOT NULL,
    "title"       TEXT        NOT NULL,
    "blocksJson"  JSONB       NOT NULL,   -- list[LessonBlockResponse] at full depth
    "oasStandards" JSONB      NOT NULL DEFAULT '[]',
    "researcherActivated" BOOLEAN NOT NULL DEFAULT false,
    "agentName"   TEXT        NOT NULL DEFAULT '',
    "generatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"   TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CanonicalLesson_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "CanonicalLesson_topicSlug_key" ON "CanonicalLesson"("topicSlug");
CREATE INDEX "CanonicalLesson_track_idx" ON "CanonicalLesson"("track");
