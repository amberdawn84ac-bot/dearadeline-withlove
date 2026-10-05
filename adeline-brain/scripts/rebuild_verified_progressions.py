"""Offline, repeatable source review builder; never run during application startup.

Requires pymupdf and beautifulsoup4. The saved PDFs/HTML must be the exact source
versions recorded in the generated provenance. Source normalization corrects
one printed code typo (3.GM 1.1) and one framework alias (PK.N1.2); obsolete
references are rejected instead of guessed. These are factual relationships,
not copied framework teaching materials.
"""

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz
from bs4 import BeautifulSoup

parser = argparse.ArgumentParser(
    description="Rebuild the reviewed graph from saved primary sources."
)
parser.add_argument(
    "--source-directory",
    type=Path,
    required=True,
    help="PDFs and math_pages used for the source review",
)
parser.add_argument(
    "--science-directory",
    type=Path,
    required=True,
    help="Saved DCI HTML pages plus index.json",
)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
SRC = args.source_directory
SEEDS = ROOT / "data/seeds"
base = json.loads((SEEDS / "oas_to_8track.json").read_text())
rows = [r for r in base["mappings"] if not r.get("authored_subskill")]
urls = {
    "ela2021": "https://oklahoma.gov/content/dam/ok/en/osde/documents/services/standards-learning/english-language-arts/ela-standards/2021%20Oklahoma%20Academic%20Standards%20for%20English%20Language%20Arts.pdf",
    "math2022": "https://oklahoma.gov/content/dam/ok/en/osde/documents/services/literacy-policy-and-programs/oklahoma-academic-standards/2022-OAS-Maths-Standards.pdf",
    "science2026": "https://oklahoma.gov/content/dam/ok/en/osde/documents/services/standards-learning/science-engineering/Final%202026%20OAS-S%201-26.pdf",
    "ela_pk5": "https://oklahoma.gov/content/dam/ok/en/osde/documents/services/standards-learning/english-language-arts/ela-standards/Vertical%20Progression%20Grades%20Pre-K-5.pdf",
    "ela_38": "https://oklahoma.gov/content/dam/ok/en/osde/documents/services/standards-learning/english-language-arts/ela-standards/Vertical%20Progression%20Grades%203-8.pdf",
    "social2026": "https://oklahoma.gov/content/dam/ok/en/osde/documents/services/standards-learning/social-studies/OAS%20Social%20Studies%207.10.26.pdf",
    "health2026": "https://oklahoma.gov/content/dam/ok/en/osde/documents/services/standards-learning/health/2026%20OAS%20Health.pdf",
    "ela_612": "https://oklahoma.gov/content/dam/ok/en/osde/documents/services/standards-learning/english-language-arts/ela-standards/Vertical%20Progression%20Grades%206-12.pdf",
}
titles = {
    "social2026": "2026 Oklahoma Academic Standards for Social Studies",
    "health2026": "2026 Oklahoma Academic Standards for Health Education",
    "ela2021": "2021 Oklahoma Academic Standards for English Language Arts",
    "math2022": "2022 Oklahoma Academic Standards for Mathematics",
    "science2026": "2026 Oklahoma Academic Standards for Science",
    "ela_pk5": "2021 ELA Vertical Progressions PK–5",
    "ela_38": "2021 ELA Vertical Progressions 3–8",
    "ela_612": "2021 ELA Vertical Progressions 6–12",
}
versions = {
    x: (
        "2026"
        if x in ("science2026", "social2026", "health2026")
        else "2022"
        if x == "math2022"
        else "2021"
    )
    for x in urls
}
patterns = {
    "social2026": r"(?m)^\s*(?:PK|K|[1-8]|AWH|MWH|TOT|OKH|USH|USG|E|WG|PS|S)\.(?:[CP]\.)?\d+(?:\.\d+){0,2}\b",
    "health2026": r"\b[1-8]\.(?:[A-Z]{2}\.)?(?:2|5|8|12)\.\d+\b",
    "ela2021": r"\b(?:PK|K|[1-9]|1[0-2])\.\d\.[A-Z]+(?:\.\d+)?\b",
    "math2022": r"\b(?:PK|K|[1-7]|PA|A1|A2|G|PC|S)\.(?:[A-Z][A-Z0-9]*|[23]D)(?:\.\d+){1,3}\b",
    "science2026": r"\b(?:PK\.S\.\d|(?:K|[1-8]|PS|CH|PH|B|ES|EN|K2|35|MS|HS)\.(?:PS|LS|ESS|ETS)\d\.\d+)\b",
}


