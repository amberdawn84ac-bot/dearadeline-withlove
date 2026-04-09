"""
Nightly self-seeding for tracks with thin Hippocampus coverage.

Runs targeted queries against the Researcher tool for GOVERNMENT_ECONOMICS,
APPLIED_MATHEMATICS, and CREATIVE_ECONOMY. When Hippocampus returns nothing,
the Researcher auto-acquires from Tavily and persists to pgvector.

This grows the corpus ~5-10 documents per track per night.
"""
import logging
import random

logger = logging.getLogger(__name__)

# Seed queries — each triggers a Tavily search + embed + persist cycle
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
}


async def seed_thin_tracks():
    """Run 3 random queries per thin track through the Researcher."""
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
