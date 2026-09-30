"""The Kitchen Case File — a family forensic-science investigation.

This is a repository canonical, served through CanonicalStore when the database
has not yet stored a copy. It is one shared experience, not a second author.

Campfire Curriculums' Forensic Science unit (12 lessons, four levels, about
four weeks) covers scene work, prints, trace, documents, impressions, blood
patterns, pathology, and DNA, often through true-crime cases. This unit covers
that scientific ground with a staged household mystery, public methods
documents, and no photographs or narratives of real victims. A kitchen cocoa
lift is practice. It is not a courtroom identification.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

from app.curriculum.canonical_author import (
    CONTRACT_VERSION,
    PROMPT_VERSION,
    validate_canonical_contract,
    validate_experience_substance,
    validate_flow_composition,
)
from app.curriculum.family_style import (
    CANONICAL_FORMAT_VERSION,
    finalize_family_lesson,
    is_current_family_canonical,
)

TOPIC = "The Kitchen Case File: What Can Household Evidence Actually Prove?"
TRACK = "CREATION_SCIENCE"
TITLE = "The Kitchen Case File"

ROLES = {
    "elementary": "Notice, count, sketch, and say only what you saw. Do not name a culprit.",
    "middle": "Measure, label, and write which observation supports which claim.",
    "high_school": "Separate observation, inference, and the unknown. Keep the chain of custody and say what this kitchen method cannot prove.",
}


def _slug(topic: str, track: str) -> str:
    raw = f"{topic.strip().lower()}:{track}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _block(
    block_id: str,
    block_type: str,
    stage: str,
    title: str,
    content: str,
    evidence: list[dict] | None = None,
) -> dict[str, Any]:
    return {
        "block_id": block_id,
        "block_type": block_type,
        "experience_stage": stage,
        "title": title,
        "content": content.strip(),
        "evidence": evidence or [],
        "family_style": True,
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
        "family_roles": dict(ROLES),
        "track": TRACK,
    }


def _source(
    *,
    title: str,
    url: str,
    holder: str,
    identifier: str,
    feature: str,
    claim: str,
) -> dict[str, str]:
    return {
        "source_title": title,
        "source_url": url,
        "holding_institution": holder,
        "item_identifier": identifier,
        "excerpt_or_observable_feature": feature,
        "claim_supported": claim,
    }


def _lessons() -> list[dict[str, Any]]:
    """Eight multi-day lessons. Twelve Campfire sittings collapse here because
    each lesson is a full kitchen session, not a one-page reading.
    """
    return [
        {
            "lesson_id": "scene",
            "title": "Secure the scene before you decide",
            "concept_ids": ["scene-security"],
            "block_ids": ["kcf-invite", "kcf-scene"],
            "individual_expectations": {
                "elementary": "Walk the boundary and sketch three things that are out of place. Do not say who did it.",
                "middle": "Write the first five observations and who has already touched the area.",
                "high_school": "Mark the boundary, start the custody log, and list what a later look can no longer prove.",
            },
        },
        {
            "lesson_id": "transfer",
            "title": "Contact leaves a trace",
            "concept_ids": ["transfer"],
            "block_ids": ["kcf-locard", "kcf-fibers"],
            "individual_expectations": {
                "elementary": "Press tape on a sleeve and count what stuck.",
                "middle": "Compare two tape lifts and say which surface gave up more material.",
                "high_school": "Explain why a trace shows contact happened, not why it happened or who meant it.",
            },
        },
        {
            "lesson_id": "prints",
            "title": "Friction ridge prints",
            "concept_ids": ["ridge-patterns"],
            "block_ids": ["kcf-prints-read", "kcf-prints-lab"],
            "individual_expectations": {
                "elementary": "Sort household prints into loops, whorls, and arches by looking.",
                "middle": "Lift one print with cocoa or cornstarch and tape, then compare it to a known card.",
                "high_school": "Use Analysis, Comparison, Evaluation, and say what Verification would still require.",
            },
        },
        {
            "lesson_id": "impressions",
            "title": "Shoe and tool impressions",
            "concept_ids": ["impressions"],
            "block_ids": ["kcf-impress-read", "kcf-shoe"],
            "individual_expectations": {
                "elementary": "Match a shoe to a print in flour or damp soil by shape.",
                "middle": "Measure length and one distinctive mark. Record the unit.",
                "high_school": "List class characteristics versus a feature that might individualize, and what the kitchen cast cannot do.",
            },
        },
        {
            "lesson_id": "documents",
            "title": "Notes, handwriting, and ink",
            "concept_ids": ["documents"],
            "block_ids": ["kcf-hand", "kcf-ink"],
            "individual_expectations": {
                "elementary": "Find three letters that look different between two writers.",
                "middle": "Run a coffee-filter ink test and record which colors traveled.",
                "high_school": "State which differences are observations and which are still a guess about authorship.",
            },
        },
        {
            "lesson_id": "droplets",
            "title": "Droplet physics without a crime",
            "concept_ids": ["droplet-physics"],
            "block_ids": ["kcf-drop-read", "kcf-drop-lab"],
            "individual_expectations": {
                "elementary": "Drop colored water from two heights and say which splash is wider.",
                "middle": "Measure diameters and keep height as the only change.",
                "high_school": "Explain why a kitchen splash does not reconstruct a violent event, and what a real analyst would still need.",
            },
        },
        {
            "lesson_id": "biology",
            "title": "What a cell can and cannot identify",
            "concept_ids": ["biological-limits"],
            "block_ids": ["kcf-dna-read", "kcf-strawberry"],
            "individual_expectations": {
                "elementary": "With an adult, mash a strawberry and point to the cloudy strands. Those strands are not a person's name.",
                "middle": "Write the difference between seeing DNA and matching a person.",
                "high_school": "Explain why a kitchen extraction is not a CODIS profile and what a lab must control before an identity claim.",
            },
        },
        {
            "lesson_id": "conference",
            "title": "Case conference",
            "concept_ids": ["claim-standards"],
            "block_ids": ["kcf-map", "kcf-verdict"],
            "individual_expectations": {
                "elementary": "Place each clue on the map as seen, guessed, or unknown.",
                "middle": "Defend one claim with two independent observations, or admit you have only one.",
                "high_school": "Write the finding the evidence supports, the allegation it does not, and what would change your mind.",
            },
        },
    ]


def _blocks() -> list[dict[str, Any]]:
    nij = _source(
        title="Crime Scene Investigation: Guides for Law Enforcement",
        url="https://nij.ojp.gov/topics/articles/crime-scene-investigation-guides-law-enforcement",
        holder="National Institute of Justice",
        identifier="NIJ topic article, published July 12, 2017, pointing at the law-enforcement scene guides",
        feature=(
            "The page says responders should treat the scene as their only chance to preserve and recover "
            "evidence, and that a careless search can contaminate or lose it."
        ),
        claim="A scene has to be secured and documented before people start explaining it.",
    )
    nist_prints = _source(
        title="Latent Print Examination and Human Factors (NISTIR 7842)",
        url="https://www.nist.gov/publications/latent-print-examination-and-human-factors-improving-practice-through-systems-approach",
        holder="National Institute of Standards and Technology",
        identifier="NISTIR 7842",
        feature=(
            "NIST convened an expert group because latent-print comparison is useful and also subject to "
            "human-factor error. The report covers the path from collecting a print to explaining a conclusion."
        ),
        claim="A fingerprint comparison is a human examination with a known risk of error, not magic proof.",
    )
    acev = _source(
        title="Latent Print Examination Process",
        url="https://ipm.nist.gov/lpe",
        holder="NIST / NIJ latent-print process map",
        identifier="ipm.nist.gov/lpe ACE-V map",
        feature=(
            "The page names the common examination sequence: Analysis, Comparison, Evaluation, and Verification. "
            "Verification means a second look, sometimes by someone who does not know the first result."
        ),
        claim="One person's glance at a kitchen lift is not a finished friction-ridge examination.",
    )
    genome = _source(
        title="Deoxyribonucleic Acid (DNA) Fact Sheet",
        url="https://www.genome.gov/about-genomics/fact-sheets/Deoxyribonucleic-Acid-Fact-Sheet",
        holder="National Human Genome Research Institute",
        identifier="genome.gov DNA fact sheet",
        feature=(
            "The fact sheet describes DNA as the molecule that carries genetic information in cells. "
            "Read it for what DNA is. Do not treat a strawberry mash as a human identification."
        ),
        claim="Seeing DNA is not the same as identifying a person.",
    )
    fbi_lab = _source(
        title="FBI Laboratory",
        url="https://www.fbi.gov/services/laboratory",
        holder="Federal Bureau of Investigation",
        identifier="fbi.gov/services/laboratory",
        feature=(
            "The FBI Laboratory page is the public front door for the lab that examines evidence for "
            "investigations. A home kitchen is not that lab and does not enter a profile into its systems."
        ),
        claim="Identity claims from biological evidence belong to a controlled laboratory process.",
    )
    scripture = _source(
        title="Deuteronomy 19:15",
        url="https://www.sefaria.org/Deuteronomy.19.15",
        holder="Sefaria",
        identifier="Deuteronomy 19:15",
        feature=(
            "Read the verse in Everett Fox on Sefaria if that translation is available for the verse, "
            "and in a second translation beside it. The legal rule is that one witness does not establish "
            "the matter. The King James text, which is public domain, says a matter is established at the "
            "mouth of two or three witnesses. Do not paste a longer copyrighted translation into the case file."
        ),
        claim="One clue, like one witness, does not establish what happened.",
    )
    return [
        _block(
            "kcf-invite",
            "TEXT",
            "INVITATION",
            "Something in this house was moved",
            """