def clean(t):
    return re.sub(r"\s+", " ", t.replace("\u200b", "")).strip()


def identity(row):
    return (row.get("standard_node") or row.get("neo4j_node"))["properties"]["id"]


def source_info(name, page):
    return dict(
        title=titles[name],
        url=urls[name],
        version=versions[name],
        page=page,
        sha256=hashlib.sha256((SRC / (name + ".pdf")).read_bytes()).hexdigest(),
    )


for row in rows:
    if row["subject"] in (
        "English Language Arts",
        "Mathematics",
        "Science",
        "Social Studies",
        "Health",
    ):
        row.pop("source_record", None)

# Extract standards only from their actual published objective location, never from mentions.
source_catalog = {}
for name, pattern in patterns.items():
    out = {}
    for page_index, page in enumerate(fitz.open(SRC / (name + ".pdf"))):
        text = page.get_text().replace("\u200b", "").replace("3.GM 1.1", "3.GM.1.1")
        matches = [
            m
            for m in re.finditer(pattern, text)
            if not text[text.rfind("\n", 0, m.start()) + 1 : m.start()].strip()
        ]
        for i, m in enumerate(matches):
            code = m[0].strip()
            tail = text[
                m.end() : matches[i + 1].start() if i + 1 < len(matches) else len(text)
            ]
            if name == "science2026":
                tail = re.split(
                    r"Clarification Statement:|Science and Engineering Practices|Oklahoma Academic Standards",
                    tail,
                )[0]
            else:
                tail = re.split(
                    r"Oklahoma Academic Standards|Standard \d:|February 2022|\n\s*\d+\s*\n",
                    tail,
                )[0]
            tail = clean(tail).lstrip("* ")
            if not tail or not re.match(r"(Students\b|[A-Z])", tail):
                continue
            # Referenced codes in examples are not objective definitions.
            if tail.startswith((")", ",", ".", "and ", "for ")):
                continue
            if code not in out or len(tail) > len(out[code]["text"]):
                out[code] = dict(text=tail, **source_info(name, page_index + 1))
    source_catalog[name] = out
print("Source catalog", {k: len(v) for k, v in source_catalog.items()})
by_subject = {
    s: {r["standard_id"]: r for r in rows if r["subject"] == s}
    for s in [
        "English Language Arts",
        "Mathematics",
        "Science",
        "Social Studies",
        "Health",
    ]
}
subjects = {
    "social2026": ("Social Studies", "SOCIAL", "TRUTH_HISTORY"),
    "health2026": ("Health", "HEALTH", "HEALTH_NATUROPATHY"),
    "ela2021": ("English Language Arts", "ENGLIS", "ENGLISH_LITERATURE"),
    "math2022": ("Mathematics", "MATHEM", "APPLIED_MATHEMATICS"),
    "science2026": ("Science", "SCIENC", "CREATION_SCIENCE"),
}
course_grades = {
    "PK": -1,
    "K": 0,
    "PA": 8,
    "A1": 9,
    "G": 10,
    "A2": 10,
    "PC": 11,
    "S": 11,
    "PS": 9,
    "CH": 10,
    "PH": 11,
    "B": 9,
    "ES": 9,
    "EN": 10,
    "K2": 0,
    "35": 3,
    "MS": 6,
    "HS": 9,
}


