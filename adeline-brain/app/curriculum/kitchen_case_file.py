"""Forensic science — the real work, for the whole family.

Repository canonical, served through CanonicalStore. One shared experience,
not a second author and not a younger edition with the subject removed.

Campfire Curriculums' Forensic Science unit is the scope: crime scene,
investigation, fingerprints, bloodstain patterns, questioned documents,
impression evidence, pathology, entomology, trace DNA, and a finale, about
four weeks, one family, different amounts of writing by age. The household
labs practice the measurements. They do not replace the career or the cases.
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
TITLE = "Forensic Science"
CONTENT_REVISION = "kitchen-case-file-v4"

ROLES = {
    "elementary": "Do the same investigation as everyone else. Measure, name the job, and write only what you saw. You may write less. You do not get a version with the death, the blood, or the insects taken out.",
    "middle": "Record the numbers, the custody line, and what the result can and cannot prove.",
    "high_school": "Read the source, state the limit of the method, and write what you would and would not say in court.",
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
        "metadata": {
            "parent_directed": True,
            "content_revision": CONTENT_REVISION,
        },
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


_FAITH_TALKS = {
    "scene": "Deuteronomy 19:15. One witness cannot establish a matter. The boundary exists so a later witness still has something true to see.",
    "investigation": "Who held the evidence is part of whether the testimony is clean. An unlogged hand is a witness you cannot question.",
    "prints": "A confident name is not a second witness. The Mayfield identification was wrong.",
    "blood": "Measure what you can see. Do not testify to a story the stain cannot carry.",
    "documents": "The letters you can point to are the testimony. A guess about who wrote them is not.",
    "impressions": "The ruler in the photograph is what lets someone else check your claim.",
    "pathology": "Cause and manner are not a verdict. The autopsy does not convict anyone.",
    "entomology": "Write the insects and the temperature you actually saw. An invented hour is a false witness.",
    "dna": "A profile can free someone as well as implicate someone. That is part of telling the truth.",
    "conference": "Say only the finding two observations can carry. Refuse the rest.",
}

_THINK_TANKS = {
    "scene": "What can a later person no longer prove if someone already walked through?",
    "investigation": "What happens to the lab's claim if one hand on the evidence was never written down?",
    "prints": "Where does ACE-V require you to stop before you say it is a match?",
    "blood": "What does the angle tell you, and what does this board refuse to reconstruct?",
    "documents": "Which marks did you see, and which claim about the writer are you not allowed to make?",
    "impressions": "Which features are shared by a whole kind of shoe, and which one might belong to only this shoe?",
    "pathology": "What can a pathologist decide, and what is still a question for the court?",
    "entomology": "Why will an entomologist not give you an hour without the species and the temperature?",
    "dna": "Who did the profile include, who did it exclude, and what did it not prove by itself?",
    "conference": "Which claim would you say under oath, and which claim do you have only one observation for?",
}


def _lessons() -> list[dict[str, Any]]:
    """Ten lessons, about four weeks. Campfire's table of contents is the job list."""
    bands = (
        ("scene", "The crime scene", "scene-security", ["kcf-invite", "kcf-scene"],
         "Walk the boundary and sketch what you see. Name who is allowed inside.",
         "Start the log: time, place, and who has already touched the area.",
         "Mark the boundary, take the first photographs, and write what a later look can no longer prove."),
        ("investigation", "Who works a scene", "investigation-roles", ["kcf-team", "kcf-custody"],
         "Name four jobs: patrol officer, crime scene investigator, detective, medical examiner.",
         "Write a chain-of-custody line for one item: who, when, what, and why.",
         "Explain how one unlogged touch changes what the lab can say."),
        ("prints", "Latent prints", "ridge-patterns", ["kcf-prints-read", "kcf-prints-lab"],
         "Sort prints into loops, whorls, and arches. Lift one with powder and tape.",
         "Compare the unknown lift to known cards and stop before you say it is a match.",
         "Tell the Brandon Mayfield case: the FBI identified a print and was wrong. Name the ACE-V steps."),
        ("blood", "Bloodstain patterns", "bloodstain", ["kcf-blood-read", "kcf-blood-lab"],
         "Drop simulated blood from two heights and onto a slant. Say which stain is rounder.",
         "Measure width and length in millimeters. Keep height or angle as the only change.",
         "Use width divided by length as the sine of the impact angle, and state what a kitchen board cannot reconstruct."),
        ("documents", "Questioned documents", "documents", ["kcf-docs-read", "kcf-docs-lab"],
         "Find three letters that differ between two writers of the same sentence.",
         "Run the ink test and record which colors traveled, including a test that does not split.",
         "Separate observations from a guess about who wrote it. Name the document examiner's job."),
        ("impressions", "Shoe, tire, and tool marks", "impressions", ["kcf-impress-read", "kcf-shoe"],
         "Match a shoe to a print by shape. Photograph it with the ruler in the frame.",
         "Measure length and one distinctive mark. Record the unit.",
         "Separate class characteristics from a feature that might individualize, and say what this cast cannot do."),
        ("pathology", "Forensic pathology", "pathology", ["kcf-path-read", "kcf-path-lab"],
         "For each practice card, say the cause and the manner in a short sentence.",
         "Write cause and manner, and one thing the pathologist still cannot decide.",
         "Explain cause versus manner, coroner versus medical examiner, and why the autopsy does not convict anyone."),
        ("entomology", "Forensic entomology", "entomology", ["kcf-ent-read", "kcf-ent-lab"],
         "Photograph the jar each day and write what insects you see and the temperature.",
         "Describe the order you actually saw. Do not invent a clock.",
         "Explain why species and temperature are required before anyone estimates a postmortem interval."),
        ("dna", "DNA analysis", "dna-identity", ["kcf-dna-read", "kcf-dna-lab"],
         "Point to the strawberry strands and say they are DNA. Name one person a DNA test excluded and one it included.",
         "Write the difference between seeing DNA and a forensic profile that includes or excludes a person.",
         "Explain Pitchfork, Buckland, and why a profile can free someone as well as implicate someone."),
        ("conference", "What you would testify", "claim-standards", ["kcf-map", "kcf-verdict"],
         "Put each result on the map as seen, inferred, or unknown.",
         "Defend one claim with two independent observations, or admit you have only one.",
         "Write the finding you would testify to, the claim you would refuse, and what would change your mind."),
    )
    lessons = []
    for lesson_id, title, concept_id, block_ids, elementary, middle, high_school in bands:
        lessons.append({
            "lesson_id": lesson_id,
            "title": title,
            "concept_ids": [concept_id],
            "block_ids": block_ids,
            "individual_expectations": {
                "elementary": elementary,
                "middle": middle,
                "high_school": high_school,
            },
            "stages": [
                {"stage":"READ", "block_ids":[block_ids[0]], "prompt":""},
                {"stage":"EXPLORE", "block_ids":[], "prompt":_THINK_TANKS[lesson_id]},
                {"stage":"WRITE", "block_ids":[], "prompt":"Record the observation and its limits in your own words while the evidence is open.", "evidence_required":["notes"]},
                {"stage":"APPLY", "block_ids":[], "prompt":middle},
                {"stage":"EXPERIENCE", "block_ids":[block_ids[1]], "prompt":"", "activity":middle, "evidence_required":["observation, measurement or artifact"]},
            ],
            "faith_talk": _FAITH_TALKS[lesson_id],
            "think_tank": _THINK_TANKS[lesson_id],
        })
    return lessons


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
        claim="A crime scene has to be secured and documented before anyone explains it.",
    )
    nist_prints = _source(
        title="Latent Print Examination and Human Factors (NISTIR 7842)",
        url="https://www.nist.gov/publications/latent-print-examination-and-human-factors-improving-practice-through-systems-approach",
        holder="National Institute of Standards and Technology",
        identifier="NISTIR 7842",
        feature=(
            "The publication is a systems study of latent-print examination. The field commissioned it "
            "because examiners are people and people can be wrong."
        ),
        claim="A fingerprint identification is a human conclusion, and it can be false.",
    )
    nist_bpa = _source(
        title="OSAC Bloodstain Pattern Analysis Subcommittee",
        url="https://www.nist.gov/osac/subcommittees/bloodstain-pattern-analysis",
        holder="National Institute of Standards and Technology",
        identifier="OSAC Bloodstain Pattern Analysis Subcommittee",
        feature=(
            "The page says the subcommittee focuses on standards for the scientific detection and analysis "
            "of bloodstain patterns at crime scenes, and it lists a training standard for bloodstain pattern analysts."
        ),
        claim="Bloodstain pattern analysis is a real forensic job with training standards, not a classroom metaphor.",
    )
    nist_docs = _source(
        title="OSAC Forensic Document Examination Subcommittee",
        url="https://www.nist.gov/osac/subcommittees/forensic-document-examination",
        holder="National Institute of Standards and Technology",
        identifier="OSAC Forensic Document Examination Subcommittee",
        feature=(
            "The page says the subcommittee focuses on standards for the forensic analysis, comparison, "
            "and evaluation of documents."
        ),
        claim="Comparing handwriting and ink is a forensic discipline with its own standards.",
    )
    name = _source(
        title="Applying and Matching to Forensic Pathology Fellowships",
        url="https://www.thename.org/applying-matching-to-forensic-pathology-fellowships",
        holder="National Association of Medical Examiners",
        identifier="NAME fellowship page",
        feature=(
            "The page says forensic pathology is the medical subspecialty focused on death investigations "
            "and on diagnosing the disease and injuries that led to death, and that the fellowship requires "
            "more than 200 autopsies in a year."
        ),
        claim="A forensic pathologist is a physician who investigates deaths and performs autopsies. It is a career with a training path.",
    )
    nij_flies = _source(
        title="Estimating Blow Fly Age and Reducing Error in Postmortem Interval Cases",
        url="https://nij.ojp.gov/media/video/estimating-blow-fly-age-reducing-error-postmortem-interval-cases",
        holder="National Institute of Justice",
        identifier="NIJ Forensic Technology Center of Excellence webinar, October 24, 2018",
        feature=(
            "The page says insect evidence can provide information in death investigations, and that "
            "forensic entomologists estimate the ages of immature insects such as blow flies to inform timelines."
        ),
        claim="Forensic entomologists use insect development, especially blow flies, when estimating time since death, and that estimate has error.",
    )
    nhgri = _source(
        title="Deoxyribonucleic Acid (DNA) Fact Sheet",
        url="https://www.genome.gov/about-genomics/fact-sheets/Deoxyribonucleic-Acid-Fact-Sheet",
        holder="National Human Genome Research Institute",
        identifier="NHGRI DNA fact sheet",
        feature="The fact sheet describes DNA as the molecule that carries genetic information in living things.",
        claim="The strands in a kitchen extraction are DNA, the molecule. They are not a person's name.",
    )
    fbi = _source(
        title="Science and Technology",
        url="https://www.fbi.gov/investigate/how-we-investigate/science-and-technology",
        holder="Federal Bureau of Investigation",
        identifier="FBI Laboratory public description",
        feature=(
            "The page says the FBI Laboratory examines DNA and fingerprints left at a crime scene, and that "
            "DNA testing results from evidence are compared to DNA from known people."
        ),
        claim="Forensic DNA work compares evidence to known people. It is a laboratory job, not a strawberry mash.",
    )
    nas = _source(
        title="Strengthening Forensic Science in the United States: A Path Forward",
        url="https://nap.nationalacademies.org/catalog/12589/strengthening-forensic-science-in-the-united-states-a-path-forward",
        holder="National Academies Press",
        identifier="National Research Council, 2009",
        feature=(
            "The catalog description says many dedicated people do vitally important forensic work, and that "
            "change is needed in a number of disciplines to ensure reliability, enforceable standards, and consistent practice."
        ),
        claim="Forensic methods are real and uneven. Some are stronger than others, and an examiner's confidence is not the same as proof.",
    )
    scripture = _source(
        title="Deuteronomy 19:15",
        url="https://www.sefaria.org/Deuteronomy.19.15",
        holder="Sefaria",
        identifier="Deuteronomy 19:15",
        feature=(
            "The verse says one witness shall not rise up against a person for any iniquity. "
            "A matter is established at the mouth of two or three witnesses."
        ),
        claim="One print, one stain, one fly, or one lab result does not establish what happened.",
    )

    return [
        _block(
            "kcf-invite",
            "TEXT",
            "INVITATION",
            "This is the job",
            """
Stand at a doorway and don't touch anything yet. On the other side of a real door, in a real case, that is where the job starts. Crime scene investigators, latent print examiners, bloodstain pattern analysts, document examiners, forensic pathologists, forensic entomologists, and DNA analysts walk into deaths and crimes and then have to say, under oath, what the evidence can actually prove.

You are going to practice their measurements in this house. Cocoa or fingerprint powder. Tape. A ruler. Simulated blood, which is corn syrup, water, and red food coloring, because human blood can carry disease. An adult may use blood from a butcher if you want the real thickness. Ink. A shoe print. A strawberry. A jar of meat or liver, because insects come to a body and an entomologist has to be able to watch that happen. Gloves are laboratory safety. They are not a nicer version of the subject.

Younger learners write less of the same file. Nobody gets a copy with the deaths, the blood, or the insects taken out. A parent decides which photographs are in the room. The science stays.

Open one case file for the whole family. Every photograph, lift, measurement, and conclusion goes in it. Deuteronomy 19:15 is the rule you will use, not a verse for the end of the day: one witness does not establish a matter. A single print, stain, or fly is one witness.

The month needs tape, paper, a pencil, a ruler, a camera, cocoa or fingerprint powder, a soft brush, clear tape, white cards, corn syrup, water, red food coloring, a dropper, a board you can prop up, gloves, coffee filters, washable markers, flour or damp soil, a strawberry, dish soap, salt, a zip bag, rubbing alcohol that only an adult handles, a small piece of meat or liver, a screened container, and a thermometer if you have one. Open the file and begin.
            """,
            [scripture],
        ),
        _block(
            "kcf-scene",
            "LAB_MISSION",
            "ACTION",
            "Secure a scene",
            """
Use a real disturbance in the house or one a parent sets. Do not clean it up first.

1. Nobody interprets until the first record exists.
2. Mark a boundary with tape or chairs. People who are not logging stay outside it.
3. Photograph the scene before anyone moves an object. Put a ruler in at least one frame.
4. Sketch the room. Elementary labels three things that are out of place. Middle adds measurements. Older notes what the photograph cannot show, including smells and what was already moved.
5. Start the custody log: date, time, address or room, and every person who enters.

This is what a crime scene investigator does before a detective has a theory. The first officers protect the scene. The investigator records it. A theory that arrives before the photographs is a way to miss what is there.

Write one sentence: what did we already change before the log started?
            """,
            [nij],
        ),
        _block(
            "kcf-team",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "The people who arrive",
            """
Read the National Institute of Justice page on crime scene investigation. The point of the guides is blunt: the scene is the chance to recover the evidence, and a careless search can contaminate it or lose it.

These are different jobs. Do not collapse them into one "detective."

- A patrol officer is often first. The job is to keep people from walking through the evidence, get medical help to the living, and hold the scene.
- A crime scene investigator photographs, sketches, searches, and collects. Many are not the person who will later do the laboratory comparison.
- A detective interviews, builds the timeline, and decides what else to ask for. An interview is not a laboratory result.
- A medic treats the injured. Treatment can move evidence. That is written down, not resented.
- A medical examiner or coroner has the death. In many places the medical examiner is a physician. In some counties a coroner is elected and is not a doctor. Learn which system your state uses. That is part of the career, because it changes who is allowed to sign the death.
- The laboratory — fingerprints, firearms, DNA, documents, toxicology — often never sees the room. They see what was collected, labeled, and sealed.

Open the NIJ page and write two sentences in the case file: what the guides say happens if the scene is searched carelessly, and which of the jobs above you would want if you were the one who had died.
            """,
            [nij],
        ),
        _block(
            "kcf-custody",
            "LAB_MISSION",
            "ACTION",
            "Chain of custody",
            """
Pick one item from the scene: a cup, a note, a fiber on tape, a shoe. Bag it or tape it to a card. The label needs the item, the place, the date, the time, and the collector's name.

Pass it to a second person. They sign the log with the time they received it. Then have a third person touch it without signing. Put that failure in the log too.

A chain of custody is the list of every person who held the evidence. If the list has a gap, a lawyer can ask whether the item in court is the item from the scene. Sometimes the answer is that nobody knows. That is a real way cases fail.

Elementary writes the four lines of the label. Middle writes both transfers, including the unsigned one. Older writes what a laboratory may no longer claim about that item.

The item stays in the case file. Do not "clean it up" and keep the claim.
            """,
            [nij],
        ),
        _block(
            "kcf-prints-read",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "What a print examiner actually does",
            """
Friction ridge skin — the raised lines on fingers, palms, and soles — leaves prints. Loops, whorls, and arches are class patterns. They narrow a comparison. They do not name a person by themselves.

Latent print examiners use ACE-V: Analysis, Comparison, Evaluation, and Verification by a second examiner. Open the NIST publication page for NISTIR 7842. The report exists because examination is done by people, and people can be wrong even when they feel certain.

The public example is Brandon Mayfield. On March 11, 2004, bombs on commuter trains in Madrid killed nearly two hundred people. The FBI identified a latent print from a bag of detonators as Mayfield's. He is a lawyer in Oregon. He was held as a material witness. The Spanish National Police did not agree with the identification. The FBI withdrew it. Mayfield had not done it.

Read that as a job fact, not as a scary story. A print examiner's conclusion can be false. Verification is part of the method because of cases like this one. Your lift this week is the same kind of comparison, without a second qualified examiner and without a court. You do not get to say you identified anyone.
            """,
            [nist_prints],
        ),
        _block(
            "kcf-prints-lab",
            "LAB_MISSION",
            "ACTION",
            "Lift a print and stop at the right place",
            """
On a clean glass, one person leaves a print. Dust it lightly with cocoa, cornstarch, or real fingerprint powder and a soft brush. Press clear tape over it and move the tape to contrasting paper. Label it "unknown," with the date and the surface.

Each person makes a known card: ink or powder on paper, rolled if you can, labeled with the person's name. Sort what you see into loops, whorls, and arches.

Elementary sorts and labels. Middle lines the unknown up against the known cards and writes which features look similar and which do not. Older writes the ACE-V steps and stops at Evaluation with the words "not verified." Then write one sentence about Mayfield: an identification was made, and it was wrong.

A cocoa lift is practice of the real method. It is not a weaker subject. It is also not an identification you may say out loud as fact.
            """,
            [nist_prints],
        ),
        _block(
            "kcf-blood-read",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "Bloodstain pattern analysis",
            """
Bloodstain pattern analysts study the shapes blood makes when a person is bleeding. The blood is real blood from an injury, including injuries that kill. The patterns have names because the physics differs:

- Drip stains fall from a person or an object that is not moving much. Drop them from higher and they often make a wider stain or more satellites.
- A transfer stain is left when a bloody surface touches another surface. A hand, a knife, a sleeve.
- Impact spatter is made when a force hits blood and breaks it into small drops. The drops travel and hit a surface.
- Cast-off is blood flung from a swinging object.
- Expirated blood is blown out of a nose or mouth.
- Arterial bleeding can leave a series of spurts.

Analysts measure. A drop that hits straight down is rounder. A drop that hits at a slant is longer. Width divided by length is the sine of the angle of impact. From several stains, an analyst may estimate where the blood was when it started moving. That estimate is an area, not a movie of the crime.

Open the NIST page for the OSAC Bloodstain Pattern Analysis Subcommittee. There is a training standard for this job because it is a job. Also open the 2009 National Academies report, Strengthening Forensic Science in the United States. Its description says change is needed in a number of forensic disciplines so the work is reliable. Bloodstain pattern testimony has been used in court beyond what the measurements can hold. You will learn the measurements and the limit in the same lesson.

Do not go looking for photographs of dead people as the assignment. A parent may show a textbook photograph if they choose. The classification and the formula do not require one.
            """,
            [nist_bpa, nas],
        ),
        _block(
            "kcf-blood-lab",
            "EXPERIMENT",
            "ACTION",
            "Measure stains",
            """
Gloves on. Cover the table. Mix simulated blood: about four parts corn syrup, one part water, and red food coloring, until it drops slowly from a spoon. An adult may use blood from a butcher instead. Do not use human blood.

Hold the dropper the same way each time.

Trial A: ten drops onto flat paper from 10 centimeters, and ten from 80 centimeters. Elementary says which group is wider. Middle measures two diameters in each group with the ruler and writes the numbers. Older states what was held constant.

Trial B: prop a board at a slant. Drop from one height onto the slant and onto flat paper. Measure the width and the length of two stains in each group, in millimeters. Older learners divide width by length. That number is the sine of the impact angle. A number near 1 is close to straight down. A smaller number is a sharper slant. If you have not learned sine yet, write the two measurements and say the angle is still unknown.

Draw the stains. Label drip versus the slanted impacts. Write one sentence a bloodstain analyst would be willing to say, and one sentence they should refuse. "This drop fell from higher" can be a careful claim if that was your only change. "This is how the person was killed" is not a claim this board can support.

Wash the table. The stains go in the case file.
            """,
            [nist_bpa],
        ),
        _block(
            "kcf-docs-read",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "Forensic document examination",
            """
Forensic document examiners compare handwriting, signatures, ink, paper, and alterations. Some work in police labs. Some work for the Secret Service, because documents include threats and financial instruments, not only notes from a crime scene. Open the NIST page for the OSAC Forensic Document Examination Subcommittee and write what it says the subcommittee is for: standards for analysis, comparison, and evaluation of documents.

Handwriting comparison looks at letter construction, slant, size, spacing, and how a writer starts and stops a stroke. Three differences you can point at are more useful than a feeling that it "looks like" someone. Examiners want known writing from the same era, written the way the questioned writing was written, not a signature scrawled once on a card.

Ink can be compared. A kitchen chromatography test is the same idea as a lab separation: different dyes travel different distances in a solvent. It will not name a pen brand unless you have the known pen and the result actually distinguishes them.

A document opinion from this table is practice. It is the real kind of comparison. It is not a courtroom identification.
            """,
            [nist_docs],
        ),
        _block(
            "kcf-docs-lab",
            "EXPERIMENT",
            "ACTION",
            "Handwriting and ink",
            """
Ask two willing people to write the same sentence on separate cards: "The jar was moved before anyone wrote it down." They should write at the same speed, with the same kind of pen if you can.

Look at letter height, slant, and how "a" or "g" is made. Elementary finds three differences and points at them. Middle lists them in the case file. Older marks which differences are observations and which would still be a guess about authorship.

Cut a coffee filter into strips. Draw a short line with a different washable marker on each strip, about two centimeters from the bottom. Hang the strips so the tips touch water and the ink line stays above the water. Wait. Middle records which colors traveled, and records it if two markers do not separate. Older writes what a document examiner would still need before saying two inks are the same ink.

Do not use a note from a real killing, or a picture of a harmed child, as the sample. You do not need someone else's tragedy to learn comparison. If a parent wants a real questioned document, use a public court exhibit they have read, and keep the writing samples in this house as the lab.
            """,
            [nist_docs],
        ),
        _block(
            "kcf-impress-read",
            "TEXT",
            "DISCOVERY",
            "Impressions",
            """
Footwear, tire, and toolmark examiners compare a mark at a scene to an object that might have made it. The National Institute of Justice scene guides treat these as evidence to photograph and collect before they are walked on or moved.

A shoe print has class characteristics: length, general tread family, a size range. Many shoes share those. It may also have a cut, a nail, a stone in the tread, or a worn spot. Examiners hope that second kind of mark ties a print to one shoe. A print in flour often never captures it. Saying "this is his shoe" from length alone is the mistake.

Toolmarks and tires work the same way. Class first. Individual only if the mark actually shows it. Photograph with a ruler in the same plane as the print before anyone casts it or steps again. A cast you make at home is practice of the record, not a laboratory comparison.
            """,
            [nij],
        ),
        _block(
            "kcf-shoe",
            "EXPERIMENT",
            "ACTION",
            "One print, with a scale",
            """
Make one shoe print in flour on a tray or in damp soil outside. Photograph it with the ruler in the frame before anyone steps again. Then set the shoe next to the photograph, not in the print.

Elementary matches by overall shape and says whether it could be that shoe. Middle measures the print length and the shoe length in the same unit and writes one distinctive mark if there is one. Older lists the class characteristics and any feature that might individualize, then writes the sentence they would refuse: a conviction, or even a firm identification, from this print alone.

If you have a tire or a tool and a safe way to make a mark in soft material, add one. Same rule. Photograph first. Class before individual.
            """,
            [nij],
        ),
        _block(
            "kcf-path-read",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "Forensic pathology",
            """
A forensic pathologist is a physician. Open the National Association of Medical Examiners page on forensic pathology fellowships. It says this subspecialty is focused on death investigations and on diagnosing the disease and the injuries that led to death. The fellowship requires more than 200 autopsies in a year, after medical school and a pathology residency. That is the training. It is not a costume.

An autopsy is an examination of a dead person. The pathologist looks at the outside of the body, the clothing, and the injuries, then at the organs, and takes specimens — blood, urine, fluid from the eye, and tissue — for toxicology and microscopy. The point is to find the cause of death and to document what the body shows. It is medical work. It is supposed to be careful, not entertainment.

Cause of death is the disease or injury: a blocked coronary artery, a blunt injury from a crash, a gunshot wound of the chest. Manner of death is the class the investigation supports. In the United States the manners are natural, accident, suicide, homicide, and undetermined. Suicide means the person acted with the intent to die. You do not need a method to learn that category. Homicide, as a manner, means the death was caused by another person. It is not the same word as murder. Murder is a legal judgment. A pathologist does not convict anyone.

A coroner and a medical examiner are not the same office in every state. Look up Oklahoma, or whichever state you live in, and write who is allowed to investigate a death where you are.

The National Academies report belongs in this lesson too. Death investigation has to be reliable. A dramatic conclusion is not better than an honest "undetermined."
            """,
            [name, nas],
        ),
        _block(
            "kcf-path-lab",
            "LAB_MISSION",
            "ACTION",
            "Cause and manner",
            """
These are practice cards, not real people. Write cause and manner for each one. Elementary uses one sentence. Middle adds what the pathologist cannot decide. Older says what further test or record would change the manner.

1. An older person dies at home. The autopsy finds a blocked coronary artery and scar in the heart muscle. There is no injury. Cause: atherosclerotic heart disease, or "heart disease" if you have not learned the longer name. Manner: natural.

2. A driver dies after a car leaves the road. The injuries are the kind a crash produces. No disease explains the death. Cause: blunt injury. Manner: accident, unless other evidence shows the car was forced off the road. If you do not have that evidence, say what is missing.

3. A person dies of a gunshot wound of the chest. Someone else has been arrested. Cause: gunshot wound of the chest. Manner: homicide. The pathologist still cannot say whether it was murder, self-defense, or an accident the court must sort out. Arrest is not an autopsy finding.

4. A person is found dead. The autopsy does not show a disease or an injury that explains it, and the laboratory tests are not back. Manner: undetermined. Leaving it there is competent work.

Put the four cards in the case file. If you want the real office, look up the medical examiner or coroner who serves your county and write what a forensic pathologist does there. You are not asking them for a case file on a named person.
            """,
            [name],
        ),
        _block(
            "kcf-ent-read",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "Insects and time since death",
            """
Forensic entomologists collect insects from a body and from the scene. Blow flies are often among the first. Eggs, maggots, and pupae develop on a schedule that depends on the species and the temperature. Open the National Institute of Justice page on estimating blow fly age. It says insect evidence can inform timelines in death investigations, and that entomologists estimate the age of immature blow flies. It also exists because that estimate has error that has to be reduced, not ignored.

A postmortem interval is an estimate of time since death. Insects actually estimate time since the insects arrived, which is not always the moment of death. A body indoors, a body buried, a cold night, or a wound that gives flies a place to lay eggs can change the clock. Species matters. "A fly" is not an identification.

This is a career. It is also biology you can watch. The next block is a real succession, on meat, because that is the process. It will not date a human death. It will show you why an entomologist refuses a number without species and temperature.
            """,
            [nij_flies],
        ),
        _block(
            "kcf-ent-lab",
            "LAB_MISSION",
            "ACTION",
            "A succession jar",
            """
An adult sets this up. Use a small piece of meat or liver from the grocery store, not a person and not a picture of a person. Put it in a container with a screen so animals cannot take it and insects can still reach it. Set it outside, out of the way. Wash hands. Do not bring the jar to the table where you eat.

Each day for as many days as the family can stand, photograph it and write the temperature if you have a thermometer, or the weather if you do not. Elementary names what is there in plain words: adult flies, eggs, maggots, or nothing yet. Middle writes the order you actually observed. Older writes why this jar is not a postmortem interval: you may not know the species, you may not have an hourly temperature record, and meat in a yard is not a human body at a scene.

If the family will not keep a meat jar, do not substitute a cute object and pretend it is the same science. Instead, take the NIJ page and write what an entomologist would have to know before giving a time. That is still the lesson. The jar is better if you can do it.

No one invents a time of death from a single photograph of one insect.
            """,
            [nij_flies],
        ),
        _block(
            "kcf-dna-read",
            "PRIMARY_SOURCE",
            "DISCOVERY",
            "What a DNA analyst can say",
            """
Open the NHGRI fact sheet. DNA is the molecule that carries genetic information. You can pull a visible tangle of it out of a strawberry. That tangle is strawberry DNA. It does not identify anyone in this house.

Forensic DNA analysis is a different task. The FBI Laboratory compares DNA testing results from evidence to DNA from known people. Read that sentence on the FBI science and technology page and copy it into the case file. Analysts use specific places in the genome, not a picture of cloudy strands. A profile can include a person, exclude a person, or be too weak or too mixed to answer.

The case that made this a job is real. In England, Lynda Mann and Dawn Ashworth, both fifteen, were murdered in 1983 and 1986 near Narborough. Richard Buckland confessed to one of the killings. Alec Jeffreys' DNA method excluded him. The same method included Colin Pitchfork, who was convicted in 1988. DNA kept a false confession from becoming the whole case, and it identified the man the court convicted. You do not need the details of the killings to understand the science. The girls were real, the exclusion was real, and the inclusion was real.

The other half of the career is the person the wrong method convicted. DNA testing has freed people who were imprisoned for crimes they did not commit. A method that can only accuse is not the job. Write both uses in the case file.

Trace DNA, the small amount that can be left by touch, is easier to move and easier to over-claim than a large blood stain. Contamination is a laboratory problem, which is why the custody log from the first week still matters here.
            """,
            [nhgri, fbi],
        ),
        _block(
            "kcf-dna-lab",
            "LAB_MISSION",
            "ACTION",
            "See the molecule, then say what a profile is",
            """
An adult measures the rubbing alcohol and keeps it off skin, eyes, and flame. Cold alcohol works better if the bottle has been in ice.

Mash one strawberry in a bag with a spoon of dish soap and a pinch of salt. Add a little water. Filter the liquid through a coffee filter into a cup. The adult pours cold alcohol slowly down the side so it forms a layer. Wait and watch for cloudy strands.

Elementary points at the strands and says "strawberry DNA," then says one sentence about the English case: the test excluded one man and included another. Middle writes the difference between seeing DNA and matching a person. Older writes why this extraction is not a forensic profile: no measured locations, no known sample to compare, no laboratory controls, and a strawberry is not a crime-scene stain.

The National Academies report is the high-school reading for this week. The catalog page says advancements are needed so forensic work is reliable. DNA, done properly, is one of the stronger tools. It is still one witness. Deuteronomy 19:15 does not step aside because the witness is a laboratory.
            """,
            [nhgri, fbi, nas, scripture],
        ),
        _block(
            "kcf-map",
            "CONCEPT_MAP",
            "CREATION",
            "Seen, inferred, unknown",
            """
Build one map for the whole family. Three columns.

Seen: the photograph, the lift, the measurements, the custody line, the insect log, the cause-and-manner cards, the strawberry notes. If it was not recorded, it does not go here.

Inferred: a claim that cites at least two Seen items. "The print and the shoe are the same length" can live here if both measurements are in Seen. "He did it" almost certainly cannot.

Unknown: everything else, including what the family wants to be true.

Elementary places the objects. Middle writes the citations on the Seen cards. Older checks that nothing in Inferred rests on a single card.

Add the jobs next to the evidence they own: scene investigator, print examiner, bloodstain analyst, document examiner, footwear examiner, forensic pathologist, forensic entomologist, DNA analyst. A claim with no job attached is a hint that nobody is actually qualified to say it, including this family.

This sheet is the shared product. It is done when a claim can be pointed at, not when the group agrees.
            """,
            [scripture, nas],
        ),
        _block(
            "kcf-verdict",
            "QUIZ",
            "DEMONSTRATION",
            "What you would say under oath",
            """
Answer in the case file. Another person in the house checks the answers against the map. Credit follows the artifacts, not a click and not a story.

1. Name the job that owns one piece of evidence you collected, and what that person is allowed to say about it.
2. What is one observation nobody disputes? Point to the sketch, photo, lift, measurement, or log.
3. What is one inference with two independent observations behind it? Name both. If you do not have one, say so.
4. Using the Madrid identification or the Pitchfork case, explain one time forensic science was wrong or one time it kept a false confession from standing. Ages and names, not a retelling of the violence.
5. Give cause and manner for one pathology card, and state what the pathologist still cannot decide.
6. Where did one witness fail to establish the matter? Use Deuteronomy 19:15 on your own evidence.

Do not award a solved sticker. The passing demonstration is a case file a skeptical sibling can check, from a learner who can say what the evidence does not prove.
            """,
            [scripture, nist_prints, nas],
        ),
    ]


