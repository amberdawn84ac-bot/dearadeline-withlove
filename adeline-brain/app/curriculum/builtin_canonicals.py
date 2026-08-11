"""Approved canonicals shipped with the application for instant, reliable access.

These are not generic fallback messages. They are complete teaching copies reviewed as
part of the repository. The database may supersede them with an approved canonical using
the same topic slug.
"""
from __future__ import annotations

import uuid
import hashlib
from typing import Any


def _block(title: str, content: str, block_type: str = "NARRATIVE") -> dict[str, Any]:
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"dear-adeline:children-history:{title}")),
        "block_type": block_type,
        "title": title,
        "content": content.strip(),
    }


CHILDREN_WHO_CHANGED_HISTORY = {
    "id": "builtin-children-who-changed-history-v1",
    "topic": "Children Who Changed History",
    "track": "JUSTICE_CHANGEMAKING",
    "title": "Children Who Changed History",
    "blocks": [
        _block(
            "History has never belonged only to adults",
            """
Children are often described as people who will change the future. History shows
something stronger: young people have already changed their own present. They noticed
barriers adults had accepted, made a brave and useful move, and worked with families,
teachers, courts, journalists, or communities until that action became lasting change.

Keep one pathway in mind throughout this lesson: barrier → action → allies and
institutions → lasting change. Courage matters, but courage becomes history through a
pathway.
""",
        ),
        _block(
            "Louis Braille: turning exclusion into a language",
            """
Louis Braille was born in France in 1809 and lost his sight after a childhood accident.
The raised-letter books available to blind students were enormous, slow to read, and did
not give students a practical way to write. At twelve, Louis learned about a twelve-dot
military code called night writing. By fifteen, he had redesigned it as compact six-dot
cells that could be read by touch.

His system was resisted by authorities and was officially adopted at his school only
after his death. Braille shows that the people living with a problem may understand the
best solution before an institution is willing to change.
""",
        ),
        _block(
            "Claudette Colvin: the teenager history nearly left out",
            """
On March 2, 1955, fifteen-year-old Claudette Colvin refused to give her Montgomery bus
seat to a white passenger and was arrested—nine months before Rosa Parks. Colvin later
became one of four plaintiffs in Browder v. Gayle, the federal case that ended legal bus
segregation in Montgomery in 1956.

Movement leaders chose Rosa Parks as the public face of the boycott because they believed
an adult with her reputation would be harder for segregationists to attack. That strategy
helped the campaign, but it also minimized Colvin's role for decades. History is shaped by
what happened and by which stories institutions repeat.
""",
            "PRIMARY_SOURCE",
        ),
        _block(
            "Ruby Bridges: when a court ruling had to become real",
            """
On November 14, 1960, six-year-old Ruby Bridges entered William Frantz Elementary School
in New Orleans under federal marshal protection. The Supreme Court had already ruled
school segregation unconstitutional, but a legal decision did not automatically change
daily life. White parents withdrew children, crowds threatened Ruby, and Barbara Henry
taught her alone for a time.

Ruby did not write the court order or command the marshals. Her importance is that the law
meant little until a real child walked through the door. Legal victory, enforcement,
supportive adults, and personal courage were separate necessary steps.
""",
        ),
        _block(
            "Samantha Smith: a question across the Cold War",
            """
In 1982, ten-year-old Samantha Smith wrote to Soviet leader Yuri Andropov while families
feared nuclear war. She asked whether frightening claims about the Soviet Union were true
and what he would do to prevent war. Andropov replied and invited her to visit in 1983.

Samantha did not end the Cold War, and governments used publicity for their own purposes.
Her contribution was citizen diplomacy: she asked a direct human question when powerful
institutions mostly communicated through threats. Curiosity can interrupt propaganda,
but it must remain alert to how power uses a story.
""",
            "PRIMARY_SOURCE",
        ),
        _block(
            "Malala Yousafzai: documenting what power wanted hidden",
            """
When the Pakistani Taliban restricted girls' education in the Swat Valley, Malala
Yousafzai spoke publicly and, at eleven, wrote an anonymous BBC Urdu diary about life
under their rule. A gunman shot her on a school bus in 2012 when she was fifteen. She
survived and continued advocating for education; at seventeen she became the youngest
Nobel Peace Prize laureate.

Malala's fame did not single-handedly create safe schools. Students, parents, teachers,
local leaders, money, and law all matter. Responsible history honors a visible symbol
without erasing the wider movement that makes structural change possible.
""",
        ),
        _block(
            "Build the change pathway together",
            """
Make one shared family wall with five rows: Louis, Claudette, Ruby, Samantha, and Malala.
For each person, add four stops: barrier → brave action → allies or institutions → lasting
change. Younger learners draw and retell one pathway. Middle learners label risks, causes,
and consequences. Older learners add a primary or near-primary source and identify what
the familiar version of the story leaves out.

Then choose one present-day problem and build a realistic pathway for it. Separate what
one person can do from what requires community, money, law, or institutional power.
Photograph the finished wall for each learner's portfolio and let each learner add a short
reflection explaining their own contribution.
""",
            "LAB_MISSION",
        ),
    ],
    "oas_standards": [],
    "researcher_activated": True,
    "agent_name": "JusticeAgent",
    "pending_approval": False,
    "needs_review_reason": None,
    "source": "repository_builtin",
    "family_style": True,
    "version": 1,
}


def builtin_canonical(slug: str) -> dict[str, Any] | None:
    def slug_for(topic: str, track: str) -> str:
        return hashlib.sha256(f"{topic.strip().lower()}:{track}".encode()).hexdigest()[:32]

    aliases = (
        ("Children Who Changed History", "JUSTICE_CHANGEMAKING"),
        ("Children Who Changed History", "TRUTH_HISTORY"),
        ("Young People Who Changed History", "JUSTICE_CHANGEMAKING"),
    )
    if slug not in {slug_for(topic, track) for topic, track in aliases}:
        return None
    record = dict(CHILDREN_WHO_CHANGED_HISTORY)
    record["topic_slug"] = slug
    return record