def grade_for(code):
    p = code.split(".")[0]
    return course_grades[p] if p in course_grades else int(p)


for name, (subject, prefix, track) in subjects.items():
    for code, record in source_catalog[name].items():
        grade = (
            {2: 0, 5: 3, 8: 6, 12: 9}[int(code.split(".")[-2])]
            if subject == "Health"
            else (
                {
                    "AWH": 9,
                    "MWH": 10,
                    "TOT": 11,
                    "OKH": 9,
                    "USH": 11,
                    "USG": 12,
                    "E": 12,
                    "WG": 9,
                    "PS": 11,
                    "S": 11,
                }.get(code.split(".")[0], None)
                if subject == "Social Studies"
                and not code.split(".")[0].isdigit()
                and code.split(".")[0] not in ("K", "PK")
                else grade_for(code)
            )
        )
        existing = by_subject[subject].get(code)
        if existing is None:
            existing = dict(
                grade=grade,
                subject=subject,
                standard_id=code,
                standard_text=record["text"],
                track=track,
                track_label=track,
                rationale="Published source objective.",
                adeline_lesson_hook="",
                homestead_adaptation="",
                block_types_suggested=["TEXT", "QUIZ"],
                difficulty="EMERGING",
                neo4j_node={
                    "label": "OASStandard",
                    "properties": dict(
                        id=f"{prefix}_G{grade}_{code}",
                        grade=grade,
                        subject=subject,
                        strand=code.split(".")[1],
                        standard_id=code,
                    ),
                },
                neo4j_relationships=[],
            )
            rows.append(existing)
            by_subject[subject][code] = existing
        if subject == "Social Studies":
            # Reuse the existing ten-track routing policy for the current codes.
            from scripts.build_oas_seed import _reroute_social_studies

            if code.split(".")[0] in {"AWH", "MWH", "TOT"}:
                routed_track = "TRUTH_HISTORY"
            else:
                routed_track, grade = _reroute_social_studies(code, record["text"], grade)
            existing["track"] = routed_track
            existing["track_label"] = routed_track
        existing["grade_band"] = (
            "PK-2"
            if subject == "Health" and grade == 0
            else "3-5"
            if subject == "Health" and grade == 3
            else "6-8"
            if subject == "Health" and grade == 6
            else "9-12"
            if subject == "Health"
            else code.split(".")[0]
            if grade >= 8
            else str(grade)
        )
        existing["grade"] = grade
        existing["course"] = code.split(".")[0] if grade >= 8 else ""
        existing["standard_text"] = record["text"]
        existing["source_record"] = record
        # Preserve compound IDs even when correcting original course/grade mistakes.
        existing["neo4j_node"]["properties"]["grade"] = grade
        existing["catalog_status"] = "ACTIVE"
# Catalog headings/support dimensions remain available for records, not assignable standards.
for row in rows:
    if row["subject"] in by_subject and not row.get("source_record"):
        row["catalog_status"] = (
            "SUPPORTING"
            if row["subject"] == "Science"
            and row["standard_id"].startswith(("CCC.", "SEP."))
            else "LEGACY_OR_CONTAINER"
        )
# All grade/course objective definitions and aliases are included; mapping identity stays stable.
edges = {}


def add(a, b, kind, info, note):
    if a == b:
        return
    k = (a, kind, b)
    edges.setdefault(
        k,
        dict(
            from_standard_id=a,
            to_standard_id=b,
            relation_type=kind,
            weight=1,
            source_title=info["title"],
            source_url=info["url"],
            source_version=info["version"],
            evidence_note=note,
            review_status="VERIFIED",
        ),
    )


def get_id(subject, code):
    row = by_subject[subject].get(code)
    return identity(row) if row and row.get("source_record") else None


