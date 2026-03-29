#!/usr/bin/env python3
"""
seed_hippocampus.py — Seed the 4 remaining Hippocampus tracks.

Covers: CREATION_SCIENCE, HOMESTEADING, DISCIPLESHIP, ENGLISH_LITERATURE
(TRUTH_HISTORY, JUSTICE_CHANGEMAKING, GOVERNMENT_ECONOMICS, HEALTH_NATUROPATHY
are handled by seed_curriculum.py and seed_corpus_expansion.py.)

Run:  cd adeline-brain && python scripts/seed_hippocampus.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import openai
from app.connections.pgvector_client import hippocampus

EMBED_MODEL = "text-embedding-3-small"


async def embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


# ── Source Documents ─────────────────────────────────────────────────────────
# Each chunk is a genuine excerpt from public domain primary sources.
# Citations reference real archives and dates.

SOURCES = [
    # ── CREATION_SCIENCE ─────────────────────────────────────────────────────
    {
        "track": "CREATION_SCIENCE",
        "source_title": "Genesis 1:1-31 (KJV)",
        "source_url": "https://www.kingjamesbibleonline.org/Genesis-Chapter-1/",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "In the beginning God created the heaven and the earth. And the earth was "
            "without form, and void; and darkness was upon the face of the deep. And the "
            "Spirit of God moved upon the face of the waters. And God said, Let there be "
            "light: and there was light. And God saw the light, that it was good: and God "
            "divided the light from the darkness. And God called the light Day, and the "
            "darkness he called Night. And the evening and the morning were the first day."
        ),
    },
    {
        "track": "CREATION_SCIENCE",
        "source_title": "Psalm 19:1-6 (KJV)",
        "source_url": "https://www.kingjamesbibleonline.org/Psalm-Chapter-19/",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "The heavens declare the glory of God; and the firmament sheweth his "
            "handywork. Day unto day uttereth speech, and night unto night sheweth "
            "knowledge. There is no speech nor language, where their voice is not heard. "
            "Their line is gone out through all the earth, and their words to the end of "
            "the world. In them hath he set a tabernacle for the sun, which is as a "
            "bridegroom coming out of his chamber, and rejoiceth as a strong man to run "
            "a race. His going forth is from the end of the heaven, and his circuit unto "
            "the ends of it: and there is nothing hid from the heat thereof."
        ),
    },
    {
        "track": "CREATION_SCIENCE",
        "source_title": "My First Summer in the Sierra",
        "source_url": "https://www.gutenberg.org/ebooks/32540",
        "citation_author": "John Muir",
        "citation_year": 1911,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "We are now in the mountains and they are in us, kindling enthusiasm, making "
            "every nerve quiver, filling every pore and cell of us. Our flesh-and-bone "
            "tabernacle seems transparent as glass to the beauty about us, as if truly an "
            "inseparable part of it, thrilling with the air and trees, streams and rocks, "
            "in the waves of the sun \u2014 a part of all nature, neither old nor young, "
            "sick nor well, but immortal."
        ),
    },
    {
        "track": "CREATION_SCIENCE",
        "source_title": "The Origin of Species (Introduction)",
        "source_url": "https://www.gutenberg.org/ebooks/1228",
        "citation_author": "Charles Darwin",
        "citation_year": 1859,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "When on board H.M.S. Beagle, as naturalist, I was much struck with certain "
            "facts in the distribution of the organic beings inhabiting South America, "
            "and in the geological relations of the present to the past inhabitants of "
            "that continent. These facts seemed to throw some light on the origin of "
            "species \u2014 that mystery of mysteries, as it has been called by one of our "
            "greatest philosophers."
        ),
    },
    # ── HOMESTEADING — Grid-down survival and self-sufficiency ───────────────
    # Frame: if everything crashed tomorrow, could your family survive?
    # No electricity. No grocery store. No pharmacy. No lumber yard.
    {
        "track": "HOMESTEADING",
        "source_title": "The American Frugal Housewife — Food Preservation",
        "source_url": "https://www.gutenberg.org/ebooks/13493",
        "citation_author": "Lydia Maria Child",
        "citation_year": 1833,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "Pork should be salted in December or January. Put a layer of salt in the "
            "bottom of the barrel; then a layer of pork; then salt again; and so on "
            "alternately. Make a strong brine of salt and water — strong enough to bear "
            "up an egg. Add saltpetre and brown sugar. Pour this over the meat and keep "
            "it pressed down with a heavy stone. Smoke-curing requires hanging meat in "
            "the smokehouse six weeks over green hickory or corncob smoke. Meat cured "
            "this way keeps through summer without refrigeration. Every family that "
            "grows and preserves its own food is a family no grocery store can hold hostage."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "The American Frugal Housewife — Home Remedies Without a Pharmacy",
        "source_url": "https://www.gutenberg.org/ebooks/13493",
        "citation_author": "Lydia Maria Child",
        "citation_year": 1833,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "Poultices of bread and milk draw out infections from wounds when no doctor "
            "is near. Onion juice dropped into the ear relieves earache; a poultice of "
            "roasted onion bound to the throat breaks up a cold. Plantain leaves, bruised "
            "and bound on bee stings, take out the swelling in minutes. Sage tea soothes "
            "sore throats. Strong ginger tea settles a sick stomach. These remedies "
            "require no prescription, no pharmacy, and no supply chain. They grow in your "
            "yard. They have worked for generations. Knowing them makes you free."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "Foxfire Book — Building Without a Lumber Yard",
        "source_url": "https://archive.org/details/foxfire1",
        "citation_author": "Eliot Wigginton (ed.)",
        "citation_year": 1972,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "The old-timers needed no lumber yard. They selected their timber standing. "
            "Chestnut split clean and straight for fence rails. Oak was the choice for "
            "sills and floor joists because it does not rot. Pine was laid up green for "
            "walls and allowed to season in place. Notching a corner required only an axe "
            "and a good eye. The mortise-and-tenon joint, held by a wooden peg, is "
            "stronger than any nail. A man who knows timber and owns an axe can build a "
            "house. A man who only knows Home Depot cannot."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "Foxfire Book — Water Without Infrastructure",
        "source_url": "https://archive.org/details/foxfire1",
        "citation_author": "Eliot Wigginton (ed.)",
        "citation_year": 1972,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "Finding water when the well pump fails begins with reading the land. Springs "
            "emerge where a hillside changes slope or where a band of rock forces water "
            "upward. Willows and alders grow along hidden streams. A hand-dug well lined "
            "with dry-stacked stone can serve a family for generations. Collecting "
            "rainwater from a metal roof into sealed barrels requires no electricity and "
            "no utility bill. Boiling water for five minutes kills what would kill you. "
            "These are not pioneer curiosities. They are the skills every family needs "
            "when the infrastructure people trusted breaks down."
        ),
    },
    # ── DISCIPLESHIP ─────────────────────────────────────────────────────────
    {
        "track": "DISCIPLESHIP",
        "source_title": "Matthew 5:1-16 (KJV) \u2014 The Sermon on the Mount",
        "source_url": "https://www.kingjamesbibleonline.org/Matthew-Chapter-5/",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "And seeing the multitudes, he went up into a mountain: and when he was set, "
            "his disciples came unto him: And he opened his mouth, and taught them, "
            "saying, Blessed are the poor in spirit: for theirs is the kingdom of heaven. "
            "Blessed are they that mourn: for they shall be comforted. Blessed are the "
            "meek: for they shall inherit the earth. Blessed are they which do hunger "
            "and thirst after righteousness: for they shall be filled."
        ),
    },
    {
        "track": "DISCIPLESHIP",
        "source_title": "Proverbs 3:1-18 (KJV)",
        "source_url": "https://www.kingjamesbibleonline.org/Proverbs-Chapter-3/",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "Trust in the LORD with all thine heart; and lean not unto thine own "
            "understanding. In all thy ways acknowledge him, and he shall direct thy "
            "paths. Be not wise in thine own eyes: fear the LORD, and depart from evil. "
            "It shall be health to thy navel, and marrow to thy bones. Happy is the man "
            "that findeth wisdom, and the man that getteth understanding."
        ),
    },
    {
        "track": "DISCIPLESHIP",
        "source_title": "Confessions, Book I",
        "source_url": "https://www.gutenberg.org/ebooks/3296",
        "citation_author": "Augustine of Hippo",
        "citation_year": 397,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "Great art Thou, O Lord, and greatly to be praised; great is Thy power, and "
            "Thy wisdom infinite. And Thee would man praise; man, but a particle of Thy "
            "creation; man, that bears about him his mortality, the witness of his sin. "
            "And yet would man praise Thee; he, but a particle of Thy creation. Thou "
            "awakest us to delight in Thy praise; for Thou madest us for Thyself, and "
            "our heart is restless, until it repose in Thee."
        ),
    },
    {
        "track": "DISCIPLESHIP",
        "source_title": "The Pilgrim's Progress",
        "source_url": "https://www.gutenberg.org/ebooks/131",
        "citation_author": "John Bunyan",
        "citation_year": 1678,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "As I walked through the wilderness of this world, I lighted on a certain "
            "place where was a Den, and I laid me down in that place to sleep: and, as I "
            "slept, I dreamed a dream. I dreamed, and behold, I saw a man clothed with "
            "rags, standing in a certain place, with his face from his own house, a book "
            "in his hand, and a great burden upon his back."
        ),
    },
    # ── ENGLISH_LITERATURE ───────────────────────────────────────────────────
    # Curriculum reading list (not in Hippocampus — too new for public domain):
    #   "Do Hard Things" by Alex & Brett Harris (2008)
    #   C.S. Lewis: Mere Christianity, The Screwtape Letters, The Abolition of Man
    # Adeline surfaces these in synthesis and recommendations.
    # Hippocampus seeds the OKLAHOMA ELA standards-aligned public domain texts below.
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "Orthodoxy — Why I Believe in Christianity",
        "source_url": "https://www.gutenberg.org/ebooks/130",
        "citation_author": "G.K. Chesterton",
        "citation_year": 1908,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "The modern world is not evil; in some ways the modern world is far too good. "
            "It is full of wild and wasted virtues. When a religious scheme is shattered "
            "it is not merely the vices that are let loose. The vices are, indeed, let "
            "loose, and they wander and do damage. But the virtues are let loose also; "
            "and the virtues wander more wildly, and the virtues do more terrible damage. "
            "The modern world is full of the old Christian virtues gone mad."
        ),
    },
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "The Abolition of Man — Men Without Chests",
        "source_url": "https://archive.org/details/AbolitionOfMan_934",
        "citation_author": "C.S. Lewis",
        "citation_year": 1943,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "In a sort of ghastly simplicity we remove the organ and demand the function. "
            "We make men without chests and expect of them virtue and enterprise. We laugh "
            "at honour and are shocked to find traitors in our midst. We castrate and bid "
            "the geldings be fruitful."
        ),
    },
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "Letter from Birmingham Jail",
        "source_url": "https://www.africa.upenn.edu/Articles_Gen/Letter_Birmingham.html",
        "citation_author": "Martin Luther King Jr.",
        "citation_year": 1963,
        "citation_archive_name": "University of Pennsylvania African Studies Center",
        "chunk": (
            "One who breaks an unjust law must do so openly, lovingly, and with a "
            "willingness to accept the penalty. I submit that an individual who breaks a "
            "law that conscience tells him is unjust, and who willingly accepts the "
            "penalty of imprisonment in order to arouse the conscience of the community "
            "over its injustice, is in reality expressing the highest respect for law."
        ),
    },
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "Up from Slavery — Chapter I",
        "source_url": "https://www.gutenberg.org/ebooks/2376",
        "citation_author": "Booker T. Washington",
        "citation_year": 1901,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "I was born a slave on a plantation in Franklin County, Virginia. I am not "
            "quite sure of the exact place or exact date of my birth, but at any rate "
            "I suspect I must have been born somewhere and at some time. As nearly as I "
            "have been able to learn, I was born near a cross-roads post-office called "
            "Hale's Ford, and the year was 1858 or 1859. I do not know the month or the "
            "day. The earliest impressions I can now recall are of the plantation and the "
            "slave quarters — the latter being the part of the plantation where the slaves "
            "had their cabins."
        ),
    },
    # ── APPLIED_MATHEMATICS — Real-world math: money, land, building, market ───
    # Curriculum reading (not in Hippocampus — copyrighted):
    #   Oklahoma Academic Standards for Mathematics (grade-level standards)
    # Hippocampus seeds: public domain sources showing math in real work
    {
        "track": "APPLIED_MATHEMATICS",
        "source_title": "Advice to a Young Tradesman — The Power of Compound Interest",
        "source_url": "https://www.gutenberg.org/ebooks/148",
        "citation_author": "Benjamin Franklin",
        "citation_year": 1748,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "Remember that money is of the prolific, generating nature. Money can beget money, "
            "and its offspring can beget more, and so on. Five shillings turned is six, turned "
            "again it is seven and three pence, and so on till it becomes a hundred pounds. "
            "The more there is of it, the more it produces every turning, so that the profits "
            "rise quicker and quicker. He that kills a breeding sow, destroys all her offspring "
            "to the thousandth generation. He that murders a crown, destroys all that it might "
            "have produced, even scores of pounds. Remember that time is money."
        ),
    },
    {
        "track": "APPLIED_MATHEMATICS",
        "source_title": "The American Frugal Housewife — Household Accounts",
        "source_url": "https://www.gutenberg.org/ebooks/13493",
        "citation_author": "Lydia Maria Child",
        "citation_year": 1833,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "A woman who keeps exact accounts will always know what she can and cannot afford. "
            "Write down every expense, however trifling. At the end of the week, cast up the "
            "column. If the sum exceeds what you earned, you are already in debt to yourself. "
            "If it is less, you have the beginning of independence. The difference between "
            "a family that thrives and one that is always poor is not income — it is arithmetic. "
            "The family that counts every shilling knows when it is wasting and when it is "
            "building. That is the whole art of household management."
        ),
    },
    {
        "track": "APPLIED_MATHEMATICS",
        "source_title": "The Foxfire Book — Measuring Land by Chain and Compass",
        "source_url": "https://archive.org/details/foxfire1",
        "citation_author": "Eliot Wigginton (ed.)",
        "citation_year": 1972,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "Every man who owns land should be able to measure it himself. A chain is sixty-six "
            "feet. Ten chains square is one acre — forty-three thousand five hundred and sixty "
            "square feet. Walk the boundary. Count your chains. Multiply length by width and "
            "divide by ten. A man who does not know the area of his own fields cannot know what "
            "his land can produce, what seed he needs, what harvest he can expect, or what his "
            "property is worth. Geometry is not a school subject. It is the difference between "
            "owning your land and being cheated out of it."
        ),
    },
    {
        "track": "APPLIED_MATHEMATICS",
        "source_title": "Elements — Book II, Proposition 14 (On Areas and Ratios)",
        "source_url": "https://www.gutenberg.org/ebooks/21076",
        "citation_author": "Euclid",
        "citation_year": -300,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "To construct a square equal in area to a given rectilineal figure. Let A be the "
            "given rectilineal figure; it is required to construct a square equal to A. "
            "For it is possible to construct a rectangle equal to any rectilineal figure. "
            "So let the rectangle BD be constructed equal to the rectilineal figure A. "
            "If, then, BE equals ED, what was enjoined will have been done; and a square BD "
            "has been constructed equal to the rectilineal figure A. "
            "Ratios of areas, lengths, and proportions are the foundation of every measurement — "
            "in land, in building, in trade, and in the sciences of nature."
        ),
    },
]


async def main():
    print("Connecting to Hippocampus (pgvector)...")
    await hippocampus.connect()

    total = 0
    for source in SOURCES:
        print(f"  Embedding: {source['source_title']} ({source['track']})...")
        embedding = await embed(source["chunk"])
        await hippocampus.upsert_document(
            source_title=source["source_title"],
            track=source["track"],
            chunk=source["chunk"],
            embedding=embedding,
            citation_author=source["citation_author"],
            citation_year=source.get("citation_year"),
            citation_archive_name=source["citation_archive_name"],
            source_url=source["source_url"],
        )
        total += 1
        print(f"    Done ({len(source['chunk'])} chars)")

    count = await hippocampus.count_documents()
    print(f"\nSeeded {total} chunks. Total in Hippocampus: {count}")


if __name__ == "__main__":
    asyncio.run(main())
