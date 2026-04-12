#!/usr/bin/env python3
"""
seed_nature_lost_vault.py — Seed curriculum from NatureLostVault.com

NatureLostVault covers:
  - Medicinal plants with clinical research citations
  - Forgotten survival foods and perennial crops
  - Traditional building techniques
  - Homesteading and self-sufficiency knowledge

Tracks: HEALTH_NATUROPATHY, HOMESTEADING, CREATION_SCIENCE

Run:  cd adeline-brain && python scripts/seed_nature_lost_vault.py
"""
import asyncio
import os
import ssl as _ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_pg_pw = os.getenv("POSTGRES_PASSWORD", "placeholder_password")
_pg_dsn = (
    os.getenv("POSTGRES_DSN")
    or os.getenv("DIRECT_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or f"postgresql://adeline:{_pg_pw}@localhost:5432/hippocampus"
).replace("postgresql://", "postgresql+asyncpg://")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBED_MODEL = "text-embedding-3-small"

import openai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


async def embed(text_input: str) -> list[float] | None:
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        resp = await client.embeddings.create(model=EMBED_MODEL, input=text_input)
        return resp.data[0].embedding
    except openai.BadRequestError as e:
        if "content_filter" in str(e).lower() or e.status_code == 400:
            print(f"  [SKIP] Content filter: '{text_input[:60]}...'")
            return None
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# NATURE LOST VAULT SOURCES
# High-quality medicinal plant profiles with clinical research citations
# ═══════════════════════════════════════════════════════════════════════════════

SOURCES = [
    # ─────────────────────────────────────────────────────────────────────────────
    # MEDICINAL PLANTS — HEALTH_NATUROPATHY
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Lemon Balm (Melissa officinalis) — The Deep Sleep Plant",
        "source_url": "https://naturelostvault.com/episodes/episode-89-lemon-balm.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Medicinal Plants",
        "chunk": (
            "Lemon balm (Melissa officinalis) has been used for 2,400 years. The Greeks named it "
            "melissa, their word for honey bee, because bees would never abandon a hive where it grew. "
            "Avicenna, the Persian physician who wrote The Canon of Medicine in 1025, prescribed it "
            "to 'cause the mind and heart to become merry.' Paracelsus called it the Elixir of Life.\n\n"
            "In 2007, researchers at the University of Ottawa tested ten plants for anxiety relief. "
            "Lemon balm was the strongest inhibitor of GABA transaminase — the enzyme that destroys "
            "your brain's primary calming neurotransmitter. The compound responsible is rosmarinic acid, "
            "which crosses the blood-brain barrier and raises GABA levels naturally without the "
            "addiction risk of benzodiazepines.\n\n"
            "A 2004 double-blind trial at Northumbria University showed anxiety scores dropped within "
            "one hour of a single dose, with improved memory recall and no sedation. The FDA placed "
            "lemon balm on the Generally Recognized As Safe list under 21 CFR Part 182."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Lemon Balm — Alzheimer's Research and Acetylcholinesterase",
        "source_url": "https://naturelostvault.com/episodes/episode-89-lemon-balm.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Medicinal Plants",
        "chunk": (
            "A 2010 Iranian clinical trial treated patients with moderate Alzheimer's disease using "
            "daily lemon balm tincture for four months. The treated group showed significantly less "
            "agitation, less wandering, and measurably better cognitive scores versus placebo.\n\n"
            "The mechanism is acetylcholinesterase inhibition — lemon balm blocks the enzyme that "
            "destroys acetylcholine in the brain. This is the exact same mechanism used by Aricept, "
            "the leading prescription Alzheimer's drug costing $300/month. Aricept cannot be grown "
            "in a pot. Lemon balm can.\n\n"
            "To prepare: harvest leaves before flowering, dry in shade, steep 1-2 teaspoons in hot "
            "water for 10 minutes. For tincture, fill a jar with fresh leaves, cover with vodka, "
            "steep 4-6 weeks, strain. Standard dose is 1-2 ml three times daily."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Boneset (Eupatorium perfoliatum) — The 1918 Flu Fighter",
        "source_url": "https://naturelostvault.com/episodes/episode-87-boneset.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Medicinal Plants",
        "chunk": (
            "Boneset (Eupatorium perfoliatum) was the primary treatment for influenza in America "
            "before aspirin. During the 1918 Spanish Flu pandemic, Eclectic physicians reported "
            "significantly lower mortality rates using boneset compared to conventional treatments.\n\n"
            "Modern research shows boneset contains sesquiterpene lactones that stimulate the immune "
            "system and have anti-inflammatory properties. A 2016 study found boneset extract "
            "prevented influenza virus from entering cells — a mechanism similar to Tamiflu.\n\n"
            "The plant grows wild in wet meadows and stream banks across eastern North America. "
            "The name comes from its historical use for 'break-bone fever' (dengue), where patients "
            "felt like their bones were breaking. Boneset tea relieved the deep aching."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Chaga Mushroom (Inonotus obliquus) — 1,600 Studies, Zero US Trials",
        "source_url": "https://naturelostvault.com/episodes/episode-90-chaga.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Medicinal Plants",
        "chunk": (
            "Chaga (Inonotus obliquus) is a fungus that grows on birch trees in cold climates. "
            "Soviet researchers used it to support cancer care for decades. Over 1,600 studies "
            "exist in the scientific literature, yet zero clinical trials have been conducted "
            "in the United States.\n\n"
            "Chaga contains betulinic acid (derived from birch bark), polysaccharides that "
            "modulate immune function, and one of the highest ORAC antioxidant scores of any "
            "natural substance. Traditional preparation involves simmering chunks in water for "
            "several hours to extract the water-soluble compounds.\n\n"
            "The fungus takes 15-20 years to mature and should be harvested sustainably, "
            "leaving at least 50% of the conk to allow regeneration. Overharvesting has "
            "depleted wild populations in some areas."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Perilla (Perilla frutescens) — Omega-3 in a Bucket",
        "source_url": "https://naturelostvault.com/episodes/episode-97-perilla.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Medicinal Plants",
        "chunk": (
            "Perilla (Perilla frutescens), also called shiso, contains the highest concentration "
            "of alpha-linolenic acid (ALA omega-3) of any leafy plant — up to 60% of seed oil. "
            "This is the same essential fatty acid found in fish oil and flaxseed.\n\n"
            "The plant is a vigorous self-seeder that grows as an annual in most climates. "
            "Plant once in spring, and it will return every year from dropped seeds. Both "
            "leaves and seeds are edible. The leaves are used fresh in Asian cuisine; the "
            "seeds can be pressed for oil or eaten whole.\n\n"
            "Perilla also contains rosmarinic acid (like lemon balm) and has been studied "
            "for anti-inflammatory and anti-allergic properties. In Japan, it's a common "
            "treatment for seasonal allergies."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # SURVIVAL FOODS — HOMESTEADING
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "track": "HOMESTEADING",
        "source_title": "American Persimmon — The Food of the Gods",
        "source_url": "https://naturelostvault.com/episodes/episode-92-persimmons.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Survival Foods",
        "chunk": (
            "American persimmon (Diospyros virginiana) — the genus name means 'food of the gods' — "
            "contains twice the antioxidants of blueberries and grows wild across the eastern "
            "United States. The fruit is astringent until fully ripe (soft and wrinkled), when "
            "it becomes intensely sweet with notes of apricot and brown sugar.\n\n"
            "Native Americans dried persimmons into cakes that stored for years. The seeds were "
            "roasted as a coffee substitute during the Civil War. The wood is extremely hard "
            "and was traditionally used for golf club heads and textile shuttles.\n\n"
            "Trees are dioecious (male and female separate), so plant multiple for fruit. They "
            "tolerate poor soil, drought, and neglect. A mature tree can produce 50-100 pounds "
            "of fruit annually with zero inputs."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "10 Weeds Worth More Than Your Vegetable Garden",
        "source_url": "https://naturelostvault.com/episodes/episode-101-10-weeds.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Survival Foods",
        "chunk": (
            "Many plants we call 'weeds' are more nutritious than cultivated vegetables:\n\n"
            "1. Lamb's Quarters (Chenopodium album) — more protein, calcium, and iron than spinach\n"
            "2. Purslane (Portulaca oleracea) — highest omega-3 content of any leafy green\n"
            "3. Dandelion (Taraxacum officinale) — entire plant edible, roots roast for coffee\n"
            "4. Plantain (Plantago major) — wound healing, edible young leaves\n"
            "5. Chickweed (Stellaria media) — mild flavor, high in vitamin C\n"
            "6. Wood Sorrel (Oxalis) — lemony flavor, high in vitamin C\n"
            "7. Amaranth (Amaranthus) — protein-rich seeds, edible leaves\n"
            "8. Stinging Nettle (Urtica dioica) — more protein than any cultivated vegetable\n"
            "9. Clover (Trifolium) — flowers edible, fixes nitrogen in soil\n"
            "10. Mallow (Malva) — mucilaginous, soothing for digestive tract\n\n"
            "These plants require no planting, no watering, no fertilizer. They appear for free."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "Eggshell Fertilizer — Replace All Fertilizer Forever",
        "source_url": "https://naturelostvault.com/episodes/episode-99-egg-shells.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Homesteading",
        "chunk": (
            "Eggshells are 95% calcium carbonate — the same compound in agricultural lime. "
            "A single eggshell contains about 2 grams of calcium, plus trace amounts of "
            "magnesium, potassium, and phosphorus.\n\n"
            "To make eggshell fertilizer: rinse shells, dry completely, crush to powder "
            "(coffee grinder works well). The finer the powder, the faster plants absorb it. "
            "Add 1 tablespoon per plant when transplanting, or brew 'eggshell tea' by steeping "
            "crushed shells in water for 24-48 hours.\n\n"
            "Tomatoes, peppers, and squash are especially prone to blossom end rot from "
            "calcium deficiency. Eggshell powder prevents this. A family eating eggs daily "
            "generates enough shells to fertilize a substantial garden — turning kitchen "
            "waste into a closed-loop fertility system."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────────────
    # BUILDING & CONSTRUCTION — HOMESTEADING / CREATION_SCIENCE
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "track": "HOMESTEADING",
        "source_title": "Roman Concrete — Why Ancient Buildings Still Stand",
        "source_url": "https://naturelostvault.com/explore/building-construction.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Building & Construction",
        "chunk": (
            "Roman concrete structures like the Pantheon have stood for 2,000 years, while "
            "modern concrete often cracks within decades. The secret: volcanic ash (pite) "
            "and seawater.\n\n"
            "When Roman concrete contacts seawater, it triggers a chemical reaction that "
            "actually strengthens the material over time. Aluminum tobermorite crystals "
            "grow within the calcium-silicate-hydrate matrix, filling cracks and increasing "
            "density. Modern Portland cement lacks this self-healing property.\n\n"
            "Roman concrete also used less calcium oxide (quickite), requiring lower "
            "kiln temperatures and producing fewer carbon emissions. A 2017 study in "
            "American Mineralogist confirmed the seawater reaction mechanism and suggested "
            "modern engineers could replicate it for more durable marine structures."
        ),
    },
    {
        "track": "CREATION_SCIENCE",
        "source_title": "Rammed Earth Construction — 10,000 Years of Proven Technology",
        "source_url": "https://naturelostvault.com/explore/building-construction.html",
        "citation_author": "Nature Lost Vault",
        "citation_year": 2024,
        "citation_archive_name": "Nature Lost Vault — Building & Construction",
        "chunk": (
            "Rammed earth construction compacts moistened soil between temporary forms to "
            "create solid walls. Sections of the Great Wall of China, built with rammed earth "
            "over 2,000 years ago, still stand today.\n\n"
            "The ideal soil mixture is approximately 70% sand/gravel, 30% clay/silt. Too much "
            "clay causes cracking; too little prevents binding. Soil is moistened to about 10% "
            "water content (should clump when squeezed but not drip), then compacted in 4-6 inch "
            "lifts using pneumatic tampers or hand tools.\n\n"
            "Rammed earth walls provide excellent thermal mass — they absorb heat during the day "
            "and release it at night, naturally regulating indoor temperature. R-value is low, "
            "but thermal lag can reduce heating/cooling costs by 50% in appropriate climates. "
            "The material is fireproof, pest-proof, and returns to soil at end of life."
        ),
    },
]


async def main():
    print("═" * 70)
    print("  NATURE LOST VAULT CURRICULUM SEEDER")
    print("  Tracks: HEALTH_NATUROPATHY, HOMESTEADING, CREATION_SCIENCE")
    print("═" * 70)

    if not OPENAI_API_KEY:
        print("[ERROR] OPENAI_API_KEY not set — cannot generate embeddings")
        sys.exit(1)

    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE

    engine = create_async_engine(
        _pg_dsn,
        echo=False,
        pool_pre_ping=True,
        connect_args={"ssl": ctx, "statement_cache_size": 0},
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        # Ensure table exists
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS "HippocampusDocument" (
                id TEXT PRIMARY KEY,
                track TEXT NOT NULL,
                source_title TEXT NOT NULL,
                source_url TEXT,
                citation_author TEXT,
                citation_year INTEGER,
                citation_archive_name TEXT,
                chunk TEXT NOT NULL,
                embedding vector(1536),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await session.commit()

        inserted = 0
        skipped = 0

        for src in SOURCES:
            # Check for duplicate
            exists = await session.execute(
                text('SELECT 1 FROM "HippocampusDocument" WHERE source_url = :url AND chunk = :chunk LIMIT 1'),
                {"url": src["source_url"], "chunk": src["chunk"][:500]},
            )
            if exists.fetchone():
                print(f"  [SKIP] Already exists: {src['source_title'][:50]}...")
                skipped += 1
                continue

            # Generate embedding
            emb = await embed(src["chunk"])
            if emb is None:
                skipped += 1
                continue

            # Insert
            import uuid
            doc_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO "HippocampusDocument" 
                    (id, track, source_title, source_url, citation_author, citation_year, 
                     citation_archive_name, chunk, embedding)
                    VALUES (:id, :track, :source_title, :source_url, :citation_author, 
                            :citation_year, :citation_archive_name, :chunk, :embedding)
                """),
                {
                    "id": doc_id,
                    "track": src["track"],
                    "source_title": src["source_title"],
                    "source_url": src["source_url"],
                    "citation_author": src["citation_author"],
                    "citation_year": src["citation_year"],
                    "citation_archive_name": src["citation_archive_name"],
                    "chunk": src["chunk"],
                    "embedding": str(emb),
                },
            )
            print(f"  [OK] {src['source_title'][:60]}...")
            inserted += 1

        await session.commit()

    print("─" * 70)
    print(f"  DONE: {inserted} inserted, {skipped} skipped")
    print("═" * 70)


if __name__ == "__main__":
    asyncio.run(main())