# Prior Knowledge and Leads to are reviewed source connections. Keep Leads to flexible.
math_snapshots = json.loads(
    (SEEDS / "progression_sources/math_connections.json").read_text()
)
math_review = {}
unresolved = []
for snap in sorted(
    math_snapshots, key=lambda r: ("UPDATED" not in r["title"], r["url"])
):
    target = get_id("Mathematics", snap["code"])
    if not target:
        continue
    raw = (SRC / "math_pages" / snap["path"]).read_text()
    soup = BeautifulSoup(raw, "html.parser")
    marker = soup.find(string=lambda t: bool(t and t.strip() == "Prior Knowledge"))
    if not marker:
        raise ValueError(f"Missing source section: {snap['url']}")
    tr = marker.find_parent("tr")
    nextrow = tr.find_next_sibling("tr")
    cells = nextrow.find_all("td", recursive=False)
    if len(cells) != 2:
        raise ValueError(f"Invalid source table: {snap['url']}")
    # Re-extract the source cells, not crawl navigation or unrelated standard mentions.
    lists = [
        sorted(set(re.findall(patterns["math2022"], cell.get_text(" ", strip=True))))
        for cell in cells
    ]
    info = dict(
        title=snap["title"],
        url=snap["url"].replace("http://", "https://"),
        version="2022 OAS-M; reviewed 2026-10-05",
    )
    math_review.setdefault(snap["code"], []).append(
        dict(
            url=info["url"],
            sha256=hashlib.sha256(raw.encode()).hexdigest(),
            prior=lists[0],
            leads=lists[1],
        )
    )
    for section, codes, kind in [
        ("Prior Knowledge", lists[0], "PREREQUISITE_FOR"),
        ("Leads to", lists[1], "FEEDS_INTO"),
    ]:
        for code in codes:
            other = get_id("Mathematics", {"PK.N1.2": "PK.N.1.2"}.get(code, code))
            if not other:
                unresolved.append(
                    dict(
                        source=snap["url"],
                        code=code,
                        disposition="REJECTED_SOURCE_REFERENCE",
                        reason="Source reference does not resolve to a current published objective; excluded from learner locks.",
                    )
                )
                continue
            a, b = (other, target) if section == "Prior Knowledge" else (target, other)
            add(
                a,
                b,
                kind,
                info,
                f"Knowledge Connections / {section} explicitly names {code} in the {snap['code']} objective page. Prior Knowledge is Adeline’s reviewed instructional dependency; Leads to is a flexible connection, not a lock.",
            )
# PDF rows show progression, including merged repeating objectives, not a universal hard order.
ela = json.loads((SEEDS / "progression_sources/ela_rows.json").read_text())
for table_row in ela["rows"]:
    codes = list(
        dict.fromkeys(code for cell in table_row["cells"] for code in cell["codes"])
    )
    codes.sort(key=lambda c: grade_for(c))
    for a, b in zip(codes, codes[1:]):
        aid, bid = (
            get_id("English Language Arts", a),
            get_id("English Language Arts", b),
        )
        if aid and bid:
            info = source_info(table_row["source"], table_row["page"] + 1)
            add(
                aid,
                bid,
                "FEEDS_INTO",
                info,
                f"PDF page {table_row['page'] + 1}, table {table_row['table'] + 1}, row {table_row['row'] + 1}: {a} and {b} occupy the same published vertical progression row. Recursive literacy support, not a mandatory lock.",
            )