A jar, a gate, a note, or a tool is not where the family left it. Before anyone argues, the family becomes the scene team.

This is not a story about a real victim. Do not use photographs of real injuries, do not stage blood, and do not pick a child to be "the criminal." A parent may plant one agreed clue, or the family may investigate something that actually moved. Anyone may sit out.

The question for the whole unit: what can the traces in this house prove, and what are we only guessing?

Materials for the month, gathered once: cocoa or cornstarch, a soft brush, clear tape, white paper, a pencil, a ruler, a magnifier if you have one, coffee filters, washable markers, a cup of water, flour or a patch of damp soil, food coloring or beet juice, a strawberry, dish soap, salt, a zip bag, and rubbing alcohol that only an adult handles.

Deuteronomy 19:15 is the rule of the case file. Read it on Sefaria. One witness does not settle a charge. Two or three independent lines of evidence might. A confession the group pressures out of somebody is not evidence.
            """,
            [scripture],
        ),
        _block(
            "kcf-scene",
            "LAB_MISSION",
            "ACTION",
            "Boundary, sketch, and custody log",
            """
Do this before anyone cleans.

1. Agree on the scene. A counter, a doorway, or the missing jar is enough.
2. Mark a boundary with tape or chairs. People who are not recording stay outside it.
3. Elementary: sketch the scene and label three things. No names of suspects on the sketch.
4. Middle: list the first five observations as "I see," not "so-and-so must have."
5. Older: open a custody log with columns for item, who touched it, when, and where it is kept now.
6. Photograph the scene before anything is picked up. The photo is portfolio evidence only if the log says who took it.