def _payload() -> dict[str, Any]:
    lessons = _lessons()
    blocks = _blocks()
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"dearadeline:{TOPIC}:{TRACK}:{CONTENT_REVISION}")),
        "topic": TOPIC,
        "track": TRACK,
        "title": TITLE,
        "big_question": "What can forensic science actually prove about what happened, and where does the proof stop?",
        "learning_goal": (
            "The family can practice the core work of a forensic investigation — scene security, chain of custody, "
            "prints, bloodstain measurement, documents, impressions, cause and manner of death, insect evidence, and DNA — "
            "name the career that owns each part, and show what a single result cannot prove."
        ),
        "shared_experience": (
            "One case file for the whole household. Same deaths, same evidence, and same careers. "
            "Younger learners write less of that file. They do not receive a different subject."
        ),
        "unit_plan": {
            "essential_concepts": [
                {
                    "concept_id": lesson["concept_ids"][0],
                    "name": lesson["title"],
                    "introduced_in_lesson_id": lesson["lesson_id"],
                    "demonstrated_in_lesson_ids": [lesson["lesson_id"]],
                }
                for lesson in lessons
            ],
            "lessons": lessons,
            "lesson_count_rationale": (
                "Ten lessons match the Campfire forensic scope as careers: scene, investigation, fingerprints, "
                "bloodstain patterns, documents, impressions, pathology, entomology, DNA, and a closing testimony. "
                "About four weeks. Household labs practice the real measurements. They do not replace the work."
            ),
        },
        "experience_design": {
            "primary_mode": "investigation",
            "layout": "dossier",
            "entry_move": "The family opens one case file and secures a scene before anyone names a person or a cause.",
            "central_question": "What can forensic science actually prove, and where does one result stop being proof?",
            "disciplines_integrated": [
                "CREATION_SCIENCE",
                "APPLIED_MATHEMATICS",
                "JUSTICE_CHANGEMAKING",
                "DISCIPLESHIP",
                "ENGLISH_LITERATURE",
            ],
            "integration_rationale": (
                "The methods are observation and measurement, including the angle of a bloodstain. "
                "Naming cause and manner, and refusing a single witness, is both science and justice. "
                "Deuteronomy 19:15 is the legal standard the case file uses. Writing the log and the finding is English."
            ),
            "flow": [
                {"id": "flow-scene", "title": "The crime scene", "block_ids": ["kcf-invite", "kcf-scene"]},
                {"id": "flow-investigation", "title": "Who works a scene", "block_ids": ["kcf-team", "kcf-custody"]},
                {"id": "flow-prints", "title": "Latent prints", "block_ids": ["kcf-prints-read", "kcf-prints-lab"]},
                {"id": "flow-blood", "title": "Bloodstain patterns", "block_ids": ["kcf-blood-read", "kcf-blood-lab"]},
                {"id": "flow-documents", "title": "Questioned documents", "block_ids": ["kcf-docs-read", "kcf-docs-lab"]},
                {"id": "flow-impressions", "title": "Impressions", "block_ids": ["kcf-impress-read", "kcf-shoe"]},
                {"id": "flow-pathology", "title": "Forensic pathology", "block_ids": ["kcf-path-read", "kcf-path-lab"]},
                {"id": "flow-entomology", "title": "Forensic entomology", "block_ids": ["kcf-ent-read", "kcf-ent-lab"]},
                {"id": "flow-dna", "title": "DNA analysis", "block_ids": ["kcf-dna-read", "kcf-dna-lab"]},
                {"id": "flow-conference", "title": "Testimony", "block_ids": ["kcf-map", "kcf-verdict"]},
            ],
        },
        "family_discussion": {
            "launch": "Open the case file at the scene. Nobody names a suspect, a cause, or a time of death until the first photograph and the log exist.",
            "questions": [
                "Which job owns this result, and what is that person allowed to say?",
                "Which claim has two independent observations, and which claim has only one?",
            ],
            "synthesis_prompt": "Read Seen, Inferred, and Unknown aloud. Strike any inferred claim with only one card under it, including a claim everyone likes.",
        },
        "real_world_task": {
            "description": "Investigate one real or parent-set scene with the methods forensic scientists use, and classify practice deaths by cause and manner.",
            "deliverable": "A case file and a Seen / Inferred / Unknown map a skeptical sibling can check.",
            "shared_family_component": "One scene, one log, one map, and the same facts for every age.",
        },
        "portfolio_task": {
            "process_evidence": [
                "Custody log, including at least one gap or contamination the family recorded on purpose",
                "Scene sketch and first photograph",
                "Failed lifts and stains as well as clear ones",
            ],
            "product_evidence": [
                "Print lift, measured bloodstains, chromatogram, scaled shoe photograph, insect log, cause-and-manner cards",
                "Case map with Seen, Inferred, and Unknown",
            ],
            "failure_and_revision_evidence": [
                "A note on which method was too weak to support a claim, tied to Mayfield, the Academies report, or the family's own bad lift",
            ],
        },
        "mastery_evidence_map": [
            {
                "concept": lesson["concept_ids"][0],
                "discipline_or_track": TRACK,
                "acceptable_evidence": [lesson["individual_expectations"]["middle"]],
                "must_be_demonstrated_by_individual": True,
                "not_awarded_for_exposure_alone": True,
            }
            for lesson in lessons
        ],
        "adaptation_contract": [
            "Change how much a learner writes alone. Do not change the science, the cases, the sources, or the rule that one clue is not proof.",
            "Do not produce a younger edition that removes death investigation, blood, autopsy, insects, or a real case. Write less. Do not hide the work.",
            "Elementary learners measure, name the job, and say only what they saw. They are not assigned a culprit, and they are not given a pretend mystery.",
            "Older learners compute, read the limits in the sources, and write what an examiner may not say in court.",
            "Simulated blood or butcher blood is laboratory safety because human blood can carry disease. It is not a softer subject.",
        ],
        "family_roles": ROLES,
        "contract_version": CONTRACT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "blocks": blocks,
    }