# Explicit starred sequential lists become individual, evidence-bearing subskills.
subskill_lists = {
    "1.2.PWS.2": ["closed syllables", "open syllables"],
    "2.2.PWS.2": [
        "closed syllables",
        "open syllables",
        "vowel digraphs",
        "vowel-consonant-silent e syllables",
        "r-controlled syllables",
        "consonant + le syllables",
    ],
    "1.2.PWS.3": ["compound words", "inflectional endings"],
    "2.2.PWS.3": [
        "compound words",
        "inflectional endings",
        "contractions",
        "abbreviations",
        "common roots and related prefixes and suffixes",
    ],
    "1.2.SE.1": [
        "consonants",
        "short vowels",
        "digraphs",
        "consonant blends",
        "vowel-consonant-silent e",
    ],
    "2.2.SE.1": ["digraphs", "trigraphs", "vowel digraphs", "r-controlled"],
    "2.2.SE.2": [
        "closed syllables",
        "open syllables",
        "vowel-consonant-silent e syllables",
        "r-controlled syllables",
    ],
    "2.2.SE.3": [
        "common prefixes",
        "common suffixes",
        "common spelling rules for adding prefixes and suffixes",
    ],
}
for code, skills in subskill_lists.items():
    parent = by_subject["English Language Arts"][code]
    parent_id = identity(parent)
    page = 13 if ".PWS." in code else 14 if code != "2.2.SE.3" else 15
    # Source lists are letters A, B, ... and explicitly marked sequential skills.
    info = source_info("ela_pk5", page)
    ids = []
    for i, skill in enumerate(skills, 1):
        sid = parent_id + f"::step:{i}"
        ids.append(sid)
        new = json.loads(json.dumps(parent))
        new["standard_id"] = code + f"::step:{i}"
        new["standard_text"] = (
            ("Decode words using " if ".PWS." in code else "Spell words using ")
            + skill
            + "."
        )
        new["neo4j_node"]["properties"]["id"] = sid
        new["neo4j_node"]["properties"]["standard_id"] = new["standard_id"]
        new["authored_subskill"] = True
        new["official_parent_id"] = parent_id
        new["source_record"] = dict(text=new["standard_text"], **info)
        new["subskill_order"] = i
        rows.append(new)
    for i, (a, b) in enumerate(zip(ids, ids[1:]), 1):
        add(
            a,
            b,
            "PREREQUISITE_FOR",
            info,
            f"PDF page {page}: {code}, starred sequential skills, letter {chr(64 + i)} precedes {chr(65 + i)}. Local subskill IDs retain the published parent; they are not additional official OAS objectives.",
        )
    add(
        ids[-1],
        parent_id,
        "PREREQUISITE_FOR",
        info,
        f"PDF page {page}: {code} explicitly specifies a sequential skill list. Demonstrate the ordered component skills before the parent-level independent demonstration; component evidence alone does not award parent mastery.",
    )
# Preserve reviewed foundational edges from the recovered bundle, replacing flexible-only assumptions.
recovered = json.loads(
    (SEEDS / "progression_sources/foundational_review.json").read_text()
)["edges"]
known = {identity(r) for r in rows}
for edge in recovered:
    if edge["from_standard_id"] in known and edge["to_standard_id"] in known:
        key = (edge["from_standard_id"], edge["relation_type"], edge["to_standard_id"])
        edges.setdefault(key, edge)
