# Railway Environment Variables Setup

## Critical Issue: Web Search Not Working

**Problem**: Queries like "Civil War" return silent/no content instead of triggering web search and auto-seeding.

**Root Cause**: `TAVILY_API_KEY` is not set in Railway production environment.

## Required Environment Variables for Railway

### Core API Keys (Required)
```bash
OPENAI_API_KEY=sk-proj-...           # OpenAI for embeddings and LLM
ANTHROPIC_API_KEY=sk-ant-api03-...   # Claude for content synthesis
TAVILY_API_KEY=tvly-dev-...          # ⚠️ CRITICAL - Web search for auto-seeding
```

### Database (Required)
```bash
DATABASE_URL=postgresql://...         # PostgreSQL connection string
POSTGRES_DSN=postgresql://...         # Same as DATABASE_URL (legacy)
NEO4J_URI=neo4j+s://...              # Neo4j Aura connection
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
```

### Optional (Recommended)
```bash
ADELINE_MODEL=claude-sonnet-4-6      # Claude model to use
CORS_ORIGINS=https://your-frontend.vercel.app
```

## How to Add TAVILY_API_KEY to Railway

1. **Get your Tavily API key** from https://tavily.com (free tier available)
2. **Go to Railway dashboard** → Select your `adeline-brain` service
3. **Click "Variables" tab**
4. **Add new variable**:
   - Name: `TAVILY_API_KEY`
   - Value: `tvly-dev-...` (your actual key)
5. **Click "Deploy"** to restart with new environment variable

## What Happens Without TAVILY_API_KEY

### Current Behavior (Broken)
```
Student: "Tell me about the Civil War"
↓
Hippocampus search (empty - not seeded yet)
↓
Researcher fallback triggered
↓
TAVILY_API_KEY missing → Web search skipped
↓
Returns empty → RESEARCH_MISSION block created
↓
Frontend shows: (silent/no content)
```

### Expected Behavior (With Tavily)
```
Student: "Tell me about the Civil War"
↓
Hippocampus search (empty)
↓
Researcher fallback triggered
↓
Tavily searches 6 declassified archives:
  - NARA (catalog.archives.gov)
  - CIA FOIA (cia.gov/information-freedom)
  - FBI Vault (vault.fbi.gov)
  - Congressional Record (congress.gov)
  - Federal Register (federalregister.gov)
  - DNSA (nsarchive.gwu.edu)
↓
Finds relevant documents
↓
Embeds and scores (≥0.82 threshold)
↓
Auto-seeds to Hippocampus
↓
Returns PRIMARY_SOURCE block with content
↓
Frontend shows: Rich historical content
```

## Researcher Flow (search_witnesses)

1. **Embed query** using OpenAI text-embedding-3-small
2. **Search Hippocampus** for existing verified sources (≥0.82 similarity)
3. **If found**: Return verified sources
4. **If empty**: Trigger deep web search via Tavily
5. **Parallel search** across 6 declassified archives
6. **Embed results** and score against query
7. **Auto-seed** documents with ≥0.82 similarity to Hippocampus
8. **Return** newly acquired sources
9. **If still empty**: Return empty (triggers RESEARCH_MISSION block)

## Logging to Check

After adding TAVILY_API_KEY, check Railway logs for:

### Success Indicators
```
[Researcher] Searching for witnesses — query='Civil War' track=TRUTH_HISTORY
[Researcher] Hippocampus empty. Triggering deep web search.
[Researcher] Acquired document: [Title] from NARA
[Researcher] Acquired 3 documents from deep web search after age filtering
```

### Failure Indicators (Missing Key)
```
[Researcher] TAVILY_API_KEY not set — deep web search will be disabled
[Researcher] TAVILY_API_KEY not set in environment — cannot search NARA
[Researcher] No results from deep web search either.
[Researcher] No results from any source. Student gets RESEARCH_MISSION.
```

## Testing After Setup

1. **Add TAVILY_API_KEY** to Railway
2. **Wait for deployment** to complete (~2-3 minutes)
3. **Test query**: "Tell me about the Civil War"
4. **Expected result**: Should return historical content from NARA or other archives
5. **Check logs**: Should see "Acquired document" messages

## Tavily Rate Limits

- **Free tier**: 1000 requests/month
- **Rate limiter**: Built-in TokenBucket (10 tokens max, 0.5/sec refill)
- **Per-archive limit**: 3 results max per search
- **Total archives**: 6 (max 18 results per query)

## Alternative: Manual Seeding

If you don't want to use Tavily, you can manually seed content:

```bash
# SSH into Railway container
railway run bash

# Run seed scripts
python scripts/seed_curriculum.py
python scripts/seed_knowledge_graph.py

# Or use the admin endpoint
curl -X POST https://your-brain.railway.app/admin/seed
```

But this requires pre-existing content and won't auto-discover new sources.

## Summary

**To fix "Civil War" silent issue**:
1. Add `TAVILY_API_KEY` to Railway environment variables
2. Redeploy
3. Test query
4. Check logs for "Acquired document" messages

**Current local key** (from `.env`):
```
TAVILY_API_KEY=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
```

Use this same key in Railway, or get a new one from https://tavily.com
