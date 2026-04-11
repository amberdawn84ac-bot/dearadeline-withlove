"""
Seed Hippocampus with Baker Creek Seeds growing guides and seed stories.

Baker Creek Heirloom Seeds (rareseeds.com) — a family seed company that
gave us free seeds. Their growing guides and seed stories are primary
sources for HOMESTEADING lessons.

Fetches content via Tavily web search and seeds into Hippocampus.

Run from adeline-brain/:
    python scripts/seed_baker_creek.py
"""
import asyncio
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("baker-creek-seed")

BAKER_CREEK_QUERIES = [
    # Growing guides
    "heirloom tomato growing guide site:rareseeds.com",
    "seed starting indoors guide site:rareseeds.com",
    "companion planting guide site:rareseeds.com",
    "winter squash growing guide site:rareseeds.com",
    "bean varieties growing guide site:rareseeds.com",
    "corn growing guide heirloom site:rareseeds.com",
    "pepper growing guide site:rareseeds.com",
    "root vegetable growing guide site:rareseeds.com",
    "herb growing guide site:rareseeds.com",
    "saving seeds guide site:rareseeds.com",
    # Seed stories
    "seed story heritage variety site:rareseeds.com",
    "heirloom seed history site:rareseeds.com",
    "Cherokee Trail of Tears bean site:rareseeds.com",
    "family farm seed preservation site:rareseeds.com",
]

# Mountain Rose Herbs — herb profiles, remedies, wildcrafting, growing
# Perfect for HEALTH_NATUROPATHY + HOMESTEADING crossover
MOUNTAIN_ROSE_QUERIES = [
    "herb profile medicinal uses site:mountainroseherbs.com",
    "growing herbs at home site:mountainroseherbs.com",
    "herbal remedy preparation site:mountainroseherbs.com",
    "wildcrafting foraging herbs site:mountainroseherbs.com",
    "elderberry echinacea immune herbs site:mountainroseherbs.com",
    "lavender chamomile calming herbs site:mountainroseherbs.com",
    "tincture infusion herbal preparation site:mountainroseherbs.com",
    "adaptogen herbs stress site:mountainroseherbs.com",
    "culinary herbs kitchen garden site:mountainroseherbs.com",
    "sustainable herb farming site:mountainroseherbs.com",
]

# Track assignment for Mountain Rose content — bridges HOMESTEADING + HEALTH_NATUROPATHY
MOUNTAIN_ROSE_TRACK = "HEALTH_NATUROPATHY"

# GotQuestions.org — Christian worldview Q&A, biblical theology, scripture explanations
GOT_QUESTIONS_QUERIES = [
    "what does the Bible say about site:gotquestions.org",
    "biblical worldview Christian faith site:gotquestions.org",
    "what is the meaning of site:gotquestions.org",
    "Old Testament New Testament connection site:gotquestions.org",
    "prayer scripture study site:gotquestions.org",
    "Christian stewardship creation care site:gotquestions.org",
    "biblical justice mercy site:gotquestions.org",
    "discernment wisdom scripture site:gotquestions.org",
]


async def seed_query(query: str, tavily_key: str, track: str = "HOMESTEADING", domain: str = "rareseeds.com", citation: str = "Baker Creek Heirloom Seeds") -> int:
    """Search Tavily and seed results to Hippocampus. Returns count seeded."""
    import httpx
    from openai import AsyncOpenAI

    log.info(f"Searching: {query}")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "include_domains": [domain],
                    "max_results": 3,
                    "search_depth": "advanced",
                },
            )
            if resp.status_code != 200:
                log.warning(f"Tavily returned {resp.status_code} for: {query}")
                return 0

            results = resp.json().get("results", [])
    except Exception as e:
        log.warning(f"Tavily error: {e}")
        return 0

    if not results:
        log.info("  No results found")
        return 0

    oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    from app.connections.pgvector_client import hippocampus

    seeded = 0
    for result in results:
        title = result.get("title", "")
        url = result.get("url", "")
        content = result.get("content", "")

        if not content or len(content) < 100:
            continue

        try:
            resp = await oai.embeddings.create(
                model="text-embedding-3-small",
                input=content[:8000],
            )
            embedding = resp.data[0].embedding

            doc_id = await hippocampus.upsert_document(
                source_title=f"{title} ({citation})",
                track=track,
                chunk=content,
                embedding=embedding,
                source_url=url,
                source_type="EDUCATIONAL",
                citation_author=citation,
                citation_year=None,
                citation_archive_name=domain,
            )
            log.info(f"  Cached: {title[:60]} ({doc_id[:8]}...)")
            seeded += 1
        except Exception as e:
            log.warning(f"  Failed to cache {url}: {e}")

    return seeded


async def main():
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        log.error("TAVILY_API_KEY not set — cannot search Baker Creek")
        return

    if not os.getenv("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY not set — cannot generate embeddings")
        return

    from app.connections.pgvector_client import hippocampus
    await hippocampus.connect()

    log.info("=" * 60)
    log.info("  Seeding Baker Creek + Mountain Rose Herbs to Hippocampus")
    log.info("=" * 60)

    total = 0

    log.info("-- Baker Creek Seeds (HOMESTEADING) --")
    for query in BAKER_CREEK_QUERIES:
        count = await seed_query(query, tavily_key, track="HOMESTEADING", domain="rareseeds.com", citation="Baker Creek Heirloom Seeds")
        total += count
        await asyncio.sleep(1.0)

    log.info("-- Mountain Rose Herbs (HEALTH_NATUROPATHY) --")
    for query in MOUNTAIN_ROSE_QUERIES:
        count = await seed_query(query, tavily_key, track=MOUNTAIN_ROSE_TRACK, domain="mountainroseherbs.com", citation="Mountain Rose Herbs")
        total += count
        await asyncio.sleep(1.0)

    log.info("-- GotQuestions.org (DISCIPLESHIP) --")
    for query in GOT_QUESTIONS_QUERIES:
        count = await seed_query(query, tavily_key, track="DISCIPLESHIP", domain="gotquestions.org", citation="GotQuestions.org")
        total += count
        await asyncio.sleep(1.0)

    log.info("=" * 60)
    log.info(f"  Done: {total} documents seeded")
    log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