# Audit all identities, with explicit contextual/legacy dispositions; no silently unreviewed nodes.
placements = {}
for row in rows:
    sid = identity(row)
    record = row.get("source_record")
    subject = row["subject"]
    code = row["standard_id"]
    if record:
        note = f"Published objective identity and text checked at PDF page {record['page']}; order in a standards document is not an instructional prerequisite."
        status = "VERIFIED_IDENTITY"
        if row.get("authored_subskill"):
            status = "VERIFIED_SUBSKILL"
            note = (
                "Locally identified subskill from an explicitly ordered published objective. "
                + note
            )
        lane = f"{row['track'].lower()}:{code.split('.')[0]}:{code.split('.')[1]}"
        mode = (
            "SEQUENTIAL"
            if subject in ("Mathematics", "English Language Arts")
            else "OPEN"
            if subject == "Social Studies"
            else "SCAFFOLDED"
        )
        if row.get("authored_subskill"):
            lane = f"{row['track'].lower()}:subskill:{row['official_parent_id']}"
        terminal = not any(
            other != code and other.startswith(code + ".")
            for other in by_subject[subject]
        )
        source = dict(
            source_title=record["title"],
            source_url=record["url"],
            source_version=record["version"],
        )
    else:
        status = "CONTEXTUAL" if subject not in by_subject else row["catalog_status"]
        mode = "OPEN"
        terminal = subject not in by_subject
        if (
            code.lower().startswith("standard ")
            or subject == "Mathematics"
            or subject == "Science"
            or subject == "English Language Arts"
        ):
            terminal = False
        lane = f"{row['track'].lower()}:context:{row['grade']}"
        source = dict(
            source_title="Dear Adeline retained curriculum catalog",
            source_url="https://github.com/amberdawn84ac-bot/dearadeline-withlove/blob/main/adeline-brain/data/seeds/oas_to_8track.json",
            source_version="2026-10-05 catalog audit",
        )
        note = "Reviewed as contextual curriculum or retained legacy/container identity. Not asserted to be a current official objective or a verified hard prerequisite. Preserve existing learner records."
    placements[sid] = dict(
        **source,
        review_status=status,
        mode=mode,
        lane=lane,
        terminal=terminal,
        parent_id=row.get("official_parent_id"),
        evidence_note=note,
        course=row.get("course", ""),
    )
for key in list(edges):
    if (
        not placements[edges[key]["from_standard_id"]]["terminal"]
        or not placements[edges[key]["to_standard_id"]]["terminal"]
    ):
        # Official parent of subskills remains a terminal parent-level demonstration.
        del edges[key]