def build_kitchen_case_canonical() -> dict[str, Any]:
    """Return a store-ready canonical. Raises if the unit violates the contract."""
    payload = _payload()
    payload["curriculum_contract_version"] = 1  # whole-unit compatibility record
    finalized, errors = finalize_family_lesson(payload["blocks"], TOPIC, track=TRACK)
    if errors:
        raise RuntimeError("Forensic science unit failed family validation: " + "; ".join(errors))
    payload["blocks"] = finalized
    contract_errors = []
    contract_errors.extend(validate_canonical_contract(payload))
    contract_errors.extend(validate_flow_composition(payload))
    contract_errors.extend(validate_experience_substance(payload))
    if contract_errors:
        raise RuntimeError("Forensic science unit failed canonical contract: " + "; ".join(contract_errors))
    if not is_current_family_canonical(payload["blocks"]):
        raise RuntimeError("Forensic science unit is not a current family canonical")

    payload["blocks"][0].setdefault("metadata", {})["canonical_contract"] = {
        key: payload.get(key)
        for key in (
            "big_question",
            "learning_goal",
            "shared_experience",
            "curriculum_contract_version",
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
    payload["blocks"][0]["metadata"]["content_revision"] = CONTENT_REVISION
    payload["blocks"][0]["metadata"]["parent_directed"] = True
    slug = _slug(TOPIC, TRACK)
    return {
        "id": payload["id"],
        "content_revision": CONTENT_REVISION,
        "stages": [stage for lesson in payload["unit_plan"]["lessons"] for stage in lesson["stages"]],
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
