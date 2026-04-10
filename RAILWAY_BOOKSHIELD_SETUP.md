# Railway Bookshelf Setup Guide

## Quick Setup (One-Click)

Once deployed, you can populate the bookshelf database with a single API call:

### 1. Get Admin Auth Token
First, authenticate as an admin user to get a JWT token:
```bash
# Replace with your actual admin login
curl -X POST https://your-railway-app.railway.app/brain/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "your-password"}'
```

Extract the `token` from the response.

### 2. Run One-Click Setup
```bash
curl -X POST https://your-railway-app.railway.app/brain/api/admin/tasks/setup-bookshelf \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

This will return:
```json
{
  "success": true,
  "message": "Bookshelf setup started. This will run migrations and seed the database.",
  "task_id": "uuid-here"
}
```

### 3. Check Progress
```bash
curl -X GET https://your-railway-app.railway.app/brain/api/admin/tasks/task/YOUR_TASK_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Verify Setup
Once completed, check the health endpoint:
```bash
curl https://your-railway-app.railway.app/brain/health
```

Look for `"books": > 0` in the response.

## Manual Setup (Alternative)

If you prefer to run steps manually:

### 1. Run Migrations
```bash
curl -X POST https://your-railway-app.railway.app/brain/api/admin/tasks/seed-bookshelf \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

### 2. Check Database
```bash
curl https://your-railway-app.railway.app/brain/health
```

## What the Setup Does

1. **Database Migrations**: Creates/updates all necessary tables including:
   - `Book` table with pgvector support
   - `ReadingRecommendationsLog` for registrar tracking
   - `ReadingSession` for progress tracking

2. **Book Seeding**: Fetches and processes books from:
   - Standard Ebooks API
   - Project Gutenberg API
   - Generates embeddings via OpenAI
   - Assigns curriculum tracks and reading levels
   - Populates searchable book catalog

3. **Verification**: Confirms books are properly indexed and searchable

## Environment Variables Required

Make sure these are set in Railway:
- `OPENAI_API_KEY` - For generating embeddings
- `DATABASE_URL` - PostgreSQL connection
- `ANTHROPIC_API_KEY` - For curriculum track assignment

## Troubleshooting

### Task Failed
Check the task status for error details:
```bash
curl -X GET https://your-railway-app.railway.app/brain/api/admin/tasks/task/TASK_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### No Books After Setup
1. Check health endpoint for book count
2. Verify `OPENAI_API_KEY` is valid
3. Check Railway logs for seed script errors

### Recommendations Still Empty
1. Verify Book table is populated (`/health` endpoint)
2. Check student profile has grade level
3. Test recommendations endpoint directly

## Expected Timeline

- **Migrations**: 1-2 minutes
- **Book Seeding**: 10-30 minutes (depends on API rate limits)
- **Total Setup**: 15-45 minutes

The setup process is designed to run safely in the background and can be retried if it fails.
