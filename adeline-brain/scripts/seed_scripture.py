"""
Seed Hippocampus with scripture content from Sefaria.

Fetches Everett Fox translations (or default English + Hebrew) for key passages
across the 10-track curriculum and seeds them into Hippocampus for DISCIPLESHIP,
TRUTH_HISTORY, and other relevant tracks.

Run once to populate, then the Sefaria service lazy-caches on demand.

Usage:
    cd adeline-brain
    python scripts/seed_scripture.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.sefaria import fetch_biblical_text, cache_to_hippocampus

# ── Key passages by track ──────────────────────────────────────────────────────
# Format: (reference, track)
# Sefaria will try Everett Fox first, fall back to default English + Hebrew.

PASSAGES = [
    # ── DISCIPLESHIP — core worldview formation ─────────────────────────────────
    ("Proverbs 3:5-6",    "DISCIPLESHIP"),
    ("Proverbs 1:7",      "DISCIPLESHIP"),
    ("Micah 6:8",         "DISCIPLESHIP"),
    ("Deuteronomy 6:4-9", "DISCIPLESHIP"),
    ("Psalm 119:105",     "DISCIPLESHIP"),
    ("Joshua 1:8-9",      "DISCIPLESHIP"),
    ("Isaiah 40:28-31",   "DISCIPLESHIP"),
    ("Romans 12:2",       "DISCIPLESHIP"),
    ("Colossians 3:23",   "DISCIPLESHIP"),
    ("James 1:5",         "DISCIPLESHIP"),
    ("Philippians 4:8",   "DISCIPLESHIP"),
    ("Matthew 5:3-12",    "DISCIPLESHIP"),   # Beatitudes
    ("Psalm 23",          "DISCIPLESHIP"),
    ("Genesis 1:1-5",     "DISCIPLESHIP"),
    ("John 1:1-5",        "DISCIPLESHIP"),
    ("Proverbs 31:10-31", "DISCIPLESHIP"),   # Virtuous woman
    ("Ecclesiastes 3:1-8","DISCIPLESHIP"),   # A time for everything
    ("Isaiah 61:1-3",     "DISCIPLESHIP"),
    ("Psalm 1",           "DISCIPLESHIP"),
    ("Proverbs 22:6",     "DISCIPLESHIP"),

    # ── TRUTH_HISTORY — historical biblical passages ─────────────────────────────
    ("Exodus 1:1-14",     "TRUTH_HISTORY"),  # Israel in Egypt
    ("Exodus 20:1-17",    "TRUTH_HISTORY"),  # Ten Commandments
    ("Nehemiah 1:1-11",   "TRUTH_HISTORY"),  # Rebuilding Jerusalem
    ("Daniel 1:1-8",      "TRUTH_HISTORY"),  # Babylon exile
    ("Esther 4:13-16",    "TRUTH_HISTORY"),  # For such a time as this
    ("Amos 5:21-24",      "TRUTH_HISTORY"),  # Justice roll down
    ("Isaiah 58:6-7",     "TRUTH_HISTORY"),  # True fasting / justice
    ("Jeremiah 29:4-14",  "TRUTH_HISTORY"),  # Letter to the exiles

    # ── JUSTICE_CHANGEMAKING ────────────────────────────────────────────────────
    ("Proverbs 31:8-9",   "JUSTICE_CHANGEMAKING"),  # Speak up for those who cannot
    ("Isaiah 1:17",       "JUSTICE_CHANGEMAKING"),
    ("Luke 4:18-19",      "JUSTICE_CHANGEMAKING"),  # Year of jubilee
    ("Leviticus 25:8-12", "JUSTICE_CHANGEMAKING"),  # Jubilee year
    ("Amos 8:4-7",        "JUSTICE_CHANGEMAKING"),  # Against exploitation

    # ── GOVERNMENT_ECONOMICS ────────────────────────────────────────────────────
    ("Deuteronomy 25:13-16", "GOVERNMENT_ECONOMICS"),  # Honest weights
    ("Proverbs 11:1",        "GOVERNMENT_ECONOMICS"),  # Honest scales
    ("Leviticus 19:35-36",   "GOVERNMENT_ECONOMICS"),
    ("Romans 13:1-7",        "GOVERNMENT_ECONOMICS"),  # Governing authorities
    ("1 Samuel 8:10-18",     "GOVERNMENT_ECONOMICS"),  # Warning about kings

    # ── HEALTH_NATUROPATHY ──────────────────────────────────────────────────────
    ("1 Corinthians 6:19-20", "HEALTH_NATUROPATHY"),  # Body is a temple
    ("Proverbs 17:22",        "HEALTH_NATUROPATHY"),  # Cheerful heart
    ("Genesis 1:29",          "HEALTH_NATUROPATHY"),  # Plants for food
    ("Ezekiel 47:12",         "HEALTH_NATUROPATHY"),  # Leaves for healing

    # ── CREATION_SCIENCE ────────────────────────────────────────────────────────
    ("Genesis 1:1-31",  "CREATION_SCIENCE"),
    ("Genesis 2:1-3",   "CREATION_SCIENCE"),
    ("Psalm 19:1-6",    "CREATION_SCIENCE"),   # Heavens declare
    ("Job 38:1-18",     "CREATION_SCIENCE"),   # Where were you when
    ("Psalm 104:1-35",  "CREATION_SCIENCE"),   # Creation psalm

    # ── HOMESTEADING ────────────────────────────────────────────────────────────
    ("Genesis 2:15",      "HOMESTEADING"),   # Till and keep the garden
    ("Proverbs 27:23-27", "HOMESTEADING"),   # Know your flocks
    ("Leviticus 25:1-7",  "HOMESTEADING"),   # Sabbath for the land
    ("Ruth 2:1-12",       "HOMESTEADING"),   # Gleaning the fields
    ("Psalm 65:9-13",     "HOMESTEADING"),   # You care for the land
]


async def seed_passage(ref: str, track: str) -> bool:
    """Fetch and cache a single passage. Returns True on success."""
    print(f"  Fetching {ref} → {track}...", end=" ", flush=True)
    try:
        data = await fetch_biblical_text(ref)
        if not data:
            print("⚠ Sefaria returned nothing")
            return False

        fox = "✓ Fox" if data["is_fox"] else "  standard"
        doc_id = await cache_to_hippocampus(ref, data, track)
        if doc_id:
            print(f"{fox} → cached ({doc_id[:8]}...)")
            return True
        else:
            print(f"{fox} → already cached")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def main():
    print(f"\n{'='*60}")
    print(f"  Seeding {len(PASSAGES)} scripture passages to Hippocampus")
    print(f"{'='*60}\n")

    success = 0
    fail = 0

    for ref, track in PASSAGES:
        ok = await seed_passage(ref, track)
        if ok:
            success += 1
        else:
            fail += 1
        # Small delay to be polite to Sefaria API
        await asyncio.sleep(0.3)

    print(f"\n{'='*60}")
    print(f"  Done: {success} seeded, {fail} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
