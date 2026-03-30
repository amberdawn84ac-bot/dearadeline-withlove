#!/usr/bin/env python3
"""
Seed the 8-Track GraphRAG knowledge graph.

Creates:
  - 8 Track nodes (one per 8-Track Constitution track)
  - ~64 Concept nodes (8 per track, spanning k-2 through 9-12)
  - PREREQUISITE_OF edges encoding the learning dependency graph
  - CROSS_TRACK_LINK edges encoding thematic connections between tracks
    (e.g., HOMESTEADING soil science ↔ CREATION_SCIENCE biology)

Usage:
    cd adeline-brain
    python scripts/seed_knowledge_graph.py

Requires:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars (or defaults from neo4j_client.py)
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Add parent to path so app imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.connections.neo4j_client import neo4j_client
from app.connections.knowledge_graph import (
    apply_schema_constraints,
    seed_tracks,
    upsert_concept,
    add_prerequisite,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ── Concept definitions: (id, title, description, track, difficulty, standard_code, grade_band) ──

CONCEPTS = [
    # ── TRUTH_HISTORY ──────────────────────────────────────────────────────────
    ("th-001", "Oral Tradition & Family History",
     "Understanding how stories pass through generations before written records.",
     "TRUTH_HISTORY", "EMERGING", "OK-US-K.1", "k2"),

    ("th-002", "Primary vs. Secondary Sources",
     "Distinguishing direct accounts from interpretations of events.",
     "TRUTH_HISTORY", "DEVELOPING", "OK-US-3.1", "35"),

    ("th-003", "Bias and Perspective in Historical Sources",
     "Identifying author perspective, motive, and potential bias in documents.",
     "TRUTH_HISTORY", "EXPANDING", "OK-US-6.2", "68"),

    ("th-004", "The Dawes Act and Indigenous Land Loss",
     "How the 1887 Dawes Act fragmented tribal sovereignty and transferred land.",
     "TRUTH_HISTORY", "EXPANDING", "OK-US-8.3", "68"),

    ("th-005", "Historiography: Who Writes History?",
     "Examining how historical narratives are constructed, contested, and revised.",
     "TRUTH_HISTORY", "MASTERING", "OK-US-11.1", "912"),

    ("th-006", "Propaganda and Media Manipulation",
     "Analyzing techniques used to shape public opinion through selective narrative.",
     "TRUTH_HISTORY", "MASTERING", "OK-US-11.3", "912"),

    ("th-007", "The Oklahoma Land Run: Multiple Perspectives",
     "Examining the 1889 Land Run from Settler, Freedmen, and Indigenous viewpoints.",
     "TRUTH_HISTORY", "DEVELOPING", "OK-US-4.2", "35"),

    ("th-008", "Witness Protocol: Evaluating Source Credibility",
     "Applying a structured framework to verify historical claims against primary sources.",
     "TRUTH_HISTORY", "MASTERING", "OK-US-12.1", "912"),

    # ── CREATION_SCIENCE ───────────────────────────────────────────────────────
    ("cs-001", "Observation and the Scientific Method",
     "Using the five senses and direct observation to ask and answer questions.",
     "CREATION_SCIENCE", "EMERGING", "OK-SC-K.1", "k2"),

    ("cs-002", "Plant Life Cycles and Seeds",
     "Understanding germination, growth, and reproduction in plants.",
     "CREATION_SCIENCE", "EMERGING", "OK-SC-1.3", "k2"),

    ("cs-003", "Ecosystems and Food Webs",
     "How producers, consumers, and decomposers interact in a balanced system.",
     "CREATION_SCIENCE", "DEVELOPING", "OK-SC-4.2", "35"),

    ("cs-004", "Cell Biology: Building Blocks of Life",
     "Structure and function of plant and animal cells; organelles.",
     "CREATION_SCIENCE", "EXPANDING", "OK-SC-7.1", "68"),

    ("cs-005", "Genetics and Heredity",
     "How traits are passed from parent to offspring via DNA.",
     "CREATION_SCIENCE", "EXPANDING", "OK-SC-7.3", "68"),

    ("cs-006", "Intelligent Design: Evidence from Biochemistry",
     "Examining irreducible complexity and specified information as evidence of design.",
     "CREATION_SCIENCE", "MASTERING", "OK-SC-B.4", "912"),

    ("cs-007", "Earth Science: Geology and Landforms",
     "Formation of landforms, rock cycles, and geological time.",
     "CREATION_SCIENCE", "DEVELOPING", "OK-SC-4.4", "35"),

    ("cs-008", "Chemistry: Matter and Its Properties",
     "States of matter, elements, compounds, and chemical change.",
     "CREATION_SCIENCE", "EXPANDING", "OK-SC-8.1", "68"),

    # ── HOMESTEADING ───────────────────────────────────────────────────────────
    ("hs-001", "Garden Basics: Soil, Seeds, and Water",
     "Starting a garden by understanding the role of soil health, seeds, and watering.",
     "HOMESTEADING", "EMERGING", "OK-AG-K.1", "k2"),

    ("hs-002", "Composting and Soil Amendments",
     "Building healthy soil through composting kitchen scraps and organic matter.",
     "HOMESTEADING", "DEVELOPING", "OK-AG-3.2", "35"),

    ("hs-003", "Soil pH and Crop Selection",
     "Measuring soil pH and matching crops to soil conditions for optimal yield.",
     "HOMESTEADING", "EXPANDING", "OK-AG-7.4", "68"),

    ("hs-004", "Permaculture Design Principles",
     "Applying observation, edge effect, and stacking functions to land design.",
     "HOMESTEADING", "EXPANDING", "OK-AG-8.1", "68"),

    ("hs-005", "Food Preservation: Canning and Fermentation",
     "Water-bath canning, lacto-fermentation, and dehydrating for long-term food storage.",
     "HOMESTEADING", "DEVELOPING", "OK-AG-5.3", "35"),

    ("hs-006", "Animal Husbandry Fundamentals",
     "Caring for chickens, goats, or cattle; feed, housing, and health basics.",
     "HOMESTEADING", "DEVELOPING", "OK-AG-4.1", "35"),

    ("hs-007", "Regenerative Agriculture and Land Management",
     "No-till farming, cover crops, and holistic grazing for soil restoration.",
     "HOMESTEADING", "MASTERING", "OK-AG-11.2", "912"),

    ("hs-008", "Water Systems: Rainwater Harvesting and Irrigation",
     "Designing water-catchment systems for drought resilience.",
     "HOMESTEADING", "MASTERING", "OK-AG-10.3", "912"),

    # ── GOVERNMENT_ECONOMICS ───────────────────────────────────────────────────
    ("ge-001", "Community Rules and Why We Have Them",
     "Why communities create rules, and how families and classrooms govern themselves.",
     "GOVERNMENT_ECONOMICS", "EMERGING", "OK-SS-K.2", "k2"),

    ("ge-002", "Local Government: How Our Town Works",
     "Roles of mayor, city council, and local services.",
     "GOVERNMENT_ECONOMICS", "DEVELOPING", "OK-SS-3.4", "35"),

    ("ge-003", "Budgeting and Personal Finance",
     "Income, expenses, savings, and the value of avoiding debt.",
     "GOVERNMENT_ECONOMICS", "DEVELOPING", "OK-SS-4.5", "35"),

    ("ge-004", "The U.S. Constitution and Separation of Powers",
     "Three branches of government and the design of checks and balances.",
     "GOVERNMENT_ECONOMICS", "EXPANDING", "OK-SS-8.2", "68"),

    ("ge-005", "Monetary Policy and the Federal Reserve",
     "How the Fed controls interest rates and money supply; inflation effects.",
     "GOVERNMENT_ECONOMICS", "MASTERING", "OK-SS-12.3", "912"),

    ("ge-006", "Regulatory Capture and Crony Capitalism",
     "When regulatory agencies serve industry interests over public interest.",
     "GOVERNMENT_ECONOMICS", "MASTERING", "OK-SS-12.4", "912"),

    ("ge-007", "Supply, Demand, and Free Markets",
     "How prices are set by voluntary exchange; market signals.",
     "GOVERNMENT_ECONOMICS", "EXPANDING", "OK-SS-7.3", "68"),

    ("ge-008", "Taxation: Types, Purpose, and Critique",
     "Income, property, sales taxes; how taxation funds (and distorts) the economy.",
     "GOVERNMENT_ECONOMICS", "EXPANDING", "OK-SS-6.4", "68"),

    # ── JUSTICE_CHANGEMAKING ───────────────────────────────────────────────────
    ("jc-001", "Fairness and Sharing in Community",
     "Basic concepts of fair treatment and helping others in a community.",
     "JUSTICE_CHANGEMAKING", "EMERGING", "OK-SS-K.3", "k2"),

    ("jc-002", "Oklahoma History: The Five Civilized Tribes",
     "Sovereignty, culture, and resilience of the Cherokee, Choctaw, Chickasaw, Creek, and Seminole Nations.",
     "JUSTICE_CHANGEMAKING", "DEVELOPING", "OK-US-5.1", "35"),

    ("jc-003", "The Trail of Tears",
     "Forced removal of the Five Tribes from southeastern homelands to Indian Territory.",
     "JUSTICE_CHANGEMAKING", "DEVELOPING", "OK-US-5.3", "35"),

    ("jc-004", "Systemic Injustice: Structural vs. Individual Racism",
     "Distinguishing interpersonal prejudice from policies that produce unequal outcomes.",
     "JUSTICE_CHANGEMAKING", "EXPANDING", "OK-SS-8.5", "68"),

    ("jc-005", "The Tulsa Race Massacre of 1921",
     "The destruction of Greenwood District ('Black Wall Street') and its legacy.",
     "JUSTICE_CHANGEMAKING", "EXPANDING", "OK-US-8.4", "68"),

    ("jc-006", "Advocacy and Community Organizing",
     "How to research an issue, build coalitions, and petition decision-makers.",
     "JUSTICE_CHANGEMAKING", "MASTERING", "OK-SS-11.2", "912"),

    ("jc-007", "Grassroots vs. Institutional Change",
     "Comparing bottom-up social movements with top-down policy reform.",
     "JUSTICE_CHANGEMAKING", "MASTERING", "OK-SS-12.2", "912"),

    ("jc-008", "Restorative Justice Principles",
     "Repairing harm through accountability, community, and reconciliation.",
     "JUSTICE_CHANGEMAKING", "EXPANDING", "OK-SS-9.3", "68"),

    # ── DISCIPLESHIP ──────────────────────────────────────────────────────────
    ("ds-001", "God's Love and Our Identity",
     "Understanding that we are created in God's image and loved unconditionally.",
     "DISCIPLESHIP", "EMERGING", "DISC-K.1", "k2"),

    ("ds-002", "Scripture Memory and the Psalms",
     "Memorizing key scriptures; introduction to the poetry of the Psalms.",
     "DISCIPLESHIP", "DEVELOPING", "DISC-3.2", "35"),

    ("ds-003", "Biblical Worldview: Creation, Fall, Redemption, Restoration",
     "The four-act structure of the biblical narrative as a lens on all of life.",
     "DISCIPLESHIP", "DEVELOPING", "DISC-4.1", "35"),

    ("ds-004", "Apologetics: Making a Defense of the Faith",
     "Evidential and presuppositional approaches to defending Christian truth claims.",
     "DISCIPLESHIP", "MASTERING", "DISC-11.1", "912"),

    ("ds-005", "Cultural Discernment: Analyzing Media and Worldviews",
     "Applying biblical wisdom to evaluate art, entertainment, and news.",
     "DISCIPLESHIP", "EXPANDING", "DISC-7.2", "68"),

    ("ds-006", "Systematic Theology: Doctrines of God",
     "Study of God's attributes: omniscience, omnipotence, holiness, love.",
     "DISCIPLESHIP", "MASTERING", "DISC-12.1", "912"),

    ("ds-007", "Prayer and Spiritual Disciplines",
     "Developing a practice of prayer, fasting, Scripture reading, and community.",
     "DISCIPLESHIP", "DEVELOPING", "DISC-5.1", "35"),

    ("ds-008", "Ethics: What Is Right and How Do We Know?",
     "Introduction to moral philosophy from a Christian epistemological framework.",
     "DISCIPLESHIP", "MASTERING", "DISC-10.1", "912"),

    # ── HEALTH_NATUROPATHY ────────────────────────────────────────────────────
    ("hn-001", "Healthy Habits: Sleep, Food, and Movement",
     "Building daily routines around sleep, nutrition, and physical activity.",
     "HEALTH_NATUROPATHY", "EMERGING", "OK-HE-K.1", "k2"),

    ("hn-002", "Nutrition Basics: Macronutrients and Micronutrients",
     "Understanding proteins, carbohydrates, fats, vitamins, and minerals.",
     "HEALTH_NATUROPATHY", "DEVELOPING", "OK-HE-4.2", "35"),

    ("hn-003", "Herbal Medicine: Common Medicinal Plants",
     "Uses, preparations, and safety of common herbs (chamomile, echinacea, elderberry).",
     "HEALTH_NATUROPATHY", "DEVELOPING", "OK-HE-5.3", "35"),

    ("hn-004", "The Gut Microbiome and Digestive Health",
     "How beneficial bacteria influence immunity, mood, and overall health.",
     "HEALTH_NATUROPATHY", "EXPANDING", "OK-HE-7.4", "68"),

    ("hn-005", "Naturopathic Principles: Vis Medicatrix Naturae",
     "The healing power of nature; the body's innate ability to self-heal.",
     "HEALTH_NATUROPATHY", "EXPANDING", "OK-HE-8.2", "68"),

    ("hn-006", "Functional Medicine: Root Cause Analysis",
     "Moving beyond symptom management to identify underlying causes of disease.",
     "HEALTH_NATUROPATHY", "MASTERING", "OK-HE-11.1", "912"),

    ("hn-007", "Anatomy and Physiology: Body Systems Overview",
     "Structure and function of the major body systems: nervous, endocrine, circulatory.",
     "HEALTH_NATUROPATHY", "EXPANDING", "OK-SC-7.2", "68"),

    ("hn-008", "Mental Health and Emotional Resilience",
     "Understanding stress, grief, and building emotional regulation practices.",
     "HEALTH_NATUROPATHY", "DEVELOPING", "OK-HE-6.1", "35"),

    # ── ENGLISH_LITERATURE ────────────────────────────────────────────────────
    ("el-001", "Story Elements: Character, Setting, Plot",
     "Identifying the basic building blocks of a narrative story.",
     "ENGLISH_LITERATURE", "EMERGING", "OK-ELA-K.5", "k2"),

    ("el-002", "Reading Comprehension and Inference",
     "Using text evidence to answer literal and inferential questions.",
     "ENGLISH_LITERATURE", "DEVELOPING", "OK-ELA-3.3", "35"),

    ("el-003", "Literary Devices: Metaphor, Simile, and Imagery",
     "Identifying and analyzing figurative language in poetry and prose.",
     "ENGLISH_LITERATURE", "DEVELOPING", "OK-ELA-4.4", "35"),

    ("el-004", "Narrative Writing: Voice and Structure",
     "Developing a personal writing voice; structuring beginning, middle, and end.",
     "ENGLISH_LITERATURE", "EXPANDING", "OK-ELA-6.5", "68"),

    ("el-005", "Classic Literature: Theme and Symbol",
     "Deep reading of classic texts to identify recurring themes and symbolic language.",
     "ENGLISH_LITERATURE", "EXPANDING", "OK-ELA-7.4", "68"),

    ("el-006", "Rhetoric and Persuasive Writing",
     "Ethos, pathos, logos; crafting well-reasoned arguments.",
     "ENGLISH_LITERATURE", "MASTERING", "OK-ELA-10.3", "912"),

    ("el-007", "Research Writing and Citation",
     "MLA format, source evaluation, thesis development, and academic writing.",
     "ENGLISH_LITERATURE", "MASTERING", "OK-ELA-11.5", "912"),

    ("el-008", "Archetype and Allegory in Literature",
     "Recognizing universal patterns and extended metaphors in canonical works.",
     "ENGLISH_LITERATURE", "MASTERING", "OK-ELA-12.2", "912"),
]


# ── Prerequisite edges: (from_id, to_id, weight) ─────────────────────────────
# Meaning: to_id must be mastered before from_id (to_id is a prerequisite of from_id)

PREREQUISITES = [
    # TRUTH_HISTORY chain
    ("th-002", "th-001", 0.9),   # Primary sources requires oral tradition basics
    ("th-003", "th-002", 0.9),   # Bias analysis requires source literacy
    ("th-005", "th-003", 0.8),   # Historiography requires bias understanding
    ("th-006", "th-003", 0.7),   # Propaganda requires bias analysis
    ("th-008", "th-002", 0.9),   # Witness Protocol requires source literacy
    ("th-004", "th-002", 0.7),   # Dawes Act requires source literacy

    # CREATION_SCIENCE chain
    ("cs-003", "cs-001", 0.8),   # Ecosystems requires observation
    ("cs-003", "cs-002", 0.8),   # Ecosystems requires plant life cycles
    ("cs-004", "cs-001", 0.8),   # Cell biology requires observation
    ("cs-005", "cs-004", 0.9),   # Genetics requires cell biology
    ("cs-006", "cs-005", 0.8),   # Intelligent design requires genetics
    ("cs-008", "cs-001", 0.7),   # Chemistry requires observation

    # HOMESTEADING chain
    ("hs-002", "hs-001", 0.9),   # Composting requires garden basics
    ("hs-003", "hs-002", 0.9),   # Soil pH requires composting
    ("hs-004", "hs-003", 0.8),   # Permaculture requires soil knowledge
    ("hs-007", "hs-004", 0.9),   # Regenerative ag requires permaculture
    ("hs-007", "hs-003", 0.8),   # Regenerative ag requires soil pH
    ("hs-008", "hs-001", 0.7),   # Water systems requires garden basics

    # GOVERNMENT_ECONOMICS chain
    ("ge-002", "ge-001", 0.8),
    ("ge-003", "ge-002", 0.7),
    ("ge-004", "ge-002", 0.8),
    ("ge-007", "ge-001", 0.7),
    ("ge-008", "ge-007", 0.7),
    ("ge-005", "ge-004", 0.8),
    ("ge-005", "ge-007", 0.8),
    ("ge-006", "ge-005", 0.9),

    # JUSTICE_CHANGEMAKING chain
    ("jc-002", "jc-001", 0.7),
    ("jc-003", "jc-002", 0.9),
    ("jc-004", "jc-001", 0.7),
    ("jc-005", "jc-004", 0.8),
    ("jc-005", "jc-003", 0.7),
    ("jc-006", "jc-004", 0.8),
    ("jc-007", "jc-006", 0.9),

    # DISCIPLESHIP chain
    ("ds-002", "ds-001", 0.8),
    ("ds-003", "ds-002", 0.8),
    ("ds-005", "ds-003", 0.8),
    ("ds-004", "ds-003", 0.9),
    ("ds-006", "ds-004", 0.8),
    ("ds-008", "ds-006", 0.8),

    # HEALTH_NATUROPATHY chain
    ("hn-002", "hn-001", 0.8),
    ("hn-003", "hn-002", 0.7),
    ("hn-004", "hn-002", 0.8),
    ("hn-005", "hn-004", 0.8),
    ("hn-006", "hn-005", 0.9),
    ("hn-007", "hn-002", 0.7),

    # ENGLISH_LITERATURE chain
    ("el-002", "el-001", 0.9),
    ("el-003", "el-002", 0.8),
    ("el-004", "el-003", 0.7),
    ("el-005", "el-004", 0.8),
    ("el-006", "el-004", 0.7),
    ("el-007", "el-006", 0.8),
    ("el-008", "el-005", 0.8),
]


# ── Cross-track OAS Standard links (thematic connections between tracks) ──────
# These are stored on the Track nodes via CROSS_TRACK_LINK relationships,
# enabling the orchestrator's cross-track context queries.

CROSS_TRACK_LINKS = [
    # Soil science bridges HOMESTEADING ↔ CREATION_SCIENCE
    ("HOMESTEADING",         "CREATION_SCIENCE"),
    # Land justice bridges JUSTICE_CHANGEMAKING ↔ TRUTH_HISTORY
    ("JUSTICE_CHANGEMAKING", "TRUTH_HISTORY"),
    # Stewardship bridges HOMESTEADING ↔ DISCIPLESHIP
    ("HOMESTEADING",         "DISCIPLESHIP"),
    # Economics bridges GOVERNMENT_ECONOMICS ↔ JUSTICE_CHANGEMAKING
    ("GOVERNMENT_ECONOMICS", "JUSTICE_CHANGEMAKING"),
    # Health + creation bridges HEALTH_NATUROPATHY ↔ CREATION_SCIENCE
    ("HEALTH_NATUROPATHY",   "CREATION_SCIENCE"),
    # Literature as history source bridges ENGLISH_LITERATURE ↔ TRUTH_HISTORY
    ("ENGLISH_LITERATURE",   "TRUTH_HISTORY"),
    # Biblical worldview bridges DISCIPLESHIP ↔ GOVERNMENT_ECONOMICS
    ("DISCIPLESHIP",         "GOVERNMENT_ECONOMICS"),
]


async def seed_cross_track_links() -> None:
    for from_track, to_track in CROSS_TRACK_LINKS:
        await neo4j_client.run(
            """
            MERGE (a:Track {name: $from_track})
            MERGE (b:Track {name: $to_track})
            MERGE (a)-[:CROSS_TRACK_LINK]->(b)
            """,
            {"from_track": from_track, "to_track": to_track},
        )
    logger.info(f"[Seed] {len(CROSS_TRACK_LINKS)} cross-track links created.")


async def main() -> None:
    logger.info("Connecting to Neo4j…")
    await neo4j_client.connect()

    logger.info("Applying schema constraints…")
    await apply_schema_constraints()

    logger.info("Seeding Track nodes…")
    await seed_tracks()

    logger.info(f"Seeding {len(CONCEPTS)} Concept nodes…")
    for concept_args in CONCEPTS:
        concept_id, title, description, track, difficulty, standard_code, grade_band = concept_args
        await upsert_concept(
            concept_id=concept_id,
            title=title,
            description=description,
            track=track,
            difficulty=difficulty,
            standard_code=standard_code,
            grade_band=grade_band,
        )

    logger.info(f"Seeding {len(PREREQUISITES)} PREREQUISITE_OF edges…")
    for from_id, to_id, weight in PREREQUISITES:
        await add_prerequisite(from_id, to_id, weight)

    logger.info("Seeding cross-track links…")
    await seed_cross_track_links()

    # Summary
    counts = await neo4j_client.run("""
        MATCH (c:Concept)   WITH count(c) AS concepts
        MATCH (t:Track)     WITH concepts, count(t) AS tracks
        MATCH (p:Concept)-[:PREREQUISITE_OF]->(:Concept) WITH concepts, tracks, count(p) AS prereqs
        RETURN concepts, tracks, prereqs
    """)
    if counts:
        c = counts[0]
        logger.info(
            f"Graph summary: {c.get('tracks')} Tracks | "
            f"{c.get('concepts')} Concepts | "
            f"{c.get('prereqs')} PREREQUISITE_OF edges"
        )

    await neo4j_client.close()
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
