"""
build_oas_seed.py — Rebuild oas_to_8track.json with full 10-track, K-12 coverage

Problems this fixes in the existing seed file:
  1. All 646 Social Studies entries are lumped under TRUTH_HISTORY instead of
     routing to GOVERNMENT_ECONOMICS, JUSTICE_CHANGEMAKING, and CREATIVE_ECONOMY.
  2. DISCIPLESHIP track has zero entries (no direct OAS equivalent — this script
     injects synthesized biblical-worldview standards for every grade band).
  3. CREATIVE_ECONOMY track has zero entries — this script injects Visual Arts
     OAS-aligned standards plus entrepreneurship content.
  4. High school OAS courses are all stamped grade=9; this script reassigns them
     to the correct canonical grade (WG→9, OKH→10, USH→11, USG/E→12, etc.).

Run from adeline-brain/:
    python scripts/build_oas_seed.py

Output: data/seeds/oas_to_8track.json  (overwrites in-place)
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "oas_to_8track.json"

# ── Track routing helpers ─────────────────────────────────────────────────────

JUSTICE_KEYWORDS = {
    "JUSTICE", "CIVIL RIGHT", "DISCRIMINATION", "INEQUIT", "OPPRESSION",
    "ACTIVISM", "PROTEST", "SEGREGAT", "ABOLIT", "SUFFRAGE", "HUMAN RIGHT",
    "INJUSTICE", "ADVOCACY", "REFORM", "CIVIL LIBERT", "EXPLOITATION",
    "REPARATION", "SYSTEMIC", "DISENFRANCHIS",
}

ECONOMICS_KEYWORDS = {
    "ECONOM", "TRADE", "FINANCIAL", "MARKET", "CONSUMER", "PRODUCER",
    "SUPPLY", "DEMAND", "ENTREPRENEUR", "BUDGET", "CURRENCY", "CAPITAL",
    "COMMERCE", "BUSINESS", "INVESTMENT", "SCARCITY", "PROFIT", "REVENUE",
    "PRICE", "MONETARY", "FISCAL", "GDP", "INFLATION",
}

GOVERNMENT_KEYWORDS = {
    "GOVERNMENT", "CIVIC", "CONSTITUTION", "DEMOCRACY", "ELECTION",
    "LEGISLATIVE", "EXECUTIVE", "JUDICIAL", "FEDERAL", "CONGRESS",
    "CITIZEN", "VOTE", "VOTING", "LAW", "POLICY", "AMENDMENT", "REPUBLIC",
    "DEMOCRATIC PROCESS", "BRANCHES OF", "BILL OF RIGHT", "FEDERALISM",
    "SEPARATION OF POWER", "CHECKS AND BALANCE", "SOVEREIGNTY",
}

# High-school Social Studies course prefixes → (track, canonical_grade)
HS_SS_PREFIX_MAP = {
    "WG":  ("TRUTH_HISTORY",        9),   # World Geography
    "OKH": ("TRUTH_HISTORY",        10),  # Oklahoma History
    "WH":  ("TRUTH_HISTORY",        9),   # World History
    "USH": ("TRUTH_HISTORY",        11),  # US History
    "USG": ("GOVERNMENT_ECONOMICS", 12),  # US Government
    "E":   ("CREATIVE_ECONOMY",     12),  # Economics
    "PS":  ("DISCIPLESHIP",         11),  # Psychology
    "S":   ("JUSTICE_CHANGEMAKING", 11),  # Sociology
}


def _hs_ss_prefix(standard_id: str):
    """Return (track, grade) for a high-school Social Studies standard_id, or None."""
    for prefix, (track, grade) in HS_SS_PREFIX_MAP.items():
        if re.match(rf"^{re.escape(prefix)}\.", standard_id, re.IGNORECASE):
            return track, grade
    return None


def _reroute_social_studies(standard_id: str, text: str, grade: int) -> tuple[str, int]:
    """Return (track, corrected_grade) for a Social Studies mapping."""
    text_upper = text.upper()

    # High-school course prefixes take priority over text analysis
    hs = _hs_ss_prefix(standard_id)
    if hs:
        return hs

    # K-8 text-based routing
    if any(k in text_upper for k in JUSTICE_KEYWORDS):
        return "JUSTICE_CHANGEMAKING", grade

    if any(k in text_upper for k in ECONOMICS_KEYWORDS):
        # Economics → CREATIVE_ECONOMY at grade 5+ (personal finance / entrepreneurship),
        # GOVERNMENT_ECONOMICS at K-4 (community helpers, markets).
        return ("CREATIVE_ECONOMY" if grade >= 5 else "GOVERNMENT_ECONOMICS"), grade

    if any(k in text_upper for k in GOVERNMENT_KEYWORDS):
        return "GOVERNMENT_ECONOMICS", grade

    return "TRUTH_HISTORY", grade


def _difficulty(grade: int) -> str:
    if grade <= 2:
        return "EMERGING"
    if grade <= 5:
        return "DEVELOPING"
    if grade <= 8:
        return "EXPANDING"
    return "MASTERING"


def _track_hook(track: str) -> str:
    return {
        "ENGLISH_LITERATURE":   "What does this text say, and how do you know?",
        "TRUTH_HISTORY":        "What primary source proves this? Where would you look?",
        "APPLIED_MATHEMATICS":  "How would you use this on the farm or in a business?",
        "CREATION_SCIENCE":     "What does this reveal about God's design in creation?",
        "HOMESTEADING":         "How does this help you steward your land more faithfully?",
        "HEALTH_NATUROPATHY":   "How does God's design for the body connect to this?",
        "GOVERNMENT_ECONOMICS": "How does this play out in real family or community life?",
        "CREATIVE_ECONOMY":     "How could a maker or small-business owner use this?",
        "JUSTICE_CHANGEMAKING": "What does faithful action look like in response to this?",
        "DISCIPLESHIP":         "How does Scripture speak to this?",
    }.get(track, "How does this connect to real life?")


def _track_homestead(track: str) -> str:
    return {
        "ENGLISH_LITERATURE":   "Practice this skill using farm records, seed catalogs, or pioneer memoirs.",
        "TRUTH_HISTORY":        "Find a local primary source — land deed, newspaper, letter — that connects to this.",
        "APPLIED_MATHEMATICS":  "Apply this to a real farm calculation: seed rates, fencing, or pricing produce.",
        "CREATION_SCIENCE":     "Observe this in the garden, with animals, or in the natural world around you.",
        "HOMESTEADING":         "Apply this directly to your land, animals, or homestead projects.",
        "HEALTH_NATUROPATHY":   "Connect this to food you grow, herbs in the garden, or outdoor activity.",
        "GOVERNMENT_ECONOMICS": "Trace how this applies to your local community, co-op, or farm stand.",
        "CREATIVE_ECONOMY":     "Build something, sell something, or design something that uses this skill.",
        "JUSTICE_CHANGEMAKING": "Research a local historical example. What documents exist? What actions were taken?",
        "DISCIPLESHIP":         "Discuss how this connects to a biblical principle you are already living.",
    }.get(track, "Connect this to your everyday homestead life.")


TRACK_BLOCKS = {
    "ENGLISH_LITERATURE":   ["TEXT", "QUIZ", "PRIMARY_SOURCE"],
    "TRUTH_HISTORY":        ["PRIMARY_SOURCE", "TEXT", "RESEARCH_MISSION"],
    "APPLIED_MATHEMATICS":  ["TEXT", "LAB_MISSION", "QUIZ"],
    "CREATION_SCIENCE":     ["TEXT", "LAB_MISSION", "QUIZ"],
    "HOMESTEADING":         ["TEXT", "LAB_MISSION", "PRIMARY_SOURCE"],
    "HEALTH_NATUROPATHY":   ["TEXT", "LAB_MISSION", "QUIZ"],
    "GOVERNMENT_ECONOMICS": ["TEXT", "QUIZ", "LAB_MISSION"],
    "CREATIVE_ECONOMY":     ["TEXT", "LAB_MISSION", "QUIZ"],
    "JUSTICE_CHANGEMAKING": ["PRIMARY_SOURCE", "TEXT", "RESEARCH_MISSION"],
    "DISCIPLESHIP":         ["TEXT", "QUIZ"],
}

TRACK_LABELS = {
    "ENGLISH_LITERATURE":   "English Language & Literature",
    "TRUTH_HISTORY":        "Truth-Based History",
    "APPLIED_MATHEMATICS":  "Applied Mathematics",
    "CREATION_SCIENCE":     "God's Creation & Science",
    "HOMESTEADING":         "Homesteading & Stewardship",
    "HEALTH_NATUROPATHY":   "Health & Naturopathy",
    "GOVERNMENT_ECONOMICS": "Government & Economics",
    "CREATIVE_ECONOMY":     "Creative Economy",
    "JUSTICE_CHANGEMAKING": "Justice & Change-making",
    "DISCIPLESHIP":         "Discipleship & Ethics",
}


def _node_id(standard_id: str, subject: str, grade: int) -> str:
    """Generate a globally-unique Neo4j node id: SUBJ_G{grade}_{standard_id}."""
    subj_code = re.sub(r"[^A-Z0-9]", "", subject.upper().replace(" ", ""))[:6]
    return f"{subj_code}_G{grade}_{standard_id}"


def _make_entry(
    standard_id: str,
    standard_text: str,
    grade: int,
    track: str,
    subject: str,
    strand: str = "",
    rationale: str = "",
) -> dict:
    grade_label = "K" if grade == 0 else str(grade)
    return {
        "grade": grade,
        "subject": subject,
        "standard_id": standard_id,
        "standard_text": standard_text,
        "track": track,
        "track_label": TRACK_LABELS[track],
        "rationale": rationale or f"{standard_id} — {subject}, Grade {grade_label}.",
        "adeline_lesson_hook": _track_hook(track),
        "homestead_adaptation": _track_homestead(track),
        "block_types_suggested": TRACK_BLOCKS[track],
        "difficulty": _difficulty(grade),
        "neo4j_node": {
            "label": "OASStandard",
            "properties": {
                "id":           _node_id(standard_id, subject, grade),
                "standard_id":  standard_id,
                "grade":        grade,
                "subject":      subject.upper().replace(" ", "_"),
                "strand":       strand,
            },
        },
        "neo4j_relationships": [
            {"type": "MAPS_TO_TRACK", "target": track},
        ],
    }


# ── Synthesized DISCIPLESHIP standards (K–12) ────────────────────────────────
# Source: Adeline 10-Track Constitution — no direct OAS equivalent.
# These biblical-worldview and character-education standards are Adeline-native.

DISCIPLESHIP_STANDARDS: list[tuple[str, int, str]] = [
    # K-2 EMERGING
    ("D.K.1",  0,  "The student understands that God made the world and everything in it, and that caring for creation is a foundational responsibility (Genesis 1–2)."),
    ("D.K.2",  0,  "The student identifies character virtues — honesty, kindness, courage, self-control — and can give examples from Scripture and daily life."),
    ("D.K.3",  0,  "The student retells familiar Bible stories, identifying the main figure, the problem, and how God acted."),
    ("D.1.1",  1,  "The student reads and reflects on simple Bible passages about character, love, and truth, and applies their meaning to everyday decisions."),
    ("D.1.2",  1,  "The student applies the Golden Rule (Matthew 7:12) to real situations at home, in school, and in community."),
    ("D.1.3",  1,  "The student understands that God is truth (John 14:6) and explains why honesty matters even when it is hard."),
    ("D.2.1",  2,  "The student understands that caring for the earth is a biblical mandate (Genesis 2:15) and demonstrates care for plants, animals, and the environment."),
    ("D.2.2",  2,  "The student distinguishes between truth and falsehood and explains why a biblical worldview values truth above personal preference."),
    ("D.2.3",  2,  "The student identifies and practices the fruit of the Spirit (Galatians 5:22–23) in daily interactions."),

    # 3-5 DEVELOPING
    ("D.3.1",  3,  "The student explains how a Christian worldview answers four key questions: origin (where did we come from?), meaning (why are we here?), morality (how do we know right from wrong?), and destiny (where are we going?)."),
    ("D.3.2",  3,  "The student respectfully describes key differences between Christianity and at least one other worldview, using primary sources from each tradition."),
    ("D.3.3",  3,  "The student memorizes and meditates on key Scripture passages and explains their meaning in their own words."),
    ("D.4.1",  4,  "The student reads and interprets a biblical ethical passage (e.g., Proverbs, Sermon on the Mount) and applies it to a modern scenario with specific reasoning."),
    ("D.4.2",  4,  "The student designs and documents a real service project, explaining the biblical motivation, the action taken, and the outcome observed."),
    ("D.4.3",  4,  "The student traces a major theme (e.g., covenant, redemption, justice) through at least five books of the Bible."),
    ("D.5.1",  5,  "The student explains the main theological claims of the Apostles' Creed and their historical significance for the Church."),
    ("D.5.2",  5,  "The student evaluates a book, film, or news story through a biblical lens, identifying worldview assumptions and contrasting them with Scripture."),
    ("D.5.3",  5,  "The student understands that vocation — all legitimate work done for God's glory — is a biblical concept, and begins to identify their own gifts and callings."),

    # 6-8 EXPANDING
    ("D.6.1",  6,  "The student identifies major philosophical questions (epistemology, ethics, metaphysics) and explains how Christianity addresses each with evidence from Scripture and Church history."),
    ("D.6.2",  6,  "The student explains and evaluates two classical arguments for the existence of God (e.g., Cosmological, Teleological) and one major objection to each."),
    ("D.6.3",  6,  "The student analyzes a cultural trend or media artifact, identifying underlying worldview commitments and contrasting them with a biblical framework."),
    ("D.7.1",  7,  "The student compares deontological, consequentialist, and virtue ethics frameworks, evaluating each through the lens of biblical ethics."),
    ("D.7.2",  7,  "The student researches and presents on a moral controversy (e.g., environmental ethics, economic justice), developing a reasoned biblical position supported by primary sources."),
    ("D.7.3",  7,  "The student traces key movements in Church history — early church, Reformation, Great Awakening — and explains their cultural and theological impact."),
    ("D.8.1",  8,  "The student examines a bioethical issue (e.g., end-of-life care, genetic technology) using Scripture, natural law, and Christian tradition, and defends a position in writing."),
    ("D.8.2",  8,  "The student explains the concept of common grace and its implications for engaging culture, science, and government from a Christian perspective."),
    ("D.8.3",  8,  "The student reads and analyzes a primary text from Church history (e.g., Augustine's Confessions, Luther's 95 Theses, Bonhoeffer's Letters and Papers from Prison) and explains its significance."),

    # 9-12 MASTERING
    ("D.9.1",  9,  "The student outlines and defends the major loci of Christian systematic theology — Scripture, God, humanity, salvation, Church, and eschatology — drawing on primary theological sources."),
    ("D.9.2",  9,  "The student evaluates the major contemporary objections to Christian belief (problem of evil, religious pluralism, scientific naturalism) and develops careful written responses."),
    ("D.10.1", 10, "The student critically examines the philosophy of religion, engaging arguments from Plantinga, Lewis, Keller, and their secular interlocutors, and produces an original philosophical essay."),
    ("D.10.2", 10, "The student compares systematic theologies across Christian traditions (Reformed, Wesleyan, Catholic, Orthodox) on at least three major doctrines."),
    ("D.11.1", 11, "The student engages a significant secular cultural narrative with a well-reasoned, evidence-based biblical response in a polished written or multimedia format."),
    ("D.11.2", 11, "The student develops and defends a personal theology of vocation, integrating spiritual gifting, community need, and biblical calling into a coherent life vision."),
    ("D.12.1", 12, "The student completes a capstone philosophy of life statement integrating Christian theology, ethics, and vocation, supported by at least five primary theological or philosophical sources."),
    ("D.12.2", 12, "The student designs and teaches a short lesson on a theological topic to a younger student, demonstrating mastery through both content accuracy and pedagogical clarity."),
]


# ── Synthesized CREATIVE_ECONOMY standards (K–12) ────────────────────────────
# Sources: Oklahoma Visual Arts Academic Standards (OVAAS) + OAS ELA/Math
# entrepreneurship strands + Adeline maker/selling philosophy.

CREATIVE_ECONOMY_STANDARDS: list[tuple[str, int, str]] = [
    # K-2 EMERGING
    ("CE.K.1",  0,  "Creating: The student explores and creates art using basic materials (crayons, paint, clay, fabric), developing fine motor skills and creative expression."),
    ("CE.K.2",  0,  "Making and sharing: The student shows completed work to others and explains in simple terms what they made and why."),
    ("CE.K.3",  0,  "The student identifies that people make things to sell or give as gifts, and names simple examples of handmade goods in their community."),
    ("CE.1.1",  1,  "Visual Arts — Creating: The student creates works of art that express ideas, feelings, or observations using line, shape, color, and texture."),
    ("CE.1.2",  1,  "Visual Arts — Presenting: The student selects a finished artwork, explains their choices, and displays it for an audience."),
    ("CE.1.3",  1,  "Design thinking: The student identifies a simple problem, brainstorms at least three solutions, and creates a model or prototype of their best idea."),
    ("CE.2.1",  2,  "Visual Arts — Responding: The student describes what they see and feel when looking at a work of art, using basic art vocabulary (line, color, shape, texture)."),
    ("CE.2.2",  2,  "The student understands that artists and makers earn income by selling their work, and identifies at least two ways creative people make a living."),
    ("CE.2.3",  2,  "The student completes a simple craft project (e.g., hand-stitched bookmark, painted tile, woven placemat) and gives it as a gift or sells it at a class market."),

    # 3-5 DEVELOPING
    ("CE.3.1",  3,  "Visual Arts — Creating: The student creates art using a variety of media and techniques, beginning to develop a personal style and artistic voice."),
    ("CE.3.2",  3,  "Visual Arts — Connecting: The student analyzes a work of art, identifying the artist's choices and describing its cultural and historical context."),
    ("CE.3.3",  3,  "Entrepreneurship: The student identifies a need in their community and sketches a product or service idea to meet it, including a simple cost estimate."),
    ("CE.4.1",  4,  "Visual Arts: The student applies principles of design (balance, contrast, emphasis, rhythm) to create a finished artwork in at least two media."),
    ("CE.4.2",  4,  "Portfolio: The student curates a portfolio of their best creative work from the year, writing a reflection for each piece explaining their growth."),
    ("CE.4.3",  4,  "Entrepreneurship: The student designs a simple product or service, prices it to cover costs and earn a small profit, and presents the plan to a real audience."),
    ("CE.5.1",  5,  "Digital design: The student uses basic digital tools to create a visual design (poster, logo, or layout) and explains the design decisions made."),
    ("CE.5.2",  5,  "Creative economy awareness: The student identifies at least five occupations in the creative economy (graphic designer, illustrator, craftsperson, musician, filmmaker, architect) and researches the skills each requires."),
    ("CE.5.3",  5,  "Visual Arts: The student creates a series of related works exploring a personal theme, demonstrating growth in technique and artistic intention."),

    # 6-8 EXPANDING
    ("CE.6.1",  6,  "Visual Arts — Advanced Creating: The student creates complex artworks using perspective, proportion, and intentional composition, demonstrating both technical skill and artistic intention."),
    ("CE.6.2",  6,  "Art history: The student places artworks and artistic movements in historical context, connecting them to cultural, technological, and economic change."),
    ("CE.6.3",  6,  "Entrepreneurship: The student writes a basic business plan for a creative enterprise — including market research, cost-benefit analysis, and a revenue projection — and presents it to a panel."),
    ("CE.7.1",  7,  "Craft and making: The student completes a significant craft or maker project (woodworking, sewing, ceramics, weaving, metalwork) and documents the full process — design, iteration, final product — in a portfolio."),
    ("CE.7.2",  7,  "Design principles: The student applies principles of design (balance, contrast, hierarchy, alignment, proximity) to create visual communications across multiple media formats."),
    ("CE.7.3",  7,  "Creative economy analysis: The student researches how an independent creator or small maker builds a sustainable business, including pricing strategy, marketing, and customer relationships."),
    ("CE.8.1",  8,  "Visual Arts — Capstone: The student develops a cohesive body of work (at least 8 pieces) around a personal theme or style, with an artist's statement explaining the conceptual and technical decisions."),
    ("CE.8.2",  8,  "Entrepreneurship: The student launches a micro-enterprise — Etsy shop, craft fair booth, local produce stand, commission project — operating it for at least one grading period and documenting revenue, expenses, and lessons learned."),
    ("CE.8.3",  8,  "Digital media: The student creates a short documentary, photo essay, or digital publication, applying principles of visual storytelling, typography, and layout."),

    # 9-12 MASTERING
    ("CE.9.1",  9,  "Advanced Visual Arts: The student develops an advanced body of work in a chosen discipline (painting, printmaking, sculpture, photography, fiber arts, digital illustration), demonstrating mastery of medium-specific techniques."),
    ("CE.9.2",  9,  "Portfolio development: The student builds a professional creative portfolio — physical and digital — suitable for college art programs, client presentations, or gallery submission."),
    ("CE.10.1", 10, "Creative entrepreneurship: The student designs, launches, and operates a creative business or freelance practice for at least one semester, tracking revenue, marketing efforts, and customer feedback."),
    ("CE.10.2", 10, "Intellectual property and creative rights: The student understands copyright, trademark, and licensing as they apply to creative work, and applies this knowledge to their own output."),
    ("CE.11.1", 11, "Gallery or exhibition: The student curates and mounts a public exhibition of their work — school gallery, community venue, or online platform — including wall labels, an artist's statement, and a promotional strategy."),
    ("CE.11.2", 11, "Creative economy capstone research: The student researches and interviews a working creative professional, analyzing their career path, business model, and the role of faith or values in their work."),
    ("CE.12.1", 12, "Capstone project: The student completes a substantial, professional-quality creative work — a manuscript, album, product line, architectural model, or full software/app design — and presents it to a public audience with a full process portfolio."),
    ("CE.12.2", 12, "The student articulates a theology of creativity — grounding their artistic practice in the Imago Dei and a biblical understanding of beauty, craft, and cultural stewardship — in a written manifesto supported by Scripture and primary sources."),
]


# ── Main rebuild ──────────────────────────────────────────────────────────────

def rebuild(path: Path) -> None:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    original_mappings: list[dict] = data["mappings"]
    print(f"Loaded {len(original_mappings)} existing mappings")

    new_mappings: list[dict] = []
    rerouted = Counter()
    grade_fixed = 0

    for m in original_mappings:
        sid = m["standard_id"]
        subj = m["subject"]
        grade = m["grade"]

        if subj == "Social Studies":
            new_track, new_grade = _reroute_social_studies(sid, m["standard_text"], grade)
            old_track = m["track"]
            changed = new_track != old_track or new_grade != grade
        else:
            new_track = m["track"]
            new_grade = grade
            old_track = m["track"]
            changed = False

        # Always ensure neo4j node id is compound-unique
        props = m["neo4j_node"]["properties"]
        current_node_id = props.get("id", sid)
        correct_node_id = _node_id(sid, subj, new_grade)
        if changed or current_node_id == sid:  # plain id needs upgrading
            m = dict(m)
            m["neo4j_node"] = dict(m["neo4j_node"])
            m["neo4j_node"]["properties"] = {
                **props,
                "id": correct_node_id,
                "standard_id": sid,
                "grade": new_grade,
            }
            if changed:
                m["track"] = new_track
                m["track_label"] = TRACK_LABELS[new_track]
                m["adeline_lesson_hook"] = _track_hook(new_track)
                m["homestead_adaptation"] = _track_homestead(new_track)
                m["block_types_suggested"] = TRACK_BLOCKS[new_track]
                m["difficulty"] = _difficulty(new_grade)
                m["grade"] = new_grade
                m["neo4j_relationships"] = [{"type": "MAPS_TO_TRACK", "target": new_track}]
                rerouted[f"{old_track}→{new_track}"] += 1
                if new_grade != grade:
                    grade_fixed += 1

        new_mappings.append(m)

    print(f"Re-routed Social Studies: {dict(rerouted)}")
    print(f"Grade corrections: {grade_fixed}")

    # ── Inject DISCIPLESHIP standards ─────────────────────────────────────────
    existing_ids = {m["standard_id"] for m in new_mappings}
    added_d = 0
    for (sid, grade, text) in DISCIPLESHIP_STANDARDS:
        if sid in existing_ids:
            continue
        new_mappings.append(_make_entry(
            standard_id=sid,
            standard_text=text,
            grade=grade,
            track="DISCIPLESHIP",
            subject="Biblical Worldview & Ethics",
            strand="",
            rationale=f"Adeline Discipleship Track — Grade {'K' if grade == 0 else grade}. No direct OAS equivalent; synthesized from biblical worldview curriculum.",
        ))
        added_d += 1
    print(f"Added {added_d} DISCIPLESHIP standards")

    # ── Inject CREATIVE_ECONOMY standards ────────────────────────────────────
    added_ce = 0
    for (sid, grade, text) in CREATIVE_ECONOMY_STANDARDS:
        if sid in existing_ids:
            continue
        new_mappings.append(_make_entry(
            standard_id=sid,
            standard_text=text,
            grade=grade,
            track="CREATIVE_ECONOMY",
            subject="Visual Arts & Entrepreneurship",
            strand="",
            rationale=f"OVAAS / Entrepreneurship — Grade {'K' if grade == 0 else grade}. Aligned to Oklahoma Visual Arts Academic Standards and Adeline Creative Economy track.",
        ))
        added_ce += 1
    print(f"Added {added_ce} CREATIVE_ECONOMY standards")

    # ── Deduplicate by compound node id (keep first occurrence) ──────────────
    seen_node_ids: set[str] = set()
    deduped: list[dict] = []
    dupes_removed = 0
    for m in new_mappings:
        nid = m["neo4j_node"]["properties"]["id"]
        if nid in seen_node_ids:
            dupes_removed += 1
            continue
        seen_node_ids.add(nid)
        deduped.append(m)
    new_mappings = deduped
    if dupes_removed:
        print(f"Removed {dupes_removed} duplicate entries")

    # ── Sort by grade then standard_id ────────────────────────────────────────
    def sort_key(m):
        sid = m["standard_id"]
        try:
            return (m["grade"], 1, float(sid))
        except ValueError:
            return (m["grade"], 0, sid)

    new_mappings.sort(key=sort_key)

    # ── Stats ─────────────────────────────────────────────────────────────────
    total = len(new_mappings)
    grade_dist = Counter(m["grade"] for m in new_mappings)
    track_dist = Counter(m["track"] for m in new_mappings)

    print(f"\nFinal count: {total} standards")
    print("Grade distribution:")
    for g in sorted(grade_dist):
        label = "K" if g == 0 else str(g)
        print(f"  Grade {label:>2}: {grade_dist[g]}")
    print("Track distribution:")
    for t, n in sorted(track_dist.items()):
        print(f"  {t}: {n}")

    # ── Write ─────────────────────────────────────────────────────────────────
    data["mappings"] = new_mappings
    data["meta"]["purpose"] = (
        "GraphRAG seed — maps OAS K-12 standards to the 10-Track Constitution. "
        "Full 10-track coverage including synthesized DISCIPLESHIP and CREATIVE_ECONOMY standards."
    )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nWritten to {path}")


if __name__ == "__main__":
    rebuild(SEED_PATH)