Read the National Institute of Justice page together. Their point is practical: if you tramp through the scene, you may destroy the only record. Write one sentence on what your family already disturbed before the log started.
            """,
            [nij],
        ),
        _block(
            "kcf-locard",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "Locard's idea, tested instead of quoted",
            """
Edmond Locard, working in Lyon in the early twentieth century, taught that contact between a person and a place leaves a transfer of material. That sentence is the family's working hypothesis, not a magic spell and not a quotation invented for this lesson. You are going to test the idea with tape.

Do not claim a specific historical experiment, statistic, or Locard sentence you have not opened. If an older learner wants Locard's own wording, find a library copy and copy the sentence with the page. Until then, the case file says "attributed to Locard" and then shows your own tape lifts.

Also read the NIJ scene guide page already in the file. Transfer and contamination are the same idea from two sides: material moves onto the scene, and the investigators bring material in.
            """,
            [nij],
        ),
        _block(
            "kcf-fibers",
            "EXPERIMENT",
            "ACTION",
            "Tape lifts from two surfaces",
            """
Change one thing: the surface.

Press a fresh piece of clear tape on a sleeve, then a second fresh piece on the floor or a rug. Stick each tape on white paper. Label them before you leave the table.

Elementary: count specks or fibers on each square.
Middle: which surface left more, and what colors do you actually see?
Older: write the hypothesis you had before you looked, then what the tapes show, then one way the test could fool you (dirty tape, a sleeve that was just outside, tape that touched the table).

