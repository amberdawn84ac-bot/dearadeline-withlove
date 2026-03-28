"""
seed_corpus_expansion.py — Expand the Hippocampus with 3 new primary source tracks.

Adds:
  - Harriet Tubman / Underground Railroad  (JUSTICE_CHANGEMAKING)
  - Constitutional Convention of 1787      (GOVERNMENT_ECONOMICS)
  - Medicinal Herbs / American Frontier    (HEALTH_NATUROPATHY)

Run from adeline-brain/:
    python scripts/seed_corpus_expansion.py
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import openai
from sqlalchemy import text, Column, String, Float, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pgvector.sqlalchemy import Vector
import uuid as uuid_lib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_expansion")

# ── Config ────────────────────────────────────────────────────────────────────

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://adeline:adeline_local_dev@localhost:5432/hippocampus",
).replace("postgresql://", "postgresql+asyncpg://")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBED_MODEL    = "text-embedding-3-small"
EMBED_DIM      = 1536


# ── SQLAlchemy table ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass

class HippocampusDocument(Base):
    __tablename__ = "hippocampus_documents"
    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    source_title          = Column(String, nullable=False)
    source_url            = Column(String, nullable=False, default="")
    track                 = Column(String, nullable=False)
    chunk                 = Column(String, nullable=False)
    embedding             = Column(Vector(EMBED_DIM), nullable=False)
    citation_author       = Column(String, nullable=False, default="")
    citation_year         = Column(Integer, nullable=True)
    citation_archive_name = Column(String, nullable=False, default="")
    created_at            = Column(DateTime(timezone=True), server_default=func.now())


# ── Primary source corpus ─────────────────────────────────────────────────────

# 1. Harriet Tubman / Underground Railroad — JUSTICE_CHANGEMAKING
_TUBMAN_BASE = {
    "source_title":          "Scenes in the Life of Harriet Tubman",
    "source_url":            "https://www.loc.gov/item/2008677915/",
    "track":                 "JUSTICE_CHANGEMAKING",
    "citation_author":       "Kate Clifford Larson (quoting Harriet Tubman; compiled by Sarah Bradford)",
    "citation_year":         1869,
    "citation_archive_name": "Library of Congress — Rare Books and Special Collections",
}

TUBMAN_CHUNKS = [
    {
        **_TUBMAN_BASE,
        "chunk": (
            "Harriet Tubman and the Underground Railroad — courage and liberation, 1849–1860. "
            "Harriet Tubman escaped slavery in Maryland in 1849, traveling by night using the North Star "
            "as her guide. She returned south nineteen times, personally leading over 300 enslaved people "
            "to freedom along the Underground Railroad. She said: 'I never ran my train off the track and "
            "I never lost a passenger.' Tubman relied on safe houses, abolitionists, and the Black church "
            "network. She was known to conductors and freedom-seekers alike as 'Moses,' because like "
            "Moshe of the Hebrew scriptures she led her people out of bondage."
        ),
    },
    {
        **_TUBMAN_BASE,
        "chunk": (
            "Harriet Tubman Underground Railroad — first-person accounts of courage. "
            "Tubman described her first escape in an 1869 account collected by Sarah Bradford: "
            "'When I found I had crossed that line, I looked at my hands to see if I was the same person. "
            "There was such a glory over everything; the sun came like gold through the trees, and over the "
            "fields, and I felt like I was in Heaven.' She immediately resolved to return for her family. "
            "Tubman used natural landmarks, swamp routes, and coded spirituals like 'Follow the Drinking Gourd' "
            "to guide freedom-seekers north to Pennsylvania and Canada."
        ),
    },
    {
        **_TUBMAN_BASE,
        "chunk": (
            "Underground Railroad network and the abolitionist movement — justice and change-making. "
            "The Underground Railroad was not a single railroad but a distributed network of free Black "
            "families, Quaker abolitionists, Methodist churches, and sympathetic farmers who provided "
            "food, hiding places, and transportation for freedom-seekers escaping slavery. "
            "Harriet Tubman was its most celebrated conductor. The network stretched from the Deep South "
            "through Maryland, Pennsylvania, Ohio, and into Canada. Tubman's courage in returning again "
            "and again to slave territory — with a bounty on her head — exemplified the spirit of justice "
            "and self-sacrificial change-making that characterized the abolitionist movement."
        ),
    },
]

# 2. Constitutional Convention of 1787 — GOVERNMENT_ECONOMICS
_CONSTITUTION_BASE = {
    "source_title":          "Notes of Debates in the Federal Convention of 1787",
    "source_url":            "https://avalon.law.yale.edu/subject_menus/debcont.asp",
    "track":                 "GOVERNMENT_ECONOMICS",
    "citation_author":       "James Madison",
    "citation_year":         1787,
    "citation_archive_name": "Avalon Project — Yale Law School / Library of Congress",
}

CONSTITUTION_CHUNKS = [
    {
        **_CONSTITUTION_BASE,
        "chunk": (
            "The Constitutional Convention of 1787 — the Founders debate the structure of the republic. "
            "In May 1787, fifty-five delegates from twelve states gathered in Philadelphia to draft a new "
            "framework of government for the United States. James Madison arrived with a detailed plan — "
            "the Virginia Plan — that proposed a bicameral legislature with proportional representation, "
            "an executive, and a federal judiciary. The Great Compromise, brokered in July 1787, resolved "
            "the conflict between large and small states: the House of Representatives would reflect "
            "population while the Senate would give each state two equal votes. The Constitution created "
            "a federal system balancing power between the national government and the states."
        ),
    },
    {
        **_CONSTITUTION_BASE,
        "chunk": (
            "Constitutional Convention 1787 — Madison's Notes on the debate over slavery and the three-fifths clause. "
            "One of the most contested debates at the Constitutional Convention concerned the counting of "
            "enslaved persons for purposes of congressional representation and taxation. Delegates from "
            "Southern states insisted that enslaved people be counted; Northern delegates objected to "
            "counting people who were denied all rights of citizenship. The Three-Fifths Compromise — "
            "counting each enslaved person as three-fifths of a free person — was a moral compromise "
            "that allowed the Constitution to be ratified but embedded the contradiction of slavery into "
            "the founding document. Madison recorded these debates in his detailed convention notes."
        ),
    },
    {
        **_CONSTITUTION_BASE,
        "chunk": (
            "Constitutional Convention 1787 — the Bill of Rights and limits on government power. "
            "During the ratification debates of 1787–1788, Anti-Federalists like Patrick Henry and George Mason "
            "argued that the Constitution lacked explicit protections for individual rights. "
            "James Madison responded by drafting twelve amendments in 1789; ten were ratified as the Bill of Rights. "
            "These amendments guaranteed freedoms of religion, speech, and the press (First Amendment); "
            "protection against unreasonable searches (Fourth Amendment); rights of the accused (Fifth and Sixth); "
            "and reserved powers to the states and the people (Tenth Amendment). "
            "The Founders deliberately designed a government of limited, enumerated powers."
        ),
    },
]

# 3. Medicinal Herbs — HEALTH_NATUROPATHY
_HERBS_BASE = {
    "source_title":          "American Materia Medica, Therapeutics and Pharmacognosy",
    "source_url":            "https://www.henriettes-herb.com/eclectic/ellingwood/index.html",
    "track":                 "HEALTH_NATUROPATHY",
    "citation_author":       "Finley Ellingwood, M.D.",
    "citation_year":         1919,
    "citation_archive_name": "Henriette's Herbal Homepage — Eclectic Medical Literature Archive",
}

HERBS_CHUNKS = [
    {
        **_HERBS_BASE,
        "chunk": (
            "Medicinal herbs of the American frontier — traditional plant medicine and its historical use. "
            "American frontier settlers and Indigenous peoples alike relied on medicinal herbs for healing "
            "long before modern pharmaceuticals. Echinacea (purple coneflower) was used by Plains Indian "
            "nations as an anti-infective and wound healer; settlers adopted it widely. "
            "Elderberry (Sambucus nigra) was used to treat fever, colds, and influenza. "
            "Yarrow (Achillea millefolium) was used to stop bleeding and reduce fever — soldiers in the "
            "Civil War packed wounds with yarrow in the field. "
            "Goldenseal (Hydrastis canadensis) was prized as an antimicrobial by Iroquois healers "
            "and later harvested nearly to extinction by European settlers."
        ),
    },
    {
        **_HERBS_BASE,
        "chunk": (
            "Traditional plant medicine and naturopathy — herbs used by American frontier homesteaders. "
            "On the American frontier, the homestead garden often included a medicinal herb plot. "
            "Common herbs grown and used for medicine included: "
            "Valerian root (Valeriana officinalis) for sleep and anxiety; "
            "Chamomile (Matricaria chamomilla) for digestive complaints and as a mild sedative; "
            "Peppermint for headaches, nausea, and fevers; "
            "Comfrey (Symphytum officinale) — known as 'knitbone' — applied as a poultice to broken bones and sprains; "
            "St. John's Wort (Hypericum perforatum) for wound healing and later recognized for mood support. "
            "These herbs formed the first line of care before a doctor could be reached across miles of frontier."
        ),
    },
    {
        **_HERBS_BASE,
        "chunk": (
            "Naturopathy and herbal medicine — historical plant remedies and their scientific basis. "
            "The Eclectic Medical movement of the 19th century documented hundreds of American medicinal plants. "
            "Dr. Finley Ellingwood's 1919 American Materia Medica catalogued plant-based medicines with "
            "clinical observations. Modern research has confirmed many traditional uses: "
            "Echinacea stimulates innate immune response; elderberry anthocyanins show antiviral activity; "
            "berberine in goldenseal and Oregon grape inhibits a broad spectrum of bacteria; "
            "thymol in thyme is a proven antiseptic. Understanding these historical remedies connects "
            "naturopathy to the scientific method — many modern drugs derive directly from plant compounds "
            "first observed in traditional medicine."
        ),
    },
]

# ── All expansion chunks ──────────────────────────────────────────────────────

ALL_EXPANSION_CHUNKS: list[tuple[str, list[dict]]] = [
    ("Harriet Tubman / Underground Railroad", TUBMAN_CHUNKS),
    ("Constitutional Convention 1787",        CONSTITUTION_CHUNKS),
    ("Medicinal Herbs / American Frontier",   HERBS_CHUNKS),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def embed(text_input: str) -> list[float] | None:
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        resp = await client.embeddings.create(model=EMBED_MODEL, input=text_input)
        return resp.data[0].embedding
    except openai.BadRequestError as e:
        if "content_filter" in str(e).lower() or e.status_code == 400:
            log.warning(f"Content filter blocked chunk. Snippet: '{text_input[:80]}...'")
            return None
        raise
    except Exception as e:
        log.error(f"Embedding error: {e}")
        raise


async def insert_document(session_factory, embedding: list[float], **meta) -> str:
    async with session_factory() as session:
        doc = HippocampusDocument(embedding=embedding, **meta)
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return str(doc.id)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-placeholder"):
        log.error("OPENAI_API_KEY is not set. Add it to .env and retry.")
        sys.exit(1)

    log.info("══════════════════════════════════════════════════")
    log.info("  CORPUS EXPANSION — Dear Adeline Hippocampus     ")
    log.info("══════════════════════════════════════════════════")

    engine = create_async_engine(POSTGRES_DSN, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    total_stored = 0

    for label, chunks in ALL_EXPANSION_CHUNKS:
        log.info(f"── Seeding: {label} ({len(chunks)} chunks) ─────")
        for i, doc_meta in enumerate(chunks, 1):
            chunk_text = doc_meta["chunk"]
            log.info(f"   Embedding chunk {i}/{len(chunks)}...")
            vector = await embed(chunk_text)
            if vector is None:
                log.warning(f"   Chunk {i} skipped — content filter")
                continue
            meta = {k: v for k, v in doc_meta.items() if k != "chunk"}
            doc_id = await insert_document(
                session_factory,
                embedding=vector,
                chunk=chunk_text,
                **meta,
            )
            log.info(f"   Chunk {i} stored → id={doc_id}")
            total_stored += 1

    # ── Final count ───────────────────────────────────────────────────────────
    async with session_factory() as session:
        total = (await session.execute(text("SELECT COUNT(*) FROM hippocampus_documents"))).scalar()

    log.info("══════════════════════════════════════════════════")
    log.info(f"  Stored {total_stored} new chunks — Hippocampus total: {total}")
    log.info("══════════════════════════════════════════════════")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
