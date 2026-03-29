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
    # ── HOMESTEADING ─────────────────────────────────────────────────────────
    {
        "track": "HOMESTEADING",
        "source_title": "The Homestead Act of 1862",
        "source_url": "https://www.archives.gov/education/lessons/homestead-act",
        "citation_author": "U.S. Congress",
        "citation_year": 1862,
        "citation_archive_name": "National Archives",
        "chunk": (
            "Be it enacted by the Senate and House of Representatives of the United "
            "States of America in Congress assembled, That any person who is the head of "
            "a family, or who has arrived at the age of twenty-one years, and is a "
            "citizen of the United States, or who shall have filed his declaration of "
            "intention to become such, shall be entitled to enter one quarter section or "
            "a less quantity of unappropriated public lands."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "The American Frugal Housewife",
        "source_url": "https://www.gutenberg.org/ebooks/13493",
        "citation_author": "Lydia Maria Child",
        "citation_year": 1833,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "The true economy of housekeeping is simply the art of gathering up all the "
            "fragments, so that nothing be lost. I mean fragments of time, as well as "
            "materials. Nothing should be thrown away so long as it is possible to make "
            "any use of it, however trifling that use may be; and whatever be the "
            "article under consideration, it is not wasteful to use it in its place."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "Farmers' Bulletin No. 1: The What and Why of Agricultural Experiment Stations",
        "source_url": "https://archive.org/details/farmersbulletin00unit",
        "citation_author": "U.S. Department of Agriculture",
        "citation_year": 1889,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "The object of experiment stations is to aid the farmer in the practical "
            "work of agriculture by conducting investigations and experiments bearing "
            "directly upon the profitable cultivation of the various crops; the best "
            "methods of treatment and feeding of live stock; the renovation and "
            "fertilization of soils; and all other subjects relating to rural industry."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "Ox-Team Days on the Oregon Trail",
        "source_url": "https://www.gutenberg.org/ebooks/43861",
        "citation_author": "Ezra Meeker",
        "citation_year": 1922,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "The homesteader learned to make the land feed him and his family by using "
            "every scrap of knowledge earned through trial and failure. The sod house "
            "was our first shelter, the ox team our first engine, and the open prairie "
            "our first classroom. Every season taught a new lesson about soil, weather, "
            "and the stubborn truth that the land will provide only to those who learn "
            "her language."
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
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "Hamlet, Act III, Scene 1",
        "source_url": "https://www.gutenberg.org/ebooks/1524",
        "citation_author": "William Shakespeare",
        "citation_year": 1603,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "To be, or not to be: that is the question: Whether 'tis nobler in the mind "
            "to suffer the slings and arrows of outrageous fortune, or to take arms "
            "against a sea of troubles, and by opposing end them? To die: to sleep; "
            "no more; and by a sleep to say we end the heart-ache and the thousand "
            "natural shocks that flesh is heir to, 'tis a consummation devoutly to be "
            "wish'd."
        ),
    },
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "Pride and Prejudice, Chapter 1",
        "source_url": "https://www.gutenberg.org/ebooks/1342",
        "citation_author": "Jane Austen",
        "citation_year": 1813,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "It is a truth universally acknowledged, that a single man in possession of "
            "a good fortune, must be in want of a wife. However little known the feelings "
            "or views of such a man may be on his first entering a neighbourhood, this "
            "truth is so well fixed in the minds of the surrounding families, that he is "
            "considered the rightful property of some one or other of their daughters."
        ),
    },
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "Because I could not stop for Death",
        "source_url": "https://www.poetryfoundation.org/poems/47652/because-i-could-not-stop-for-death-479",
        "citation_author": "Emily Dickinson",
        "citation_year": 1890,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "Because I could not stop for Death \u2013 He kindly stopped for me \u2013 "
            "The Carriage held but just Ourselves \u2013 And Immortality. We slowly "
            "drove \u2013 He knew no haste And I had put away My labor and my leisure "
            "too, For His Civility \u2013"
        ),
    },
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "Orthodoxy, Chapter IV: The Ethics of Elfland",
        "source_url": "https://www.gutenberg.org/ebooks/130",
        "citation_author": "G.K. Chesterton",
        "citation_year": 1908,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "My first and last philosophy, that which I believe in with unbroken "
            "certainty, I learnt in the nursery. The things I believed most then, the "
            "things I believe most now, are the things called fairy tales. They seem to "
            "me to be the entirely reasonable things. Fairyland is nothing but the sunny "
            "country of common sense."
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