The tapes go in the custody log. A fiber shows that something touched that surface or that the tape touched something. It does not name a person and it does not prove a motive.
            """,
        ),
        _block(
            "kcf-prints-read",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "Ridges, and the human doing the comparing",
            """
Friction ridge skin leaves prints. Loops, whorls, and arches are class patterns. They narrow a comparison. They are not, by themselves, a name.

Open the NIST process map at https://ipm.nist.gov/lpe and read the four words: Analysis, Comparison, Evaluation, Verification. Analysis is studying the unknown print first. Comparison is side by side. Evaluation is the conclusion. Verification is another examiner.

Then open NISTIR 7842's publication page. The reason that report exists is that print examiners are people, and people can be wrong. Your cocoa lift is for learning the steps. It is not an identification you may say out loud as fact.
            """,
            [nist_prints, acev],
        ),
        _block(
            "kcf-prints-lab",
            "LAB_MISSION",
            "ACTION",
            "A cocoa lift against known cards",
            """
Each person who agrees rolls or presses one known print on white paper and signs that card. Those are exemplars.

On a clean glass, one person — or the parent, if a clue was planted — leaves a print. Dust lightly with cocoa or cornstarch and a soft brush. Press tape over it and move the tape to contrasting paper. Label it "unknown."

Elementary: which class pattern do you see on the unknown, if the lift is clear enough to say?
Middle: put the unknown next to each exemplar. Where do ridges agree, and where does the lift smudge?
Older: stop after Evaluation and write "not verified." Name what a second person would need to see before you would say "this matches."

If the lift is bad, record the bad lift. A failed lift is data. Do not invent a match to finish the lesson.
            """,
            [acev],
        ),
        _block(
            "kcf-impress-read",
            "TEXT",
            "DISCOVERY",
            "Class and individual marks",
            """
A shoe print has class characteristics: size range, general tread family. It may also have a cut, a nail, or a worn spot. That second kind of mark is what examiners hope will tie a print to one shoe. A flour print in a kitchen rarely captures that much.

Outside investigators cast prints so the record survives. You will photograph and measure instead of pouring plaster unless an adult already knows how. Do not track mud through the house to make the scene "more real."
            """,
        ),
        _block(
            "kcf-shoe",
            "EXPERIMENT",
            "ACTION",
            "One print, every shoe that might fit",
            """
Make one print in flour on a tray or in a small patch of damp soil. Photograph it with the ruler in the frame before anyone steps again.

Elementary: line up family shoes and set aside the ones that are obviously the wrong shape.
Middle: measure the print length and each candidate shoe. Write the numbers. A difference of a size is a difference. A matching length is not a conviction.
Older: circle one feature that many shoes share and one feature, if any, that only one shoe has. If you cannot find the second, the honest finding is "consistent with these shoes" or "not excluded," not "this person walked here."

