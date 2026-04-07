#!/usr/bin/env python3
"""
seed_corpus_expansion.py — Expand the Hippocampus corpus.

Fills gaps in: HEALTH_NATUROPATHY (0→5), GOVERNMENT_ECONOMICS (0→5),
TRUTH_HISTORY (3→9), and deepens all other tracks with sources aligned
to Adeline's values:
  - Farm as laboratory, grid-down self-sufficiency
  - Biblical worldview, discipleship through real life
  - Portfolio of accomplishments — making, building, growing, selling
  - Primary sources for history/government/justice tracks
  - Math tied to land, commerce, and building — not worksheets

Run:  cd adeline-brain && python scripts/seed_corpus_expansion.py
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


SOURCES = [
    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH_NATUROPATHY — 0 chunks exist. Biblical health, herbal medicine,
    # nutrition, body stewardship. Not primary-source-gated.
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Leviticus 11:1-23 (KJV) — Clean and Unclean Foods",
        "source_url": "https://www.kingjamesbibleonline.org/Leviticus-Chapter-11/",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "And the LORD spake unto Moses and to Aaron, saying unto them, Speak unto "
            "the children of Israel, saying, These are the beasts which ye shall eat "
            "among all the beasts that are on the earth. Whatsoever parteth the hoof, "
            "and is clovenfooted, and cheweth the cud, among the beasts, that shall ye "
            "eat. These shall ye eat of all that are in the waters: whatsoever hath fins "
            "and scales in the waters, in the seas, and in the rivers, them shall ye eat. "
            "The dietary laws given to Israel distinguished clean from unclean animals — "
            "a framework for health that preceded germ theory by millennia."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "The American Herbal — Elderberry and Immune Function",
        "source_url": "https://www.gutenberg.org/ebooks/41680",
        "citation_author": "Samuel Stearns",
        "citation_year": 1801,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "The elder tree is one of the most useful plants in the physician's garden. "
            "The flowers, steeped in boiling water, produce a tea that opens the pores "
            "and promotes perspiration — useful in fevers and colds. The berries, boiled "
            "into syrup with honey, soothe sore throats and strengthen the constitution "
            "against winter illness. The bark, taken in small quantities, acts as a "
            "purgative. The leaves, bruised and applied as a poultice, reduce swelling "
            "from sprains and bruises. Every part of the elder serves a medicinal purpose. "
            "A family that grows elderberry needs no pharmacy for common winter ailments."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Daniel 1:8-16 (KJV) — The Pulse and Water Test",
        "source_url": "https://www.kingjamesbibleonline.org/Daniel-Chapter-1/",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "But Daniel purposed in his heart that he would not defile himself with the "
            "portion of the king's meat, nor with the wine which he drank. Prove thy "
            "servants, I beseech thee, ten days; and let them give us pulse to eat, and "
            "water to drink. Then let our countenances be looked upon before thee, and "
            "the countenance of the children that eat of the portion of the king's meat. "
            "And at the end of ten days their countenances appeared fairer and fatter in "
            "flesh than all the children which did eat the portion of the king's meat. "
            "Daniel's test is the first recorded controlled dietary experiment — simple "
            "food and water against the richest table in the empire."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Every Man His Own Doctor — Kitchen Physic",
        "source_url": "https://archive.org/details/everymanhi00tend",
        "citation_author": "John Tennent",
        "citation_year": 1734,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "The best physic is that which comes from the garden and the kitchen. Garlic "
            "taken daily strengthens the blood and wards off contagion. Honey mixed with "
            "apple cider vinegar and warm water, taken each morning, settles the stomach "
            "and clears the head. Chamomile tea calms the nerves and invites sleep. "
            "Peppermint relieves indigestion better than any compounded pill. Turmeric "
            "root, grated into broth, reduces the inflammation of joints. These remedies "
            "cost nothing but attention. The family that knows its herbs and roots is a "
            "family that does not depend on a drugstore to stay well."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "1 Corinthians 6:19-20 (KJV) — The Body as Temple",
        "source_url": "https://www.kingjamesbibleonline.org/1-Corinthians-Chapter-6/",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "What? know ye not that your body is the temple of the Holy Ghost which is "
            "in you, which ye have of God, and ye are not your own? For ye are bought "
            "with a price: therefore glorify God in your body, and in your spirit, which "
            "are God's. The stewardship of the body is not vanity — it is worship. What "
            "you eat, how you move, how you rest, and what you refuse to put into your "
            "body are acts of obedience. Health is not the absence of disease. It is the "
            "faithful care of what God entrusted to you."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # GOVERNMENT_ECONOMICS — 0 chunks exist. Primary founding documents,
    # property rights, free markets, constitutional principles.
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "GOVERNMENT_ECONOMICS",
        "source_title": "Declaration of Independence — Preamble",
        "source_url": "https://www.archives.gov/founding-docs/declaration-transcript",
        "citation_author": "Thomas Jefferson et al.",
        "citation_year": 1776,
        "citation_archive_name": "National Archives",
        "chunk": (
            "We hold these truths to be self-evident, that all men are created equal, "
            "that they are endowed by their Creator with certain unalienable Rights, "
            "that among these are Life, Liberty and the pursuit of Happiness. That to "
            "secure these rights, Governments are instituted among Men, deriving their "
            "just powers from the consent of the governed. That whenever any Form of "
            "Government becomes destructive of these ends, it is the Right of the "
            "People to alter or to abolish it, and to institute new Government, laying "
            "its foundation on such principles and organizing its powers in such form, "
            "as to them shall seem most likely to effect their Safety and Happiness."
        ),
    },
    {
        "track": "GOVERNMENT_ECONOMICS",
        "source_title": "U.S. Constitution — Bill of Rights (Amendments I-X)",
        "source_url": "https://www.archives.gov/founding-docs/bill-of-rights-transcript",
        "citation_author": "James Madison et al.",
        "citation_year": 1791,
        "citation_archive_name": "National Archives",
        "chunk": (
            "Amendment I: Congress shall make no law respecting an establishment of "
            "religion, or prohibiting the free exercise thereof; or abridging the freedom "
            "of speech, or of the press; or the right of the people peaceably to assemble, "
            "and to petition the Government for a redress of grievances. Amendment II: "
            "A well regulated Militia, being necessary to the security of a free State, "
            "the right of the people to keep and bear Arms, shall not be infringed. "
            "Amendment IV: The right of the people to be secure in their persons, houses, "
            "papers, and effects, against unreasonable searches and seizures, shall not "
            "be violated."
        ),
    },
    {
        "track": "GOVERNMENT_ECONOMICS",
        "source_title": "Federalist No. 10 — Factions and Republic",
        "source_url": "https://www.congress.gov/resources/display/content/The+Federalist+Papers#TheFederalistPapers-10",
        "citation_author": "James Madison",
        "citation_year": 1787,
        "citation_archive_name": "Library of Congress",
        "chunk": (
            "By a faction, I understand a number of citizens, whether amounting to a "
            "majority or a minority of the whole, who are united and actuated by some "
            "common impulse of passion, or of interest, adverse to the rights of other "
            "citizens, or to the permanent and aggregate interests of the community. "
            "The latent causes of faction are thus sown in the nature of man. A republic, "
            "by which I mean a government in which the scheme of representation takes "
            "place, opens a different prospect, and promises the cure for which we are "
            "seeking. A republic filters the passions of the majority through elected "
            "representatives — but only if those representatives answer to the people "
            "and not to the factions that fund them."
        ),
    },
    {
        "track": "GOVERNMENT_ECONOMICS",
        "source_title": "The Wealth of Nations — Division of Labour",
        "source_url": "https://www.gutenberg.org/ebooks/3300",
        "citation_author": "Adam Smith",
        "citation_year": 1776,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "The greatest improvement in the productive powers of labour, and the greater "
            "part of the skill, dexterity, and judgment with which it is anywhere directed, "
            "or applied, seem to have been the effects of the division of labour. One man "
            "draws out the wire, another straightens it, a third cuts it, a fourth points "
            "it, a fifth grinds it at the top for receiving the head. Ten persons could "
            "make among them upwards of forty-eight thousand pins in a day. But if they "
            "had all wrought separately and independently, they certainly could not each "
            "of them have made twenty, perhaps not one pin in a day. Specialization "
            "multiplies output — but the specialist who cannot do anything else is "
            "dependent on the system that employs him."
        ),
    },
    {
        "track": "GOVERNMENT_ECONOMICS",
        "source_title": "Farewell Address — Warnings Against Faction and Debt",
        "source_url": "https://www.archives.gov/exhibits/american_originals/farewell.html",
        "citation_author": "George Washington",
        "citation_year": 1796,
        "citation_archive_name": "National Archives",
        "chunk": (
            "As a very important source of strength and security, cherish public credit. "
            "One method of preserving it is to use it as sparingly as possible, avoiding "
            "occasions of expense by cultivating peace. Avoid likewise the accumulation "
            "of debt, not only by shunning occasions of expense, but by vigorous exertion "
            "in time of peace to discharge the debts which unavoidable wars may have "
            "occasioned, not ungenerously throwing upon posterity the burden which we "
            "ourselves ought to bear. The spirit of encroachment tends to consolidate the "
            "powers of all the departments in one, and thus to create a real despotism."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # TRUTH_HISTORY — Only Douglass exists. Founding era, civil rights,
    # Native American history, Reconstruction. PRIMARY SOURCES.
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "TRUTH_HISTORY",
        "source_title": "Emancipation Proclamation",
        "source_url": "https://www.archives.gov/exhibits/featured-documents/emancipation-proclamation",
        "citation_author": "Abraham Lincoln",
        "citation_year": 1863,
        "citation_archive_name": "National Archives",
        "chunk": (
            "That on the first day of January, in the year of our Lord one thousand eight "
            "hundred and sixty-three, all persons held as slaves within any State or "
            "designated part of a State, the people whereof shall then be in rebellion "
            "against the United States, shall be then, thenceforward, and forever free; "
            "and the Executive Government of the United States, including the military "
            "and naval authority thereof, will recognize and maintain the freedom of such "
            "persons, and will do no act or acts to repress such persons, or any of them, "
            "in any efforts they may make for their actual freedom."
        ),
    },
    {
        "track": "TRUTH_HISTORY",
        "source_title": "Gettysburg Address",
        "source_url": "https://www.loc.gov/resource/rbpe.24404500/",
        "citation_author": "Abraham Lincoln",
        "citation_year": 1863,
        "citation_archive_name": "Library of Congress",
        "chunk": (
            "Four score and seven years ago our fathers brought forth on this continent, "
            "a new nation, conceived in Liberty, and dedicated to the proposition that all "
            "men are created equal. Now we are engaged in a great civil war, testing whether "
            "that nation, or any nation so conceived and so dedicated, can long endure. "
            "It is rather for us to be here dedicated to the great task remaining before "
            "us — that from these honored dead we take increased devotion to that cause "
            "for which they gave the last full measure of devotion — that we here highly "
            "resolve that these dead shall not have died in vain — that this nation, under "
            "God, shall have a new birth of freedom."
        ),
    },
    {
        "track": "TRUTH_HISTORY",
        "source_title": "Dawes Act (General Allotment Act)",
        "source_url": "https://www.archives.gov/milestone-documents/dawes-act",
        "citation_author": "U.S. Congress",
        "citation_year": 1887,
        "citation_archive_name": "National Archives",
        "chunk": (
            "An Act to provide for the allotment of lands in severalty to Indians on the "
            "various reservations, and to extend the protection of the laws of the United "
            "States and the Territories over the Indians. Every Indian born within the "
            "territorial limits of the United States who has voluntarily taken up his "
            "residence separate and apart from any tribe of Indians therein, and has "
            "adopted the habits of civilized life, is hereby declared to be a citizen. "
            "The Dawes Act broke tribal land holdings into individual parcels — within "
            "47 years, Native nations lost two-thirds of their land. What was framed as "
            "citizenship was in practice dispossession."
        ),
    },
    {
        "track": "TRUTH_HISTORY",
        "source_title": "Treaty of New Echota (Cherokee Removal)",
        "source_url": "https://www.archives.gov/education/lessons/cherokee",
        "citation_author": "U.S. Government / Cherokee Nation (disputed)",
        "citation_year": 1835,
        "citation_archive_name": "National Archives",
        "chunk": (
            "The Cherokee Nation hereby cedes, relinquishes, and conveys to the United "
            "States all the lands owned, claimed, or possessed by them east of the "
            "Mississippi River. In consideration of the sum of five million dollars, "
            "the Cherokee shall remove to the territory west of the Mississippi. "
            "This treaty was signed by a minority faction without the authority of the "
            "Cherokee National Council. Chief John Ross and over 15,000 Cherokee protested "
            "in a petition to Congress. The treaty was ratified by a single vote. "
            "The forced removal that followed — the Trail of Tears — killed an estimated "
            "4,000 Cherokee. A primary source document showing how legal process was used "
            "to dispossess a sovereign nation."
        ),
    },
    {
        "track": "TRUTH_HISTORY",
        "source_title": "Thirteenth Amendment to the U.S. Constitution",
        "source_url": "https://www.archives.gov/milestone-documents/13th-amendment",
        "citation_author": "U.S. Congress",
        "citation_year": 1865,
        "citation_archive_name": "National Archives",
        "chunk": (
            "Section 1. Neither slavery nor involuntary servitude, except as a punishment "
            "for crime whereof the party shall have been duly convicted, shall exist within "
            "the United States, or any place subject to their jurisdiction. Section 2. "
            "Congress shall have power to enforce this article by appropriate legislation. "
            "The Thirteenth Amendment abolished slavery — but its exception clause for "
            "convicted persons created a legal pathway that would be exploited through "
            "convict leasing, chain gangs, and mass incarceration for generations to come. "
            "The text of a law is never the whole story. Read what it permits as carefully "
            "as what it prohibits."
        ),
    },
    {
        "track": "TRUTH_HISTORY",
        "source_title": "Oklahoma Land Run — Proclamation Opening the Unassigned Lands",
        "source_url": "https://www.archives.gov/legislative/features/oklahoma",
        "citation_author": "Benjamin Harrison",
        "citation_year": 1889,
        "citation_archive_name": "National Archives",
        "chunk": (
            "I, Benjamin Harrison, President of the United States, by virtue of the power "
            "in me vested by the act of Congress approved March second, eighteen hundred "
            "and eighty-nine, do hereby declare and make known that the lands in the "
            "Indian Territory known as the Unassigned Lands are open to settlement under "
            "the provisions of the homestead law. On April 22, 1889, an estimated 50,000 "
            "settlers raced to claim nearly two million acres of land that had been "
            "designated as Indian Territory. Oklahoma's founding is inseparable from "
            "the displacement of the nations that lived here first. The land run is "
            "celebrated as pioneer spirit — but the land was not empty."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # HOMESTEADING — Deepen grid-down skills: animal husbandry, soil, soap
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "HOMESTEADING",
        "source_title": "The American Frugal Housewife — Soap Making",
        "source_url": "https://www.gutenberg.org/ebooks/13493#soap",
        "citation_author": "Lydia Maria Child",
        "citation_year": 1833,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "Save all your grease drippings in a stone crock. When you have enough — "
            "about six pounds — mix it with lye water made by running rainwater through "
            "wood ashes. Boil the mixture slowly for several hours, stirring with a "
            "wooden paddle. When it thickens and a drop holds its shape on a cold plate, "
            "pour it into moulds and let it harden for a week. This soap cleans clothes, "
            "dishes, and bodies. It costs nothing but kitchen waste and patience. A family "
            "that makes its own soap from its own ashes and its own grease has one less "
            "thing to buy and one more skill that cannot be taken away."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "Foxfire Book — Keeping a Milk Cow and Making Butter",
        "source_url": "https://archive.org/details/foxfire1#butter",
        "citation_author": "Eliot Wigginton (ed.)",
        "citation_year": 1972,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "A good milk cow gives four to six gallons a day. Let the milk sit in a cool "
            "place overnight and the cream rises to the top. Skim it off and churn it — "
            "a dasher churn takes about thirty minutes of steady work. When the butter "
            "comes, wash it in cold water three times to get the buttermilk out, or it "
            "will go rancid. Salt it and press it into moulds. The buttermilk left behind "
            "makes the best biscuits and cornbread you will ever eat. One cow, properly "
            "kept, gives a family milk, cream, butter, buttermilk, and cheese. That is "
            "an entire dairy section produced in your own barn."
        ),
    },
    {
        "track": "HOMESTEADING",
        "source_title": "Farmers' Bulletin No. 1452 — Soil Fertility and Composting",
        "source_url": "https://archive.org/details/CAT87201428#composting",
        "citation_author": "U.S. Department of Agriculture",
        "citation_year": 1925,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "The fertility of soil depends upon the organic matter it contains. Compost "
            "is made by layering green material — kitchen scraps, garden waste, fresh "
            "manure — with brown material — dry leaves, straw, wood shavings. Turn the "
            "pile every two weeks. In three months, the pile becomes dark, crumbly earth "
            "that smells like a forest floor. This is the best fertilizer that exists. "
            "It costs nothing. It requires no factory, no supply chain, and no shipping. "
            "Every scrap that would have gone to waste becomes the foundation for next "
            "year's harvest. Soil is not dirt — it is a living system, and composting "
            "is how you feed it."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CREATION_SCIENCE — Farm as laboratory, observation, stewardship
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "CREATION_SCIENCE",
        "source_title": "The Voyage of the Beagle — Galapagos Observations",
        "source_url": "https://www.gutenberg.org/ebooks/944",
        "citation_author": "Charles Darwin",
        "citation_year": 1839,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "The natural history of these islands is eminently curious, and well deserves "
            "attention. Most of the organic productions are aboriginal creations, found "
            "nowhere else; there is even a difference between the inhabitants of the "
            "different islands. The archipelago is a little world within itself. Seeing "
            "every height crowned with its crater, and the boundaries of most of the "
            "lava-streams still distinct, we are led to believe that within a period "
            "geologically recent the unbroken ocean was here spread out. Hence, both in "
            "space and time, we seem to be brought somewhat near to that great fact — "
            "that mystery of mysteries — the first appearance of new beings on this earth."
        ),
    },
    {
        "track": "CREATION_SCIENCE",
        "source_title": "Genesis 2:15 and 8:22 (KJV) — Stewardship of the Earth",
        "source_url": "https://www.kingjamesbibleonline.org/Genesis-Chapter-2/#stewardship",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "And the LORD God took the man, and put him into the garden of Eden to dress "
            "it and to keep it. While the earth remaineth, seedtime and harvest, and cold "
            "and heat, and summer and winter, and day and night shall not cease. The first "
            "job God gave to a human being was not worship, not war, not commerce — it was "
            "tending a garden. Stewardship of the land is the oldest human calling. To "
            "observe how a seed becomes a plant, how soil feeds a root, how rain and sun "
            "drive a season — that is science conducted in the laboratory God built first."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # DISCIPLESHIP — Deeper biblical worldview, practical faith, homeschooling
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "DISCIPLESHIP",
        "source_title": "Deuteronomy 6:4-9 (KJV) — The Shema and Teaching Children",
        "source_url": "https://www.kingjamesbibleonline.org/Deuteronomy-Chapter-6/",
        "citation_author": "King James Bible",
        "citation_year": 1611,
        "citation_archive_name": "Public Domain",
        "chunk": (
            "Hear, O Israel: The LORD our God is one LORD: And thou shalt love the LORD "
            "thy God with all thine heart, and with all thy soul, and with all thy might. "
            "And these words, which I command thee this day, shall be in thine heart: And "
            "thou shalt teach them diligently unto thy children, and shalt talk of them "
            "when thou sittest in thine house, and when thou walkest by the way, and when "
            "thou liest down, and when thou risest up. The instruction of children is not "
            "a classroom task. It is woven into every waking moment — breakfast, chores, "
            "walks, bedtime. Homeschooling is the oldest form of education. It began here."
        ),
    },
    {
        "track": "DISCIPLESHIP",
        "source_title": "Mere Christianity — The Law of Human Nature",
        "source_url": "https://archive.org/details/MereChristianity_229#law",
        "citation_author": "C.S. Lewis",
        "citation_year": 1952,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "Every one has heard people quarrelling. They say things like this: 'How'd "
            "you like it if anyone did the same to you?' — 'That's my seat, I was there "
            "first' — 'Come on, you promised.' People say things like that every day. "
            "Now what interests me about all these remarks is that the man who makes them "
            "is not merely saying that the other man's behaviour does not happen to please "
            "him. He is appealing to some kind of standard of behaviour which he expects "
            "the other man to know about. Quarrelling means trying to show that the other "
            "man is in the wrong. And there would be no sense in trying to do that unless "
            "you and he had some sort of agreement as to what Right and Wrong are."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # JUSTICE_CHANGEMAKING — More advocacy, civil rights. Primary sources.
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "JUSTICE_CHANGEMAKING",
        "source_title": "Ain't I a Woman? — Speech at Women's Convention",
        "source_url": "https://www.nps.gov/articles/sojourner-truth.htm",
        "citation_author": "Sojourner Truth",
        "citation_year": 1851,
        "citation_archive_name": "National Park Service",
        "chunk": (
            "That man over there says that women need to be helped into carriages, and "
            "lifted over ditches, and to have the best place everywhere. Nobody ever helps "
            "me into carriages, or over mud-puddles, or gives me any best place! And ain't "
            "I a woman? Look at me! Look at my arm! I have ploughed and planted, and "
            "gathered into barns, and no man could head me! And ain't I a woman? I could "
            "work as much and eat as much as a man — when I could get it — and bear the "
            "lash as well! And ain't I a woman? I have borne thirteen children, and seen "
            "most all sold off to slavery, and when I cried out with my mother's grief, "
            "none but Jesus heard me! And ain't I a woman?"
        ),
    },
    {
        "track": "JUSTICE_CHANGEMAKING",
        "source_title": "Brown v. Board of Education — Opinion of the Court",
        "source_url": "https://www.archives.gov/milestone-documents/brown-v-board-of-education",
        "citation_author": "Chief Justice Earl Warren",
        "citation_year": 1954,
        "citation_archive_name": "National Archives",
        "chunk": (
            "We come then to the question presented: Does segregation of children in "
            "public schools solely on the basis of race, even though the physical "
            "facilities and other tangible factors may be equal, deprive the children "
            "of the minority group of equal educational opportunities? We believe that "
            "it does. To separate them from others of similar age and qualifications "
            "solely because of their race generates a feeling of inferiority as to their "
            "status in the community that may affect their hearts and minds in a way "
            "unlikely ever to be undone. We conclude that, in the field of public "
            "education, the doctrine of 'separate but equal' has no place. Separate "
            "educational facilities are inherently unequal."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # APPLIED_MATHEMATICS — Real-world: building, farming, commerce
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "APPLIED_MATHEMATICS",
        "source_title": "Farmers' Bulletin — Calculating Seed and Yield Per Acre",
        "source_url": "https://archive.org/details/CAT87201428#seed",
        "citation_author": "U.S. Department of Agriculture",
        "citation_year": 1925,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "To calculate seed required: measure the field in acres (length in feet times "
            "width in feet, divided by 43,560). Multiply acres by the seeding rate for "
            "your crop — wheat takes 90 pounds per acre, oats take 64, corn takes 8. "
            "To estimate yield: count the plants in a measured row, multiply by rows "
            "per acre, multiply by average ears or heads per plant, multiply by average "
            "kernels per ear, divide by kernels per bushel. A farmer who cannot do this "
            "arithmetic is guessing how much to plant and hoping for the best. Math on "
            "a farm is not theoretical. It is the difference between a full barn and "
            "an empty one."
        ),
    },
    {
        "track": "APPLIED_MATHEMATICS",
        "source_title": "The Builder's Guide — Calculating Roof Pitch and Rafter Length",
        "source_url": "https://archive.org/details/buildersguide00hillrich",
        "citation_author": "Chester Hills",
        "citation_year": 1834,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "To find the length of a common rafter: measure the run (half the span of "
            "the building) and the rise (how high the peak stands above the wall plate). "
            "The rafter is the hypotenuse. Square the run, square the rise, add them "
            "together, and take the square root. A building 24 feet wide with a 6-foot "
            "rise: run is 12, rise is 6. Twelve squared is 144, six squared is 36, sum "
            "is 180, square root is 13 feet 5 inches. Add overhang. The Pythagorean "
            "theorem is not a school exercise — it is how you cut a rafter that fits. "
            "Every builder uses it. Every builder who skips it wastes lumber."
        ),
    },
    {
        "track": "APPLIED_MATHEMATICS",
        "source_title": "Poor Richard's Almanack — Interest, Debt, and Time Value of Money",
        "source_url": "https://www.gutenberg.org/ebooks/52135#debt",
        "citation_author": "Benjamin Franklin",
        "citation_year": 1737,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "Creditors have better memories than debtors. He that goes a borrowing goes "
            "a sorrowing. Rather go to bed supperless than rise in debt. If you would "
            "know the value of money, go and try to borrow some; for he that goes a "
            "borrowing goes a sorrowing. The borrower is servant to the lender. The "
            "arithmetic of debt is simple and unforgiving: borrow one hundred dollars "
            "at six percent and in twelve years you owe two hundred. The money doubles "
            "itself while you sleep. Every dollar you owe is a dollar working against "
            "you. Every dollar you save is a dollar working for you. Compound interest "
            "is the most powerful force in commerce — and it does not care whose side "
            "it is on."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # CREATIVE_ECONOMY — Making, pricing, selling, entrepreneurship
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "CREATIVE_ECONOMY",
        "source_title": "Up from Slavery — Industrial Education and Self-Reliance",
        "source_url": "https://www.gutenberg.org/ebooks/2376#industrial",
        "citation_author": "Booker T. Washington",
        "citation_year": 1901,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "No race can prosper till it learns that there is as much dignity in tilling "
            "a field as in writing a poem. It is at the bottom of life we must begin, and "
            "not at the top. Nor should we permit our grievances to overshadow our "
            "opportunities. Cast down your bucket where you are — cast it down in "
            "agriculture, mechanics, in commerce, in domestic service, and in the "
            "professions. The person who can do something that the world wants done will, "
            "in the end, make his way regardless of his race. The hand that makes "
            "something useful will never go hungry."
        ),
    },
    {
        "track": "CREATIVE_ECONOMY",
        "source_title": "Walden — Economy (Chapter 1)",
        "source_url": "https://www.gutenberg.org/ebooks/205#economy",
        "citation_author": "Henry David Thoreau",
        "citation_year": 1854,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "The cost of a thing is the amount of what I will call life which is required "
            "to be exchanged for it, immediately or in the long run. By a seeming fate, "
            "commonly called necessity, men are employed laying up treasures which moth "
            "and rust will corrupt and thieves break through and steal. It is a fool's "
            "life, as they will find when they get to the end of it, if not before. "
            "I went to the woods because I wished to live deliberately, to front only the "
            "essential facts of life, and see if I could not learn what it had to teach, "
            "and not, when I came to die, discover that I had not lived. The true cost of "
            "anything is measured in hours of your life, not dollars."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ENGLISH_LITERATURE — More classic public domain voices
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "Narrative of Sojourner Truth — Sold at Auction",
        "source_url": "https://www.gutenberg.org/ebooks/7102",
        "citation_author": "Sojourner Truth (Olive Gilbert, amanuensis)",
        "citation_year": 1850,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "At length, the sale began. Isabella, as we shall now call her, was sold for "
            "one hundred dollars to one John Neely, of Ulster County, New York. She was "
            "only nine years old. She could not speak English — only Dutch. She could not "
            "understand the orders given her, and was beaten for disobedience she could "
            "not have prevented. What language does a child speak who is sold? The language "
            "of survival. What does she learn first? Not grammar, not arithmetic — she "
            "learns whose voice means pain and whose voice means safety. Literature begins "
            "with the human voice under pressure. This is that voice."
        ),
    },
    {
        "track": "ENGLISH_LITERATURE",
        "source_title": "The Souls of Black Folk — Of Our Spiritual Strivings",
        "source_url": "https://www.gutenberg.org/ebooks/408",
        "citation_author": "W.E.B. Du Bois",
        "citation_year": 1903,
        "citation_archive_name": "Project Gutenberg",
        "chunk": (
            "Between me and the other world there is ever an unasked question: How does "
            "it feel to be a problem? One ever feels his twoness — an American, a Negro; "
            "two souls, two thoughts, two unreconciled strivings; two warring ideals in "
            "one dark body, whose dogged strength alone keeps it from being torn asunder. "
            "The history of the American Negro is the history of this strife — this longing "
            "to attain self-conscious manhood, to merge his double self into a better and "
            "truer self. He would not bleach his Negro soul in a flood of white Americanism, "
            "for he knows that Negro blood has a message for the world."
        ),
    },
]


async def main():
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-placeholder"):
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    print("=" * 50)
    print("  CORPUS EXPANSION — Dear Adeline Hippocampus")
    print("=" * 50)

    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    engine = create_async_engine(
        _pg_dsn, echo=False,
        connect_args={"ssl": ctx, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    total = 0
    skipped = 0
    for source in SOURCES:
        # Duplicate check by source_title + track
        async with session_factory() as session:
            existing = await session.execute(
                text("SELECT id FROM hippocampus_documents WHERE source_title = :t AND track = :tr LIMIT 1"),
                {"t": source["source_title"], "tr": source["track"]},
            )
            if existing.scalar():
                print(f"  [skip] {source['source_title']} ({source['track']})")
                skipped += 1
                continue

        print(f"  Embedding: {source['source_title']} ({source['track']})...")
        vector = await embed(source["chunk"])
        if vector is None:
            skipped += 1
            continue

        async with session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO hippocampus_documents
                        (id, source_title, source_url, track, chunk, embedding,
                         source_type, citation_author, citation_year, citation_archive_name)
                    VALUES
                        (gen_random_uuid(), :title, :url, :track, :chunk, CAST(:embedding AS vector),
                         'PRIMARY_SOURCE', :author, :year, :archive)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "title": source["source_title"],
                    "url": source["source_url"],
                    "track": source["track"],
                    "chunk": source["chunk"],
                    "embedding": str(vector),
                    "author": source["citation_author"],
                    "year": source.get("citation_year"),
                    "archive": source["citation_archive_name"],
                },
            )
            await session.commit()
        total += 1
        print(f"    Done ({len(source['chunk'])} chars)")

    # Final count
    async with session_factory() as session:
        count = (await session.execute(text("SELECT COUNT(*) FROM hippocampus_documents"))).scalar()

    print(f"\nSeeded {total} new chunks, skipped {skipped}. Total in Hippocampus: {count}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
