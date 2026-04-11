"""
Seed Hippocampus with science experiment content from curated educational sites.

Sources:
- weareteachers.com/easy-science-experiments/
- stevespanglerscience.com
- sciencebuddies.org
- pbslearningmedia.org

Tracks: CREATION_SCIENCE, HOMESTEADING

Run from adeline-brain/:
    python scripts/seed_science_experiments.py
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
log = logging.getLogger("science-seed")

EXPERIMENT_QUERIES = [
    # We Are Teachers
    ("easy science experiments kids home site:weareteachers.com", "CREATION_SCIENCE", "weareteachers.com"),
    ("biology science experiments elementary site:weareteachers.com", "CREATION_SCIENCE", "weareteachers.com"),
    ("chemistry kitchen experiments site:weareteachers.com", "CREATION_SCIENCE", "weareteachers.com"),
    ("plant science experiments garden site:weareteachers.com", "HOMESTEADING", "weareteachers.com"),
    ("weather earth science experiments site:weareteachers.com", "CREATION_SCIENCE", "weareteachers.com"),

    # Steve Spangler Science
    ("hands-on science experiment instructions site:stevespanglerscience.com", "CREATION_SCIENCE", "stevespanglerscience.com"),
    ("baking soda vinegar chemistry experiment site:stevespanglerscience.com", "CREATION_SCIENCE", "stevespanglerscience.com"),
    ("density experiment kitchen science site:stevespanglerscience.com", "CREATION_SCIENCE", "stevespanglerscience.com"),

    # Science Buddies
    ("biology experiment procedure hypothesis site:sciencebuddies.org", "CREATION_SCIENCE", "sciencebuddies.org"),
    ("plant growth experiment variables site:sciencebuddies.org", "HOMESTEADING", "sciencebuddies.org"),
    ("soil science experiment site:sciencebuddies.org", "HOMESTEADING", "sciencebuddies.org"),
    ("physics forces motion experiment site:sciencebuddies.org", "CREATION_SCIENCE", "sciencebuddies.org"),
    ("ecology environment experiment site:sciencebuddies.org", "CREATION_SCIENCE", "sciencebuddies.org"),

    # PBS Learning Media
    ("science experiment activity guide site:pbslearningmedia.org", "CREATION_SCIENCE", "pbslearningmedia.org"),
    ("nature science investigation outdoor site:pbslearningmedia.org", "HOMESTEADING", "pbslearningmedia.org"),
]


async def seed_query(query: str, track: str, domain: str, tavily_key: str) -> int:
    import httpx
    from openai import AsyncOpenAI
    from app.connections.pgvector_client import hippocampus

    log.info(f"Searching [{track}]: {query[:60]}...")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "include_domains": [domain],
                    "max_results": 3,
                    "search_depth": "basic",
                },
            )
            if resp.status_code != 200:
                log.warning(f"  Tavily {resp.status_code}")
                return 0
            results = resp.json().get("results", [])
    except Exception as e:
        log.warning(f"  Search error: {e}")
        return 0

    if not results:
        return 0

    oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    seeded = 0

    for result in results:
        content = result.get("content", "")
        if len(content) < 100:
            continue
        url = result.get("url", "")
        title = result.get("title", "")

        try:
            embed_resp = await oai.embeddings.create(
                model="text-embedding-3-small",
                input=content[:8000],
            )
            embedding = embed_resp.data[0].embedding

            doc_id = await hippocampus.upsert_document(
                source_title=title,
                track=track,
                chunk=content,
                embedding=embedding,
                source_url=url,
                source_type="EDUCATIONAL",
                citation_author=domain,
                citation_year=None,
                citation_archive_name=domain,
            )
            log.info(f"  Cached: {title[:55]} ({doc_id[:8]}...)")
            seeded += 1
        except Exception as e:
            log.warning(f"  Failed to cache {url}: {e}")

    return seeded


async def main():
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        log.error("TAVILY_API_KEY not set")
        return
    if not os.getenv("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY not set")
        return

    from app.connections.pgvector_client import hippocampus
    await hippocampus.connect()

    log.info("=" * 60)
    log.info("  Seeding science experiments to Hippocampus")
    log.info("=" * 60)

    total = 0
    for query, track, domain in EXPERIMENT_QUERIES:
        count = await seed_query(query, track, domain, tavily_key)
        total += count
        await asyncio.sleep(1.0)

    log.info("=" * 60)
    log.info(f"  Done: {total} experiment documents seeded")
    log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
