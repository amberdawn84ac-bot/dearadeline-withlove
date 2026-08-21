# Production scale runbook

Dear Adeline is designed to scale horizontally: Vercel serves the Next.js UI,
Railway replicas serve the FastAPI Brain, PostgreSQL owns durable educational
records, Redis coordinates caches and limits, and Supabase Storage keeps child
evidence private.

## Required production configuration

- `ADELINE_ENV=production`
- `DATABASE_URL` or `POSTGRES_DSN` (use the transaction-pooler URL)
- `STUDENT_JWT_SECRET` (a dedicated random secret)
- `INTERNAL_API_KEY` (a dedicated random secret)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and Supabase auth settings
- `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`, or `REDIS_URL`
- `GEMINI_API_KEY` (and `OPENAI_API_KEY` for embeddings where used)
- `SENTRY_DSN`
- production `CORS_ORIGINS`

Database transport is always TLS. Set `DB_SSL_ROOT_CERT` to a mounted provider
CA bundle to additionally enforce certificate and hostname verification.

## Capacity controls

- `DB_POOL_MIN_SIZE=1`, `DB_POOL_MAX_SIZE=10` per worker by default
- `AI_MAX_CONCURRENCY=20` per worker
- `EVIDENCE_UPLOAD_CONCURRENCY=4` per worker
- `WEB_CONCURRENCY=1` by default; prefer additional Railway replicas before
  increasing workers on memory-constrained containers
- resource searches cache for one hour; learning plans retain their existing
  five-minute adaptive cache
- expensive actions use Redis-backed per-account limits shared by all replicas

Start with two Railway replicas for production availability. Increase replicas
when sustained CPU exceeds 65%, p95 application latency exceeds 1.5 seconds
outside model-streaming routes, or AI queue saturation appears in logs. Keep
`replicas × workers × DB_POOL_MAX_SIZE` within the database pooler's connection
budget.

## Release gate

1. Migrations complete successfully before the server starts.
2. `/health/ready` returns 200; `/health` is liveness only.
3. Vercel production build and Railway deployment are both healthy.
4. Verify student sign-in, parent-to-child access, blocked cross-household
   access, chat streaming, resource routing, activity credit, private evidence,
   learning-plan refresh, and Daily Bread.
5. Confirm request IDs, latency, errors, and model failures reach logs/Sentry.

Database backups and point-in-time recovery must be enabled at the provider.
Test restoration quarterly; a backup that has never been restored is not a
verified backup.
