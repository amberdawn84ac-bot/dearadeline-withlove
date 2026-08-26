"""
Nightly self-seeding for tracks with thin Hippocampus coverage, plus ongoing
primary-source acquisition for TRUTH_HISTORY and JUSTICE_CHANGEMAKING.

Runs targeted queries against the Researcher tool (`search_witnesses`), which
searches Hippocampus first, then falls back to a free DuckDuckGo site-scoped
search of each track's approved primary-source domains (NARA, Library of
Congress, CourtListener, etc. — see `TRACK_DOMAINS` in researcher.py) when
nothing is already indexed. No external API key required. Results are
embedded and persisted to pgvector automatically, gated by the same
track-aware Witness Protocol threshold used at request time.

This replaces the old Tavily-only seed_declassified_documents.py /
seed_justice_changemaking.py scripts, which called the Tavily API directly
and had been silently failing since no TAVILY_API_KEY was ever set.

This grows the corpus ~5-10 documents per track per night.
"""
import logging
import random

logger = logging.getLogger(__name__)

# Seed queries — each triggers a web search + embed + persist cycle
SEED_QUERIES = {
    "GOVERNMENT_ECONOMICS": [
        "how does the Federal Reserve control money supply",
        "regulatory capture definition examples history",
        "what is a fiat currency and how does it lose value",
        "how do lobbyists influence legislation",
        "state vs federal government powers 10th amendment",
        "property taxes how they are calculated and used",
        "what is eminent domain and when has it been abused",
        "history of the gold standard in America",
        "how does inflation affect families and savings",
        "what is fractional reserve banking explained simply",
        "supply and demand real world examples for students",
        "how does a family budget work with irregular income",
        "what are tariffs and how do they affect consumers",
        "history of income tax in the United States",
        "how do credit unions differ from banks",
    ],
    "APPLIED_MATHEMATICS": [
        "how to calculate area of a garden plot for planting",
        "compound interest explained with savings examples",
        "measuring lumber board feet for building projects",
        "how to read a land survey and calculate acreage",
        "ratios and proportions in cooking and baking",
        "how to calculate crop yield per acre",
        "budgeting math for a small farm business",
        "geometry in carpentry and woodworking joints",
        "statistics in weather forecasting for farming",
        "how to calculate fabric needed for sewing projects",
        "figuring profit margin for a craft business",
        "measurement conversions for homesteading recipes",
        "how does mortgage amortization math work",
        "basic accounting for a market stand business",
        "how to estimate materials for a building project",
    ],
    "CREATIVE_ECONOMY": [
        "pricing handmade goods for craft fairs",
        "history of cottage industries in America",
        "how to start a small business as a teenager",
        "branding and storytelling for artisan products",
        "how Etsy makers price their products profitably",
        "the economics of farmers market vendors",
        "apprenticeship traditions in skilled trades",
        "how to photograph products for online selling",
        "arts and crafts movement William Morris philosophy",
        "how quilting bees built community and economy",
        "candle making soap making as cottage industry",
        "how to write product descriptions that sell",
        "pottery and ceramics as a sustainable business",
        "woodworking as a trade history and economics",
        "how to calculate cost of goods sold for handmade items",
    ],
    "TRUTH_HISTORY": [
        "declassified CIA documents Cold War overview",
        "FBI COINTELPRO surveillance of civil rights movement",
        "Pentagon Papers Vietnam War decision making",
        "National Archives records of the Civil War",
        "declassified Cuban Missile Crisis documents",
        "presidential decision records Eisenhower Cold War",
        "primary source documents the Great Depression",
        "National Archives immigration records Ellis Island",
        "declassified records Manhattan Project",
        "Congressional Record debates over the New Deal",
        "primary sources Reconstruction era after the Civil War",
        "National Archives Homestead Act records",
        "declassified State Department cables historical",
        "primary source letters and diaries World War II homefront",
        "Library of Congress civil rights era oral histories",
    ],
    "JUSTICE_CHANGEMAKING": [
        "lobbying disclosure records how influence is tracked",
        "campaign finance history and reform legislation",
        "landmark Supreme Court civil rights opinions",
        "legislative history of the Civil Rights Act",
        "corporate accountability investigative journalism history",
        "whistleblower protections history and law",
        "history of labor union organizing and legislation",
        "voting rights legislation history United States",
        "history of antitrust law and monopoly regulation",
        "court opinions on freedom of the press",
        "history of the Freedom of Information Act",
        "investigative reporting that changed public policy",
        "history of consumer protection regulation",
        "legislative history of environmental protection law",
        "how congressional oversight hearings work",
    ],
}


async def seed_thin_tracks():
    """Run 3 random queries per seeded track through the Researcher."""
    try:
        from app.tools.researcher import search_witnesses
    except ImportError:
        logger.error("[SeedThinTracks] Could not import search_witnesses")
        return

    total_acquired = 0

    for track, queries in SEED_QUERIES.items():
        # Pick 3 random queries to avoid always hitting the same ones
        selected = random.sample(queries, min(3, len(queries)))

        for query in selected:
            try:
                results = await search_witnesses(query=query, track=track)
                acquired = len(results)
                total_acquired += acquired
                if acquired:
                    logger.info(f"[SeedThinTracks] {track}: +{acquired} docs for '{query[:50]}'")
            except Exception as e:
                logger.warning(f"[SeedThinTracks] {track} query failed: {e}")

    logger.info(f"[SeedThinTracks] Nightly run complete: {total_acquired} new documents acquired")
