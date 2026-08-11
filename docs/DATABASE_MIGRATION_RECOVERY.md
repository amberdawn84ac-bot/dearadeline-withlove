# Production Prisma Migration Recovery

## Current failure

Railway reports:

- `P3009`: `20260327192741_init_8_track_schema` is recorded as failed.
- `P3008`: `20260529_add_focus_and_multimodal` is already recorded as applied.

The current `entrypoint.sh` responds to any failed `prisma migrate deploy` by trying to mark only `20260529_add_focus_and_multimodal` as applied. That cannot repair the failed eight-track migration and must not be treated as a successful baseline.

The application currently continues starting after migration failure. This keeps the service available, but it also means code and schema can drift silently.

## Safety rule

Do not delete migration rows, reset the database, run `prisma migrate reset`, or mark the failed migration applied until the live schema has been inspected.

Student identities, conversations, curriculum, journal records, standards evidence, credits, portfolios, and transcripts must be preserved.

## 1. Back up first

Create a Supabase database backup or point-in-time recovery checkpoint before changing migration history.

Record:

- backup/checkpoint timestamp
- current Railway deployment ID
- current Git commit
- database host and database name, without copying credentials into an issue or log

## 2. Inspect migration history

Run this read-only query in the Supabase SQL editor:

```sql
SELECT
  migration_name,
  started_at,
  finished_at,
  rolled_back_at,
  applied_steps_count,
  logs
FROM "_prisma_migrations"
ORDER BY started_at;
```

For `20260327192741_init_8_track_schema`, determine:

- whether `finished_at` is null
- whether `rolled_back_at` is null
- the exact failing statement in `logs`
- whether `applied_steps_count` is greater than zero

## 3. Inspect the objects from the failed migration

These checks are read-only:

```sql
SELECT typname
FROM pg_type
WHERE typname IN (
  'UserRole',
  'Track',
  'BlockType',
  'EvidenceVerdict',
  'DifficultyLevel'
)
ORDER BY typname;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'User',
    'Lesson',
    'LessonTrack',
    'LessonBlock',
    'Evidence',
    'StudentLesson'
  )
ORDER BY table_name;
```

Also verify the expected primary keys, indexes, and foreign keys. A table merely existing does not prove that the migration completed correctly.

```sql
SELECT
  tc.table_name,
  tc.constraint_name,
  tc.constraint_type
FROM information_schema.table_constraints AS tc
WHERE tc.table_schema = 'public'
  AND tc.table_name IN (
    'User',
    'Lesson',
    'LessonTrack',
    'LessonBlock',
    'Evidence',
    'StudentLesson'
  )
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;
```

## 4. Choose the recovery based on evidence

### A. The entire migration is already represented correctly

Only after every expected enum, table, column, index, primary key, and foreign key is verified:

```sh
prisma migrate resolve \
  --applied 20260327192741_init_8_track_schema \
  --schema /app/prisma/schema.prisma
```

Then run:

```sh
prisma migrate deploy --schema /app/prisma/schema.prisma
```

### B. The migration was partially applied

Do not mark it applied.

1. Identify exactly which statements succeeded and failed.
2. Write a reviewed, idempotent repair SQL script for only the missing or incorrect objects.
3. Apply the repair inside a controlled maintenance window.
4. Verify the complete expected schema.
5. Mark the migration applied.
6. Run `prisma migrate deploy`.

### C. The migration did not apply and no objects exist

Mark the failed migration rolled back:

```sh
prisma migrate resolve \
  --rolled-back 20260327192741_init_8_track_schema \
  --schema /app/prisma/schema.prisma
```

Then run `prisma migrate deploy`. Do this only when the inspection proves there is no partially created state.

## 5. Verify application data after recovery

Read-only verification should confirm:

- existing student username/PIN login still works
- existing `User` IDs are unchanged
- canonical lesson counts are unchanged
- conversation and journal tables retain their row counts
- transcript and standards mastery row counts are unchanged
- `prisma migrate deploy` exits successfully on two consecutive runs
- Railway health check remains green

## 6. Fix startup behavior separately

After the database is repaired, change `entrypoint.sh` so that it:

- runs `prisma migrate deploy`
- fails the deployment when a migration fails
- never guesses which migration to mark applied
- never mutates migration history automatically

Migration resolution is an audited maintenance operation, not a normal container-startup fallback.

## Journal/sketchnote dependency

Do not add a new journal/sketchnote migration until this recovery is complete. Once migration history is healthy, add the new table through a normal reviewed Prisma migration using the current student ID as the ownership key. Do not create it at runtime with SQLAlchemy `create_all`.