Log who made the test print if you know, and keep that name off the conclusion line until the comparison is done blind if you can stand to do it that way.
            """,
        ),
        _block(
            "kcf-hand",
            "TEXT",
            "DISCOVERY",
            "Handwriting is a comparison, not a hunch",
            """
Ask two willing people to write the same sentence on separate cards: "The jar was moved before breakfast." Add one unsigned card written by one of them. Mix the unsigned card in without telling the youngest who wrote it.

Look at letter height, slant, and how a letter like "a" or "g" is formed. Three differences are more interesting than a feeling that it "looks like" someone.

Do not use a ransom note from a real case, or a picture of a harmed child, as the sample. Those cases are not required to learn comparison, and they do not belong in this family lesson.

A handwriting opinion from the kitchen is practice. Document examiners use known samples taken on purpose, and they still talk about limitations.
            """,
        ),
        _block(
            "kcf-ink",
            "EXPERIMENT",
            "ACTION",
            "Which ink traveled",
            """
Cut a coffee filter into strips. Draw a short line with a different washable marker on each strip, about two centimeters from the bottom. Hang the strips so the tips touch water and the ink line stays above the water. Wait.

Elementary: name the colors that appear as the water climbs.
Middle: two markers that look like the same black may split into different colors. Record that if it happens, and record it if it does not.
Older: this is chromatography, a separation. It can show that two inks behave differently. It cannot show who held the pen.

Stop the test while the colors are still on the paper. Dry the strips and put them in the case file.
            """,
        ),
        _block(
            "kcf-drop-read",
            "TEXT",
            "DISCOVERY",
            "A splash is physics",
            """
Real laboratories study bloodstain patterns because drop size, height, angle, and surface change the stain. That work is specialized, and pictures of real blood from real injuries are not part of this unit.

You will use colored water or beet juice on paper you can throw away. One variable: height. Same dropper, same surface, same amount as nearly as you can.

You may not conclude that a person was struck, how many times, or where they stood. If a show or a worksheet invites that conclusion from a cartoon splatter, the case file's answer is: the picture does not contain those facts.
            """,
        ),
        _block(
            "kcf-drop-lab",
            "EXPERIMENT",
            "ACTION",
            "Two heights, one surface",
            """
Cover a table. Drop colored water from knee height and from as high as an adult can hold the dropper over the same kind of paper. Use at least three drops at each height.

Elementary: which group of spots looks wider?
Middle: measure two diameters in each group with the ruler and write the numbers beside a sketch.
Older: say what you held constant and what you failed to hold constant (drop size is hard). Then write the sentence you are not allowed to write: anything about a weapon or an injury.

Wash hands. The paper can be photographed and discarded. It is not biohazard, and it should not be talked about as if it were.
            """,
        ),
        _block(
            "kcf-dna-read",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "DNA is a molecule. A profile is a lab claim.",
            """
Read the National Human Genome Research Institute DNA fact sheet far enough to say what DNA is in your own words.

Then open the FBI Laboratory's public page. That is a laboratory with controlled methods. The combined DNA index the FBI runs is not a zip-bag experiment, and this lesson will not pretend you produced a profile or a match statistic.

A strawberry is a useful cell because it is easy to mash and has a lot of DNA. The strands you may see are strawberry DNA. They do not identify a member of this household. Hair, a drink glass, or a "touch" sample in a real case also does not identify anyone until a lab does work you are not equipped to do.

If an older learner wants the limit in one sentence: a visible extraction shows that DNA was present in the cells you broke open. It does not show whose cells, and it does not show what anyone did.
            """,
            [genome, fbi_lab],
        ),
        _block(
            "kcf-strawberry",
            "LAB_MISSION",
            "ACTION",
            "Strawberry extraction, adult on the alcohol",
            """
An adult measures the rubbing alcohol and keeps it off skin, eyes, and flame. Cold alcohol works better if you can set the bottle in ice first.

