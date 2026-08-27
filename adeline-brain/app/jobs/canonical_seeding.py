"""Controlled background authoring for the shared canonical lesson library.

The web experience route and this job deliberately call the same canonical
author.  Background work only moves that expensive call ahead of the learner;
it does not introduce a second lesson format or a block-by-block generator.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, replace
from typing import Iterable

logger = logging.getLogger(__name__)

_LOCK_NAME = "dear-adeline:canonical-library-replenishment"


@dataclass(frozen=True)
class CanonicalSeed:
    topic: str
    track: str
    cross_track: bool = False
    archive_query: str = ""
    evidence_revision: str = ""
    display_title: str = ""
    family_summary: str = ""
    authoring_brief: str = ""
    content_revision: str = ""

    @property
    def learner_title(self) -> str:
        return self.display_title.strip() or self.topic

    @property
    def quality_approved(self) -> bool:
        """Only deliberately designed seeds may enter automatic authoring."""
        return bool(self.family_summary.strip() and self.authoring_brief.strip())


# Ordered deliberately: launch-critical public-interest and practical family
# investigations are authored first, followed by balanced track coverage.
CANONICAL_SEED_CATALOG: tuple[CanonicalSeed, ...] = (
    CanonicalSeed(
        "The Opioid Crisis: Corporate Decisions, Regulation, and Unequal Consequences",
        "JUSTICE_CHANGEMAKING",
        True,
        archive_query="Purdue OxyContin guilty plea marketing FDA opioid",
        display_title="Operation Hooked: How Did OxyContin Become a National Crisis?",
        family_summary=(
            "Open Purdue plea records, OxyContin labels, marketing evidence, regulatory decisions, and overdose data; trace how a profitable product, medical systems, and public policy helped create harm, then pursue a useful accountability or prevention action."
        ),
        authoring_brief=(
            "MISSION FRAME: preserve the focused intelligence-dossier energy of Operation Hooked. DOCUMENTED STARTING POINT: Purdue's affiliate pleaded guilty in 2007 to falsely marketing OxyContin as less addictive, less subject to abuse and diversion, and less likely to cause dependence and withdrawal than other pain medicines; Purdue later pleaded guilty to federal fraud and kickback conspiracies. State those admissions plainly and cite the actual plea records. "
            "DRIVING QUESTION: Through what decisions, incentives, institutions, and accountability failures could profitable opioid marketing contribute to widespread harm, and what response is supported now? OPENING ENCOUNTER: compare the plea language, an FDA label or review record, a company or congressional record, and CDC data before giving an explanatory summary. "
            "SHARED OUTCOME: a sourced accountability map separating Purdue-specific conduct from the broader prescription, heroin, and illicit-fentanyl waves; a calculation, timeline, source analysis, or communication contribution at each learner's actual progression level; and one evidence-backed prevention, treatment, diversion, disclosure, or accountability action addressed to a real recipient whose need is verified. "
            "CORRECTNESS: oxycodone and heroin are opioids but are not chemically identical; do not attribute every opioid death to Purdue; do not claim a Greek word proves a defendant's knowledge. Use records to establish knowledge and conduct, and Scripture to examine the moral meaning of what the records show."
        ),
        content_revision="operation-hooked-records-v3",
    ),
    CanonicalSeed(
        "From Possession to Prison: Drug Policy, Diversion, and Reform",
        "JUSTICE_CHANGEMAKING",
        True,
        display_title="Possession, Prison, or Help? Test How Drug Policy Treats People",
        family_summary=(
            "Compare actual possession rules, sentencing consequences, diversion programs, and outcomes; then defend a practical reform or support proposal "
            "to a real local or state recipient."
        ),
        authoring_brief=(
            "DRIVING QUESTION: When does drug policy protect a community, when does it deepen harm, and what evidence distinguishes punishment from effective help? "
            "OPENING ENCOUNTER: compare two real legal or program records that lead to different consequences for similar conduct. SHARED OUTCOME: an evidence table "
            "and a specific recommendation for a real court, legislator, treatment/diversion provider, or community organization after validating what would be useful."
        ),
        content_revision="drug-policy-comparison-v2",
    ),
    CanonicalSeed(
        "Food Systems: Who Profits, Who Pays, and What the Evidence Shows",
        "JUSTICE_CHANGEMAKING",
        True,
        display_title="Who Controls Our Food? Trace One Family Meal from Seed to Store",
        family_summary=(
            "Put one real family meal on the table, trace its ingredients, prices, ownership, labor, processing, and rules, then build a verified food-system map "
            "and choose one useful change the family can test."
        ),
        authoring_brief=(
            "DRIVING QUESTION: Who made the important decisions behind one meal, who received the money, who carried the costs, and what can this family verify or change? "
            "OPENING ENCOUNTER: learners select one meal or grocery item already in the home and examine its package, ingredient list, origin, price, and company ownership before explanation. "
            "SHARED OUTCOME: a seed-to-store system map grounded in the chosen food, with sourced claims, price or quantity evidence where genuinely useful, and one feasible household, producer, or civic action whose need and impact can be checked. "
            "Do not survey the entire food industry, preach a predetermined verdict, or assign learners to go research everything themselves. Supply and use the evidence needed for this case."
        ),
        content_revision="one-meal-system-map-v1",
    ),
    CanonicalSeed(
        "Operation Bitter Harvest: Glyphosate, Seed Control, and Corporate Accountability",
        "JUSTICE_CHANGEMAKING",
        True,
        archive_query="glyphosate Monsanto court EPA seed patent Schmeiser",
        display_title="Operation Bitter Harvest: What Does the Record Actually Prove?",
        family_summary=(
            "Open a real case file of court opinions, agency findings, scientific assessments, product labels, and seed-patent decisions; separate what is proven, disputed, or still unknown, then design a Beneficial Product Standard and test it with a real recipient."
        ),
        authoring_brief=(
            "DRIVING QUESTION: What do the strongest available records establish about glyphosate risk, corporate conduct, seed control, regulation, and accountability—and where does the evidence remain disputed? "
            "OPENING ENCOUNTER: place a real court finding, an EPA assessment, the IARC classification, a product label, and a patent decision into an evidence file before giving a verdict. "
            "SHARED OUTCOME: a claim ledger that distinguishes verified fact, jury or judicial finding, agency conclusion, scientific hazard assessment, allegation, interpretation, and unanswered question; a family-authored Beneficial Product Standard with measurable criteria; and one lawful, useful action whose recipient and need are confirmed first. "
            "PRESERVE THE MISSION/CASE-FILE ENERGY, Scripture study, sustained investigation, real creation, and portfolio evidence. State any documented verdict, judgment, agency conclusion, or authenticated company record plainly and with its source; do not downgrade a finding to a mere allegation. Do not fabricate internal memos or witness testimony, turn an allegation into a finding, overstate what a cited record proves, or ask minors to handle, dilute, apply, or deliberately expose soil/plants to glyphosate. Use safe observations, public datasets, labels, court records, or nonchemical proxy investigations instead."
        ),
        content_revision="bitter-harvest-record-first-v2",
    ),
    CanonicalSeed(
        "Ultra-Processed Food: Marketing, Regulation, and Health Evidence",
        "HEALTH_NATUROPATHY",
        True,
        display_title="What Is in This Food? Put Package Claims on Trial",
        family_summary=(
            "Audit several foods already in the kitchen, compare package promises with ingredients and strong health evidence, and create a practical family buying guide that marks uncertainty honestly."
        ),
        authoring_brief=(
            "DRIVING QUESTION: Which package claims are supported by the product and evidence, which are merely persuasive, and what information would help this family choose? "
            "OPENING ENCOUNTER: place two or more real packages side by side and make an initial claim-evidence chart from labels alone. SHARED OUTCOME: a revised, sourced household buying guide or comparison tool based on ingredients, serving sizes, processing, cost, and appropriately cautious health evidence."
        ),
        content_revision="package-claims-v1",
    ),
    CanonicalSeed(
        "Pesticides, Farmworkers, and the Food Supply",
        "JUSTICE_CHANGEMAKING",
        True,
        display_title="Pesticides on the Label and in the Field: Who Is Protected?",
        family_summary=(
            "Examine an actual pesticide label alongside exposure rules and farmworker evidence, trace how protection is supposed to work, and create a useful evidence-based safety or policy resource for a validated recipient."
        ),
        authoring_brief=(
            "DRIVING QUESTION: What does a pesticide label require, how is exposure controlled in real work, and whose safety depends on the rules being followed? "
            "OPENING ENCOUNTER: inspect a real EPA label or regulatory record and identify the exact hazard, use, protective-equipment, interval, and enforcement claims it makes. "
            "SHARED OUTCOME: a source-linked protection map and one useful deliverable for a real grower, worker-support group, family gardener, or public official after confirming the need. Avoid unsupported toxicity claims."
        ),
        content_revision="label-to-field-v1",
    ),
    CanonicalSeed(
        "Seed Patents, Market Concentration, and Farmer Choice",
        "GOVERNMENT_ECONOMICS",
        True,
        display_title="Who Owns a Seed? Law, Markets, and a Farmer's Choices",
        family_summary=(
            "Compare seed-saving traditions with actual licenses, plant-variety protections, patent decisions, and market concentration; then build a decision guide for a real growing scenario."
        ),
        authoring_brief=(
            "DRIVING QUESTION: What may a farmer or gardener legally and practically do with a seed, who controls the choices, and how do law and market concentration change the answer? "
            "OPENING ENCOUNTER: compare the terms or claims attached to two real seed sources. SHARED OUTCOME: a sourced choice map for one plausible farm or garden, clearly distinguishing patents, plant-variety protection, contracts, open-pollinated seed, and unanswered legal questions."
        ),
        content_revision="seed-choice-map-v1",
    ),
    CanonicalSeed(
        "Railroads, Oil, and the Robber Barons: Building America or Consolidating Power?",
        "TRUTH_HISTORY",
        True,
        "railroads monopoly Standard Oil",
        "robber-baron-primary-pack-v2",
        display_title="Railroads, Oil, and the Robber Barons: Building America or Consolidating Power?",
        family_summary=(
            "Put federal railroad laws and contemporary Standard Oil cartoons in conversation with subsidies, labor, monopoly, and political power; then add a defensible piece to the living wall timeline."
        ),
        authoring_brief=(
            "DRIVING QUESTION: Did railroad and oil consolidation mainly build shared national capacity, concentrate private power, or both—and what does the record actually support? "
            "OPENING ENCOUNTER: examine the routed Pacific Railway Act, Interstate Commerce Act, and contemporary Standard Oil cartoons before receiving a summary. "
            "SHARED OUTCOME: an evidence matrix, a reasoned provisional verdict with uncertainty, and a printable wall-timeline contribution connecting law, capital, labor, expansion, and people usually omitted."
        ),
        content_revision="robber-baron-investigation-v3",
    ),
    CanonicalSeed(
        "Greenhouse Foundations: Stewardship, Design, and Food Resilience",
        "HOMESTEADING",
        True,
        display_title="Greenhouse Foundations: Can We Design a Growing Place That Works?",
        family_summary=(
            "Study Genesis 2:15 accurately, survey a real site, test light and heat, compare structure choices, calculate only the measurements each learner is ready for, and produce a buildable greenhouse plan or tested first phase."
        ),
        authoring_brief=(
            "DRIVING QUESTION: How can this family design a greenhouse that responsibly serves a real growing need in its actual climate, site, budget, and skill range? "
            "SCRIPTURE ANCHOR: use the actual Hebrew wording of Genesis 2:15, especially avad and shamar, without presenting a single lemma as the full verse or overstating disputed authorship. "
            "OPENING ENCOUNTER: survey a real candidate site and record sun path, shade, drainage, wind exposure, access, and temperature before choosing a design. "
            "SHARED OUTCOME: a site-specific greenhouse design dossier with purpose, scaled sketch, materials and cost ranges, ventilation and water plan, safety constraints, build phases, and either a tested model or a documented first construction phase. "
            "Connect plant biology, heat transfer, measurement, food history, and stewardship only where the design truly requires them. Do not require a 16-by-32-foot purchase or pretend the family has built what it has only planned."
        ),
        content_revision="greenhouse-foundations-v1",
    ),
    CanonicalSeed("The Oklahoma Land Run: Multiple Perspectives", "TRUTH_HISTORY"),
    CanonicalSeed("Oral Tradition and Family History", "TRUTH_HISTORY"),
    CanonicalSeed("The Boston Tea Party: Primary Accounts", "TRUTH_HISTORY"),
    CanonicalSeed("Plant Life Cycles and Seeds", "CREATION_SCIENCE"),
    CanonicalSeed("The Fossil Record and Catastrophism", "CREATION_SCIENCE"),
    CanonicalSeed("Design in the Human Eye", "CREATION_SCIENCE"),
    CanonicalSeed("Building a Rainwater Collection System", "HOMESTEADING"),
    CanonicalSeed("Soil Regeneration and Composting", "HOMESTEADING"),
    CanonicalSeed("Corporate Lobbying vs. Citizen Advocacy", "JUSTICE_CHANGEMAKING"),
    CanonicalSeed(
        "Operation Regulatory Capture: ALEC, Model Bills, and Public Power",
        "JUSTICE_CHANGEMAKING",
        True,
        archive_query="ALEC model policy living wage preemption state bill legislative text",
        display_title="Operation Regulatory Capture: Who Wrote the Law?",
        family_summary=(
            "Compare an ALEC model policy with introduced or enacted state text, trace sponsors, private interests, public claims, and local preemption, then ask a real legislator for a transparent account of the bill's origin and beneficiaries."
        ),
        authoring_brief=(
            "MISSION FRAME: preserve the secure legislative-intelligence dossier and the feeling that learners are uncovering the system behind the system. "
            "DOCUMENTED STARTING POINT: ALEC openly maintains a model-policy library; its Living Wage Mandate Preemption Act expressly repeals local living-wage mandates and prohibits political subdivisions from enacting them. State that text plainly and use the actual model policy. "
            "DRIVING QUESTION: Who wrote or promoted the language in one real state bill, whose interests and arguments shaped it, who gains or loses authority, and what disclosure or public process would serve constituents? "
            "OPENING ENCOUNTER: conduct a side-by-side textual comparison of one model policy and one official state bill or enacted law before summarizing ALEC. Trace sponsors, testimony, votes, lobbying or membership disclosures where records exist, affected local authority, and the strongest public arguments for and against the policy. "
            "SHARED OUTCOME: an annotated bill-origin dossier, a money/power/authority map, and a respectful evidence-specific inquiry to the actual representative, committee, ethics body, journalist, or civic group best able to answer or act. Scripture may supply a moral lens on gifts, partiality, truth, and justice, but the legislative record must establish the institutional claims."
        ),
        content_revision="operation-regulatory-capture-v1",
    ),
    CanonicalSeed("The Parable of the Sower: Original Context", "DISCIPLESHIP"),
    CanonicalSeed("What Does 'Love Your Neighbor' Mean in Practice?", "DISCIPLESHIP"),
    CanonicalSeed("History of the Income Tax in the United States", "GOVERNMENT_ECONOMICS"),
    CanonicalSeed("How Property Taxes Are Calculated and Used", "GOVERNMENT_ECONOMICS"),
    CanonicalSeed("The Hero's Journey in Literature", "ENGLISH_LITERATURE"),
    CanonicalSeed("Symbolism in Scripture and Classic Stories", "ENGLISH_LITERATURE"),
    CanonicalSeed("Calculating Board Feet for Building Projects", "APPLIED_MATHEMATICS"),
    CanonicalSeed("Reading a Land Survey and Calculating Acreage", "APPLIED_MATHEMATICS"),
    CanonicalSeed("Pricing Handmade Goods for Market", "CREATIVE_ECONOMY"),
    CanonicalSeed("Photography for Online Product Sales", "CREATIVE_ECONOMY"),
    CanonicalSeed("Herbal First Aid: Plantain, Lavender, and Calendula", "HEALTH_NATUROPATHY"),
    CanonicalSeed("Stewardship in Creation Science", "CREATION_SCIENCE", True),
    CanonicalSeed("Justice Themes in Scripture and History", "TRUTH_HISTORY", True),
    CanonicalSeed("Biblical Economics and Property Rights", "GOVERNMENT_ECONOMICS", True),
    CanonicalSeed("Healing the Land: Soil, Health, and Sabbath Rest", "HOMESTEADING", True),
    CanonicalSeed(
        "Kitchen Chemistry: Bread and Fermentation",
        "CREATION_SCIENCE",
        True,
        display_title="Kitchen Chemistry: What Makes Bread Rise?",
        family_summary=(
            "Run a controlled dough comparison, observe yeast and gluten in action, use measurements at each learner's level, and preserve a tested family bread formula with evidence explaining why it worked."
        ),
        authoring_brief=(
            "DRIVING QUESTION: How do living yeast, ingredient ratios, temperature, gluten, time, and heat transform simple ingredients into bread? "
            "OPENING ENCOUNTER: mix or observe two small dough conditions that differ in one meaningful variable before the explanation. SHARED OUTCOME: a family lab record, a tested bread formula or model, and an evidence-backed explanation connecting observations to fermentation, gas retention, structure, and baking. "
            "Use baker's percentages only for learners ready for ratios; younger learners contribute through observation, counting, measuring, drawing, and comparison."
        ),
        content_revision="bread-family-lab-v1",
    ),
    CanonicalSeed("Household Water: Testing, Treatment, and Public Responsibility", "CREATION_SCIENCE", True),
    CanonicalSeed("School Lunches: Nutrition, Budgets, Contracts, and Student Voice", "GOVERNMENT_ECONOMICS", True),
    CanonicalSeed("Housing, Zoning, and Who Gets to Live Where", "GOVERNMENT_ECONOMICS", True),
    CanonicalSeed("News Claims Under Pressure: Evidence, Incentives, and Verification", "ENGLISH_LITERATURE", True),
    CanonicalSeed("Design and Test a Low-Cost Food Dryer", "HOMESTEADING", True),
    CanonicalSeed("Map a Household Supply Chain from Raw Material to Waste", "APPLIED_MATHEMATICS", True),
    CanonicalSeed("Build a Community Price Index", "APPLIED_MATHEMATICS", True),
    CanonicalSeed("Create a Useful Product with a Real Customer", "CREATIVE_ECONOMY", True),
)


def canonical_seed_for(topic: str, track: str) -> CanonicalSeed | None:
    """Resolve the approved design brief for an exact catalog topic."""
    normalized_topic = topic.strip().casefold()
    normalized_track = track.strip().upper()
    return next(
        (
            seed for seed in CANONICAL_SEED_CATALOG
            if seed.topic.strip().casefold() == normalized_topic
            and seed.track.upper() == normalized_track
            and seed.quality_approved
        ),
        None,
    )


def canonical_seeding_enabled() -> bool:
    return os.getenv("CANONICAL_SEEDING_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }


def configured_batch_size() -> int:
    try:
        return max(1, min(int(os.getenv("CANONICAL_SEED_BATCH_SIZE", "6")), 50))
    except ValueError:
        logger.warning("Invalid CANONICAL_SEED_BATCH_SIZE; using 6")
        return 6


async def seed_one_canonical(seed: CanonicalSeed) -> str:
    """Create one missing/outdated canonical through the production author."""
    from app.api.experience_builder import _author, canonical_resource_query
    from app.connections.canonical_store import canonical_slug, canonical_store
    from app.curriculum.family_style import finalize_family_lesson, is_current_family_canonical
    from app.schemas.api_models import LessonRequest, Track
    from app.services.resource_router import resource_router

    slug = canonical_slug(seed.topic, seed.track)
    existing = await canonical_store.get(slug)
    stored_revision = ""
    stored_content_revision = ""
    if existing and is_current_family_canonical(existing.get("blocks") or []):
        blocks = existing.get("blocks") or []
        stored_revision = str(
            ((blocks[0].get("metadata") or {}).get("evidence_revision") if blocks else "")
            or ""
        )
        stored_content_revision = str(
            ((blocks[0].get("metadata") or {}).get("content_revision") if blocks else "")
            or ""
        )
        evidence_current = not seed.evidence_revision or stored_revision == seed.evidence_revision
        content_current = not seed.content_revision or stored_content_revision == seed.content_revision
        if evidence_current and content_current:
            logger.info("[CanonicalSeed] SKIP current — %s / %s", seed.topic, seed.track)
            return "skipped"
    if existing:
        reason = (
            "canonical_evidence_upgrade"
            if seed.evidence_revision and stored_revision != seed.evidence_revision
            else "canonical_content_upgrade" if seed.content_revision
            else "canonical_format_upgrade"
        )
        await canonical_store.archive(slug, reason=reason)

    try:
        request = LessonRequest(
            student_id="canonical-seeder",
            track=Track(seed.track),
            topic=seed.topic,
            is_homestead=seed.track == "HOMESTEADING",
            grade_level="9",
        )
        resource_query = canonical_resource_query(request)
        if seed.archive_query:
            resource_query = replace(resource_query, topic=seed.archive_query)
        packet = await resource_router.search(resource_query)
        routed = packet.get("resources") or []
        verified_primary = sum(
            1 for item in routed
            if str(item.get("resource_type") or "").upper() == "PRIMARY_SOURCE"
            and str(item.get("availability") or "").upper()
            in {"VERIFIED_API_ITEM", "VERIFIED_ARCHIVE_ITEM"}
        )
        logger.info(
            "[CanonicalSeed] Sources — topic=%s routed=%d verified_primary=%d provider_failures=%s",
            seed.topic,
            len(routed),
            verified_primary,
            packet.get("provider_failures") or [],
        )
        authored = await _author(
            request,
            packet.get("resources") or [],
            authoring_brief=seed.authoring_brief,
        )
        blocks = finalize_family_lesson(
            authored.get("blocks") or [], seed.topic, track=seed.track
        )
        if not blocks:
            raise ValueError("canonical author returned no valid investigation blocks")
        blocks[0].setdefault("metadata", {})["canonical_contract"] = {
            key: authored.get(key)
            for key in (
                "big_question",
                "learning_goal",
                "shared_experience",
                "experience_design",
                "investigation_scope_contract",
                "public_interest_contract",
                "real_world_task",
                "portfolio_task",
                "printable_contract",
                "demonstration_contract",
                "mastery_evidence_map",
                "family_roles",
            )
        }
        if seed.evidence_revision:
            blocks[0]["metadata"]["evidence_revision"] = seed.evidence_revision
        if seed.content_revision:
            blocks[0]["metadata"]["content_revision"] = seed.content_revision
        record = {
            "id": str(uuid.uuid4()),
            "topic": seed.topic,
            "track": seed.track,
            "title": authored.get("title") or seed.topic,
            "blocks": blocks,
            "oas_standards": [],
            "researcher_activated": bool(packet.get("resources")),
            "agent_name": "Canonical Experience Author",
        }
        await canonical_store.save(slug, record, pending=False)
        logger.info("[CanonicalSeed] READY — %s / %s", seed.topic, seed.track)
        return "seeded"
    except Exception:
        logger.exception("[CanonicalSeed] FAILED — %s / %s", seed.topic, seed.track)
        return "failed"


async def replenish_canonical_library(
    *,
    batch_size: int | None = None,
    catalog: Iterable[CanonicalSeed] | None = None,
) -> dict[str, int | bool]:
    """Author a bounded number of missing canonicals, once across all replicas."""
    from app.config import get_db_conn

    limit = configured_batch_size() if batch_size is None else max(1, min(batch_size, 50))
    # The standing weekly job may author only seeds that carry a deliberate
    # learner-facing promise and a concrete design brief. Passing an explicit
    # catalog remains available to focused tests and controlled repair jobs.
    seeds = (
        tuple(catalog)
        if catalog is not None
        else tuple(seed for seed in CANONICAL_SEED_CATALOG if seed.quality_approved)
    )
    result: dict[str, int | bool] = {
        "seeded": 0,
        "skipped": 0,
        "failed": 0,
        "attempted": 0,
        "locked": False,
    }
    conn = await get_db_conn()
    owns_lock = False
    try:
        owns_lock = bool(await conn.fetchval(
            "SELECT pg_try_advisory_lock(hashtext($1))", _LOCK_NAME
        ))
        if not owns_lock:
            result["locked"] = True
            logger.info("[CanonicalSeed] Another replica owns this replenishment run")
            return result

        logger.info(
            "[CanonicalSeed] Replenishment started — batch=%d catalog=%d", limit, len(seeds)
        )
        for seed in seeds:
            if int(result["attempted"]) >= limit:
                break
            status = await seed_one_canonical(seed)
            result[status] = int(result[status]) + 1
            if status != "skipped":
                result["attempted"] = int(result["attempted"]) + 1
            # Keep provider traffic deliberately serial and gentle.
            if status != "skipped":
                await asyncio.sleep(2)
        logger.info("[CanonicalSeed] Replenishment complete — %s", result)
        return result
    finally:
        if owns_lock:
            try:
                await conn.execute("SELECT pg_advisory_unlock(hashtext($1))", _LOCK_NAME)
            except Exception:
                logger.exception("[CanonicalSeed] Failed to release advisory lock")
        await conn.close()


async def scheduled_canonical_replenishment() -> dict[str, int | bool]:
    """APScheduler entry point; the scheduler itself controls enablement."""
    return await replenish_canonical_library()
