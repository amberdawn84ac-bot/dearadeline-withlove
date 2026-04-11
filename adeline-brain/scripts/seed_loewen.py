"""
Seed Hippocampus with content from / about 'Lies My Teacher Told Me'
by James W. Loewen.

We cannot copy copyrighted text, so we:
1. Seed the documented historical corrections Loewen makes (factual claims,
   publicly documented in reviews, interviews, and academic analysis)
2. Search for freely available academic discussions and reviews via Tavily
3. Seed Loewen's key theses as reference chunks so Adeline can cite the book

Track: TRUTH_HISTORY and JUSTICE_CHANGEMAKING

Run from adeline-brain/:
    python scripts/seed_loewen.py
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
log = logging.getLogger("loewen-seed")

# Key documented corrections from Loewen — publicly cited factual claims.
# These are his documented arguments, not quoted text.
LOEWEN_REFERENCE_CHUNKS = [
    {
        "title": "Lies My Teacher Told Me — Helen Keller's Radicalism",
        "track": "TRUTH_HISTORY",
        "content": (
            "James W. Loewen, in 'Lies My Teacher Told Me' (1995, 2007), documents that "
            "Helen Keller was a committed socialist and radical activist whose political views "
            "are almost entirely omitted from standard American textbooks. Keller supported "
            "the Industrial Workers of the World (IWW), opposed US entry into World War I, "
            "and wrote extensively about how poverty and industrialism — not just individual "
            "misfortune — caused disability. Loewen argues textbooks reduce her to an "
            "inspirational figure, erasing her as a political thinker."
        ),
    },
    {
        "title": "Lies My Teacher Told Me — Woodrow Wilson's Racism",
        "track": "TRUTH_HISTORY",
        "content": (
            "Loewen documents that Woodrow Wilson, celebrated in textbooks as a progressive "
            "idealist, was one of the most openly racist presidents in American history. "
            "Wilson resegregated the federal civil service, personally screened and rejected "
            "Black applicants from federal positions, and screened 'Birth of a Nation' — a "
            "KKK propaganda film — at the White House. Loewen argues this omission protects "
            "a myth of progressive presidential history that erases Black Americans' experience."
        ),
    },
    {
        "title": "Lies My Teacher Told Me — Columbus and the Taino",
        "track": "TRUTH_HISTORY",
        "content": (
            "Loewen documents that Christopher Columbus initiated the enslavement and "
            "systematic killing of the Taino people of Hispaniola. Columbus's own journals "
            "(held in the Archivo General de Indias, Seville) record his orders to take "
            "Taino people by force. Within 50 years of Columbus's arrival, the Taino "
            "population collapsed from an estimated 300,000 to near extinction. Standard "
            "textbooks, Loewen argues, celebrate Columbus without acknowledging this genocide."
        ),
    },
    {
        "title": "Lies My Teacher Told Me — The Truth About Thanksgiving",
        "track": "TRUTH_HISTORY",
        "content": (
            "Loewen documents that the 'Thanksgiving' narrative taught in American schools "
            "is largely invented. The 1621 harvest gathering at Plymouth was not called "
            "Thanksgiving by the Pilgrims, and the Wampanoag people who attended had their "
            "own complex reasons for alliance with the English settlers — reasons rooted in "
            "intertribal politics after a devastating epidemic had killed 90% of coastal "
            "New England Native populations. The romanticized 'first Thanksgiving' story "
            "was largely constructed in the 19th century."
        ),
    },
    {
        "title": "Lies My Teacher Told Me — Reconstruction's Erasure",
        "track": "TRUTH_HISTORY",
        "content": (
            "Loewen documents that American textbooks consistently misrepresent "
            "Reconstruction (1865-1877) as a failure caused by Black incompetence and "
            "Northern overreach. Primary sources — including Congressional records, "
            "newspaper accounts, and freedmen's bureau documents — show Reconstruction "
            "governments were among the most democratic in Southern history, establishing "
            "public schools and civil rights. Their destruction was achieved through "
            "organized terrorist violence by groups like the Ku Klux Klan, Red Shirts, "
            "and White League, not through political failure."
        ),
    },
    {
        "title": "Lies My Teacher Told Me — The Myth of Lincoln the Liberator",
        "track": "TRUTH_HISTORY",
        "content": (
            "Loewen documents the complexity of Abraham Lincoln's views on race that "
            "textbooks flatten into a simple 'Great Emancipator' narrative. Lincoln's own "
            "words — including his 1858 debate statements expressing belief in white "
            "superiority — show a man whose views evolved under political pressure and "
            "wartime necessity. The Emancipation Proclamation freed enslaved people only "
            "in Confederate states, not in Union slave states. Loewen argues honest "
            "history requires holding this complexity rather than mythologizing Lincoln."
        ),
    },
    {
        "title": "Lies My Teacher Told Me — The Agent Orange Cover-Up",
        "track": "JUSTICE_CHANGEMAKING",
        "content": (
            "Loewen documents that US government and military officials knowingly used "
            "Agent Orange in Vietnam despite internal evidence of its toxicity to humans. "
            "The Veterans Administration initially denied health claims from American "
            "veterans for decades. Vietnamese civilian casualties from Agent Orange — "
            "estimated in the millions with multigenerational birth defects — receive "
            "almost no attention in standard American history textbooks. Loewen uses this "
            "as an example of how textbooks protect government credibility over truth."
        ),
    },
    {
        "title": "Lies My Teacher Told Me — Loewen's Core Thesis on Heroification",
        "track": "TRUTH_HISTORY",
        "content": (
            "James Loewen's central argument in 'Lies My Teacher Told Me' is that American "
            "history textbooks engage in 'heroification' — turning complex historical "
            "figures into perfect icons, stripping away anything that complicates the "
            "national mythology. This process, Loewen argues, produces students who cannot "
            "think critically about their society because they have been given myths instead "
            "of history. The antidote is primary source investigation: what did the person "
            "actually say, write, and do? Who was harmed? Who benefited? Whose account "
            "was recorded and whose was silenced?"
        ),
    },
]

# Web searches for freely available academic analysis and interviews
LOEWEN_WEB_QUERIES = [
    "James Loewen Lies My Teacher Told Me historical analysis",
    "Loewen heroification American history textbooks critique",
    "Loewen American history myths Columbus Thanksgiving criticism",
]


async def seed_reference_chunks() -> int:
    """Seed the documented Loewen reference chunks directly."""
    from openai import AsyncOpenAI
    from app.connections.pgvector_client import hippocampus

    oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    seeded = 0

    for chunk in LOEWEN_REFERENCE_CHUNKS:
        try:
            resp = await oai.embeddings.create(
                model="text-embedding-3-small",
                input=chunk["content"],
            )
            embedding = resp.data[0].embedding

            doc_id = await hippocampus.upsert_document(
                source_title=chunk["title"],
                track=chunk["track"],
                chunk=chunk["content"],
                embedding=embedding,
                source_url="https://www.simonandschuster.com/books/Lies-My-Teacher-Told-Me/James-W-Loewen/9781620974018",
                source_type="EDUCATIONAL",
                citation_author="James W. Loewen",
                citation_year=2007,
                citation_archive_name="Lies My Teacher Told Me (Touchstone, 2007)",
            )
            log.info(f"Cached: {chunk['title'][:60]} ({doc_id[:8]}...)")
            seeded += 1
        except Exception as e:
            log.warning(f"Failed: {chunk['title'][:40]}: {e}")

    return seeded


async def seed_web_analysis(tavily_key: str) -> int:
    """Search for freely available academic analysis."""
    import httpx
    from openai import AsyncOpenAI
    from app.connections.pgvector_client import hippocampus

    oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    seeded = 0

    for query in LOEWEN_WEB_QUERIES:
        log.info(f"Searching: {query}")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": query,
                        "max_results": 3,
                        "search_depth": "basic",
                    },
                )
                if resp.status_code != 200:
                    continue
                results = resp.json().get("results", [])

            for result in results:
                content = result.get("content", "")
                if len(content) < 100:
                    continue
                url = result.get("url", "")
                title = result.get("title", "")

                embed_resp = await oai.embeddings.create(
                    model="text-embedding-3-small",
                    input=content[:8000],
                )
                embedding = embed_resp.data[0].embedding

                doc_id = await hippocampus.upsert_document(
                    source_title=f"{title} (re: Loewen)",
                    track="TRUTH_HISTORY",
                    chunk=content,
                    embedding=embedding,
                    source_url=url,
                    source_type="EDUCATIONAL",
                    citation_author="James W. Loewen (analysis)",
                    citation_year=None,
                    citation_archive_name="Lies My Teacher Told Me",
                )
                log.info(f"Cached: {title[:60]} ({doc_id[:8]}...)")
                seeded += 1

        except Exception as e:
            log.warning(f"Web search failed for '{query}': {e}")

        await asyncio.sleep(1.0)

    return seeded


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY not set")
        return

    from app.connections.pgvector_client import hippocampus
    await hippocampus.connect()

    log.info("=" * 60)
    log.info("  Seeding Lies My Teacher Told Me — Loewen")
    log.info("=" * 60)

    total = await seed_reference_chunks()
    log.info(f"Reference chunks: {total} seeded")

    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        web_count = await seed_web_analysis(tavily_key)
        total += web_count
        log.info(f"Web analysis: {web_count} seeded")
    else:
        log.warning("TAVILY_API_KEY not set — skipping web analysis")

    log.info("=" * 60)
    log.info(f"  Done: {total} Loewen documents seeded")
    log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