Mash one strawberry in a bag with a spoon of dish soap and a pinch of salt. Add a little water. Filter the liquid through a coffee filter into a cup. Adult pours cold alcohol slowly down the side so it forms a layer. Wait and watch for cloudy strands.

Elementary: point to the strands and say "DNA from the strawberry," not "I found the culprit."
Middle: write the steps you actually did, including anything you spilled or skipped.
Older: list two controls a forensic lab would add that you did not have (known samples, a clean blank, a method that compares specific regions rather than a visible glob).

No meat, no blood, and no "time of death." If you want a time question this week, photograph one cut apple each day and describe only what the apple did. That is decay you can see. It is not forensic entomology and it does not date an event.
            """,
            [genome],
        ),
        _block(
            "kcf-map",
            "CONCEPT_MAP",
            "CREATION",
            "The case map",
            """
On one large sheet, make three columns: Seen, Inferred, Unknown.

Every lift, print, measurement, chromatogram, sketch, and photo goes in Seen, with the custody-log line next to it.
Inferred holds only claims that cite at least two Seen items.
Unknown holds the rest, including anything the family wants to be true.

Elementary places the objects. Middle writes the citations on the Seen cards. Older checks that nothing in Inferred rests on a single card, a hunch, or a person who got tired of being questioned.

This sheet is the shared family product. It is done when a claim can be pointed at, not when the group agrees.
            """,
            [scripture],
        ),
        _block(
            "kcf-verdict",
            "QUIZ",
            "DEMONSTRATION",
            "What the file actually supports",
            """
Answer in the case file. A parent reviews the answers against the map. Credit follows the artifacts, not a click.

1. What is one observation nobody in the family disputes? Point to the sketch, photo, or lift.
2. What is one inference that has two independent observations behind it? Name both.
3. What did someone suggest that the file does not support?
4. Which kitchen method was the weakest, and what would you change if you repeated it?
5. Where did Deuteronomy 19:15 stop the family from treating one clue as proof?