base["meta"]["progression_audit_date"] = "2026-10-05"
base["mappings"] = rows
(SEEDS / "oas_to_8track.json").write_text(
    json.dumps(base, ensure_ascii=False, indent=2) + "\n"
)
(SEEDS / "verified_standard_progressions.json").write_text(
    json.dumps(
        dict(
            scope="Complete catalog review with source-verified identities, explicit instructional dependencies, flexible progressions, and contextual/retained dispositions. VERIFIED edges certify the cited relationship, not a state-mandated universal lesson order.",
            reviewed_at="2026-10-05",
            edges=list(edges.values()),
        ),
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
(SEEDS / "standard_progression_review.json").write_text(
    json.dumps(
        dict(
            reviewed_at="2026-10-05",
            standards=placements,
            source_counts={k: len(v) for k, v in source_catalog.items()},
            math_framework=math_review,
            unresolved_source_references=unresolved,
        ),
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
print(
    "catalog",
    len(rows),
    "edges",
    len(edges),
    collections.Counter(e["relation_type"] for e in edges.values()),
    "unresolved",
    len(unresolved),
    "audit",
    collections.Counter(r["review_status"] for r in placements.values()),
)

SCIENCE_SRC = args.science_directory
m = json.loads((SEEDS / "oas_to_8track.json").read_text())["mappings"]
by_code = {
    r["standard_id"]: r
    for r in m
    if r["subject"] == "Science" and r.get("source_record")
}
review = json.loads((SEEDS / "standard_progression_review.json").read_text())
bundle = json.loads((SEEDS / "verified_standard_progressions.json").read_text())
edges = {
    (e["from_standard_id"], e["relation_type"], e["to_standard_id"]): e
    for e in bundle["edges"]
}
snapshots = []
pdf = fitz.open(args.source_directory / "science2026.pdf")


def normalize(t):
    return re.sub(r"[^a-z0-9]+", "", t.lower().replace("&", "and"))


def matches_current_dimension(code, heading):
    text = pdf[by_code[code]["source_record"]["page"] - 1].get_text()
    label = re.sub(r"^\S+\s+", "", heading).strip()
    return bool(label) and normalize(label) in normalize(text)


pat = r"\b(?:K|[1-8]|PS|CH|PH|B|ES|EN|K2|35|MS|HS)\.(?:PS|LS|ESS|ETS)\d\.\d+\b"
for source in json.loads((SCIENCE_SRC / "index.json").read_text()):
    if "file" not in source:
        raise ValueError(source)
    raw = (SCIENCE_SRC / source["file"]).read_text()
    soup = BeautifulSoup(raw, "html.parser")
    heading = ""
    url = source["url"].replace("http://", "https://")
    for i, tr in enumerate(soup.select("tr")):
        cells = tr.find_all(["td", "th"], recursive=False)
        if len(cells) == 1 and cells[0].get("colspan") == "4":
            heading = cells[0].get_text(" ", strip=True)
        if len(cells) != 4 or any("Grades K-2" in c.get_text() for c in cells):
            continue
        bands = [
            sorted(set(re.findall(pat, c.get_text(" ", strip=True)))) for c in cells
        ]
        if not any(bands):
            continue
        snapshots.append(
            dict(
                url=url,
                sha256=hashlib.sha256(raw.encode()).hexdigest(),
                row=i + 1,
                dimension=heading,
                bands=bands,
            )
        )
        for a_band, b_band in zip(bands, bands[1:]):
            for a in a_band:
                for b in b_band:
                    if a not in by_code or b not in by_code or a == b:
                        continue
                    if not matches_current_dimension(
                        a, heading
                    ) or not matches_current_dimension(b, heading):
                        continue
                    aid = (
                        by_code[a].get("standard_node") or by_code[a].get("neo4j_node")
                    )["properties"]["id"]
                    bid = (
                        by_code[b].get("standard_node") or by_code[b].get("neo4j_node")
                    )["properties"]["id"]
                    key = (aid, "FEEDS_INTO", bid)
                    edges.setdefault(
                        key,
                        dict(
                            from_standard_id=aid,
                            to_standard_id=bid,
                            relation_type="FEEDS_INTO",
                            weight=0.5,
                            source_title=soup.title.get_text(),
                            source_url=url,
                            source_version="2020 learning progression; objective identities/text reviewed against 2026 OAS-S on 2026-10-05",
                            evidence_note=f"Published DCI table row {i + 1}, {heading}: {a} and {b} are explicitly referenced in adjacent grade-band cells. This verifies a flexible dimensional progression, not a claim that every earlier standard must be mastered before every later standard. Both identities were checked against 2026 OAS-S; changed meanings require new review.",
                            review_status="VERIFIED",
                        ),
                    )
bundle["edges"] = list(edges.values())
review["science_dimensions"] = snapshots
(SEEDS / "verified_standard_progressions.json").write_text(
    json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
)
(SEEDS / "standard_progression_review.json").write_text(
    json.dumps(review, ensure_ascii=False, indent=2) + "\n"
)
(SEEDS / "progression_sources/science_dimensions.json").write_text(
    json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n"
)
print(
    "science rows",
    len(snapshots),
    "science flexible edges",
    sum(e["from_standard_id"].startswith("SCIENC") for e in edges.values()),
    "total",
    len(edges),
)

inc = collections.Counter(
    e["to_standard_id"]
    for e in bundle["edges"]
    if e["relation_type"] == "PREREQUISITE_FOR"
)
support = collections.Counter(
    e["to_standard_id"] for e in bundle["edges"] if e["relation_type"] == "FEEDS_INTO"
)
for sid, row in review["standards"].items():
    row["dependency_disposition"] = (
        "NOT_ASSIGNABLE"
        if not row["terminal"]
        else "REVIEWED_PREREQUISITES"
        if inc[sid]
        else "FLEXIBLE_SUPPORT"
        if support[sid]
        else "DIAGNOSE_FOUNDATIONS"
    )
    row["prerequisite_count"] = inc[sid]
    row["support_count"] = support[sid]
(SEEDS / "standard_progression_review.json").write_text(
    json.dumps(review, ensure_ascii=False, indent=2) + "\n"
)
