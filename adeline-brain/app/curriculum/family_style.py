"""Family-style rules shared by canonical authoring and student adaptation."""

FAMILY_CANONICAL_AUTHORING_RULES = """
FAMILY-STYLE CANONICAL RULES (non-negotiable):
- Author the durable lesson at full adult/high-school depth. Do not lower or remove
  verified facts because the requesting learner is younger.
- Build one shared intellectual experience for the household: one story, inquiry,
  demonstration, discussion, or real project that learners can do together.
- Give learners different responsibility, not different disconnected lessons:
  upper-elementary learners notice, name, sequence, measure, draw, or narrate;
  middle-school learners explain mechanisms, compare evidence, and make connections;
  high-school learners evaluate sources, handle nuance, calculate, design, or lead synthesis.
- The shared work must culminate in something real: a model, map, experiment, record,
  performance, plan, service, or useful creation. No worksheets or decorative busywork.
- Each learner must be able to preserve an individual contribution as portfolio evidence.
- Keep facts, sources, central questions, and worldview fixed across ages. Adapt only
  vocabulary, scaffolding, independence, and depth of responsibility.
""".strip()


def family_workshop_block(topic: str) -> dict:
    """Return the stable one-room-schoolhouse spine stored with every canonical."""
    safe_topic = topic.strip() or "this topic"
    return {
        "block_type": "NARRATIVE",
        "content": (
            f"## Family workshop: {safe_topic}\n\n"
            "Gather around one shared question: **What is really happening here, how do we know, "
            "and what can our family make or do with that truth?** Use the lesson's story, sources, "
            "and demonstration together before anyone separates for individual work.\n\n"
            "**Younger contributors (roughly grades 4–5):** notice and name important details; "
            "sequence events or steps; measure, sketch, label, narrate, or build a concrete part.\n\n"
            "**Middle contributors (grades 6–8):** explain cause and effect or the central mechanism; "
            "compare evidence; record results; connect the lesson to another subject or real situation.\n\n"
            "**Older contributors (grades 9–12):** test claims and sources; handle exceptions and nuance; "
            "design the method, calculate where useful, or lead the family's final synthesis.\n\n"
            "**Make one real thing together.** Choose the form that fits the lesson—a model, map, "
            "experiment record, performance, plan, service, or useful creation. Each learner signs or "
            "labels the part they contributed and saves one photo, page, recording, explanation, or "
            "reflection as individual portfolio evidence."
        ),
        "evidence": [],
        "is_silenced": False,
        "homestead_content": None,
        "_enrichment": True,
        "family_style": True,
        "family_roles": {
            "upper_elementary": "notice, name, sequence, measure, sketch, narrate, or build",
            "middle_school": "explain, compare evidence, record results, and connect ideas",
            "high_school": "evaluate sources, handle nuance, design, calculate, and lead synthesis",
        },
        "portfolio_evidence": "Each learner preserves an identifiable contribution to the shared work.",
    }


def ensure_family_workshop(blocks: list[dict], topic: str) -> list[dict]:
    """Add exactly one family workshop without mutating the caller's list."""
    if any(block.get("family_style") for block in blocks):
        return list(blocks)
    return [*blocks, family_workshop_block(topic)]