Do not award a "solved" sticker. The passing demonstration is a case file a skeptical sibling can check.
            """,
            [scripture, nij],
        ),
    ]


def _payload() -> dict[str, Any]:
    lessons = _lessons()
    blocks = _blocks()
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"dearadeline:{TOPIC}:{TRACK}")),
        "topic": TOPIC,
        "track": TRACK,
        "title": TITLE,
        "big_question": "What can the traces in this house prove, and what are we only guessing?",
        "learning_goal": (
            "The family can secure a small scene, collect household traces, and sort every claim "
            "into what was seen, what was inferred from at least two observations, and what is still unknown."
        ),
        "shared_experience": (
            "One household mystery, one custody log, and one case map. Siblings do not get separate fake crime stories."
        ),
        "unit_plan": {
            "essential_concepts": [
                {
                    "concept_id": "scene-security",
                    "name": "Secure and document a scene before interpreting it",
                    "introduced_in_lesson_id": "scene",
                    "demonstrated_in_lesson_ids": ["scene"],
                },
                {
                    "concept_id": "transfer",
                    "name": "Contact can transfer material, and investigators can contaminate a scene",
                    "introduced_in_lesson_id": "transfer",
                    "demonstrated_in_lesson_ids": ["transfer"],
                },
                {
                    "concept_id": "ridge-patterns",
                    "name": "Friction-ridge comparison is a stepwise human examination",
                    "introduced_in_lesson_id": "prints",
                    "demonstrated_in_lesson_ids": ["prints"],
                },
                {
                    "concept_id": "impressions",
                    "name": "Impression evidence has class features and rarely a true individual feature at home",
                    "introduced_in_lesson_id": "impressions",
                    "demonstrated_in_lesson_ids": ["impressions"],
                },
                {
                    "concept_id": "documents",
                    "name": "Handwriting and ink comparisons describe differences without inventing an author",
                    "introduced_in_lesson_id": "documents",
                    "demonstrated_in_lesson_ids": ["documents"],
                },
                {
                    "concept_id": "droplet-physics",
                    "name": "Drop height changes a splash, and a splash is not a reconstruction of violence",
                    "introduced_in_lesson_id": "droplets",
                    "demonstrated_in_lesson_ids": ["droplets"],
                },
                {
                    "concept_id": "biological-limits",
                    "name": "A visible DNA extraction is not a human identification",
                    "introduced_in_lesson_id": "biology",
                    "demonstrated_in_lesson_ids": ["biology"],
                },
                {
                    "concept_id": "claim-standards",
                    "name": "A claim needs independent support, and one witness does not establish it",
                    "introduced_in_lesson_id": "conference",
                    "demonstrated_in_lesson_ids": ["conference"],
                },
            ],
            "lessons": lessons,
            "lesson_count_rationale": (
                "Eight lessons cover the Campfire forensic scope — scene, transfer, prints, impressions, "
                "documents, pattern physics, biological identity, and a closing judgment — as multi-day "
                "kitchen sessions across about four weeks. Pathology and famous criminal cases are omitted "
                "on purpose: a cut apple can show change over time, and a real victim is not curriculum material "
                "for this age span. More lessons would repeat the same claim-standard rather than add a method."
            ),
        },
        "experience_design": {
            "primary_mode": "investigation",
            "layout": "dossier",
            "entry_move": "The family finds one thing in the house disturbed and may not name a culprit until the case map has two independent observations.",
            "central_question": "What can household evidence actually prove?",
            "disciplines_integrated": [
                "CREATION_SCIENCE",
                "APPLIED_MATHEMATICS",
                "JUSTICE_CHANGEMAKING",
                "DISCIPLESHIP",
                "ENGLISH_LITERATURE",
            ],
            "integration_rationale": (
                "The methods are scientific observation and measurement. The lengths and droplet diameters are mathematics. "
                "The rule that one witness does not establish a charge is both a biblical legal standard and a justice standard. "
                "Writing the custody log and the finding is English. None of those is a themed worksheet bolted on."
            ),
            "flow": [
                {"id": "flow-scene", "title": "Secure the scene", "block_ids": ["kcf-invite", "kcf-scene"]},
                {"id": "flow-transfer", "title": "Transfer", "block_ids": ["kcf-locard", "kcf-fibers"]},
                {"id": "flow-prints", "title": "Prints", "block_ids": ["kcf-prints-read", "kcf-prints-lab"]},
                {"id": "flow-impressions", "title": "Impressions", "block_ids": ["kcf-impress-read", "kcf-shoe"]},
                {"id": "flow-documents", "title": "Documents", "block_ids": ["kcf-hand", "kcf-ink"]},
                {"id": "flow-droplets", "title": "Droplets", "block_ids": ["kcf-drop-read", "kcf-drop-lab"]},
                {"id": "flow-biology", "title": "Biological limits", "block_ids": ["kcf-dna-read", "kcf-strawberry"]},
                {"id": "flow-conference", "title": "Case conference", "block_ids": ["kcf-map", "kcf-verdict"]},
            ],
        },
        "family_discussion": {
            "launch": "Walk to the disturbed thing. Nobody names a person until the boundary is marked and the first photo is taken.",
            "questions": [
                "What did we already change before the log started?",
                "Which claim on the map has two independent observations, and which claim has only a feeling?",
            ],
            "synthesis_prompt": "Read the Seen, Inferred, and Unknown columns out loud and strike any inferred claim that has only one card under it.",
        },
        "real_world_task": {
            "description": "Investigate one real or parent-planted household disturbance with scene notes, lifts, measurements, and a custody log.",
            "deliverable": "A case map that sorts every clue into seen, inferred from at least two observations, or unknown.",
            "shared_family_component": "One scene, one log, and one map for the whole household.",
        },
        "portfolio_task": {
            "process_evidence": [
                "Custody log",
                "Scene sketch and first photograph",
                "Failed lifts as well as clear ones",
            ],
            "product_evidence": [
                "Tape lifts, chromatogram, and measured droplet sketch",
                "Case map with Seen, Inferred, and Unknown",
            ],
            "failure_and_revision_evidence": [
                "A note on which method was too weak to support a claim and what the family would repeat",
            ],
        },
        "mastery_evidence_map": [
            {
                "concept": "scene-security",
                "discipline_or_track": TRACK,
                "acceptable_evidence": ["Boundary sketch plus a custody log that names who touched the scene"],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            },
            {
                "concept": "transfer",
                "discipline_or_track": TRACK,
                "acceptable_evidence": ["Two labeled tape lifts and a sentence limiting what a fiber can prove"],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            },
            {
                "concept": "ridge-patterns",
                "discipline_or_track": TRACK,
                "acceptable_evidence": ["Unknown lift compared to exemplars with an explicit not-verified stop"],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            },
            {
                "concept": "impressions",
                "discipline_or_track": TRACK,
                "acceptable_evidence": ["Measured print and shoe comparison that refuses a single-shoe conviction without an individual feature"],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            },
            {
                "concept": "documents",
                "discipline_or_track": TRACK,
                "acceptable_evidence": ["Handwriting differences list and a dried chromatogram"],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            },
            {
                "concept": "droplet-physics",
                "discipline_or_track": TRACK,
                "acceptable_evidence": ["Two-height measurement sketch that states what was held constant"],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            },
            {
                "concept": "biological-limits",
                "discipline_or_track": TRACK,
                "acceptable_evidence": ["Strawberry extraction notes that distinguish visible DNA from a human identity claim"],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            },
            {
                "concept": "claim-standards",
                "discipline_or_track": TRACK,
                "acceptable_evidence": ["Case conference answers checked against the map by another household member"],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            },
        ],
        "adaptation_contract": [
            "Change vocabulary and how much of the log a learner writes alone. Do not change the scene, the sources, or the rule that one clue is not proof.",
            "Younger learners notice, count, and place cards. They are not assigned a culprit or a graphic case.",
            "Older learners write limitations and measurements. They do not receive a more violent version of the same mystery.",
            "Never add a real victim, a staged injury, or a famous criminal case as the 'advanced' text.",
        ],
        "family_roles": ROLES,
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "blocks": blocks,
    }


def build_kitchen_case_canonical() -> dict[str, Any]:
    """Return a store-ready canonical. Raises if the unit violates the contract."""
    payload = _payload()
    finalized, errors = finalize_family_lesson(payload["blocks"], TOPIC, track=TRACK)
    if errors:
        raise RuntimeError("Kitchen Case File failed family validation: " + "; ".join(errors))
    payload["blocks"] = finalized
    contract_errors = []
    contract_errors.extend(validate_canonical_contract(payload))
    contract_errors.extend(validate_flow_composition(payload))
    contract_errors.extend(validate_experience_substance(payload))
    if contract_errors:
        raise RuntimeError("Kitchen Case File failed canonical contract: " + "; ".join(contract_errors))
    if not is_current_family_canonical(payload["blocks"]):
        raise RuntimeError("Kitchen Case File is not a current family canonical")

    payload["blocks"][0].setdefault("metadata", {})["canonical_contract"] = {
        key: payload.get(key)
        for key in (
            "big_question",
            "learning_goal",
            "shared_experience",
            "unit_plan",
            "experience_design",
            "family_discussion",
            "real_world_task",
            "portfolio_task",
            "mastery_evidence_map",
            "family_roles",
            "contract_version",
            "prompt_version",
        )
    }
    slug = _slug(TOPIC, TRACK)
    return {
        "id": payload["id"],
        "topic_slug": slug,
        "topic": TOPIC,
        "track": TRACK,
        "title": TITLE,
        "blocks": payload["blocks"],
        "oas_standards": [],
        "researcher_activated": False,
        "agent_name": "Canonical Experience Author",
        "pending_approval": False,
        "needs_review_reason": None,
    }
