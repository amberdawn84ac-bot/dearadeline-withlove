"""Reviewed family investigation that opens without an authoring provider."""

from app.curriculum.classroom import (
    Blueprint,
    Classroom,
    Scene,
    SceneBrief,
    Speech,
    TeachingDesign,
)
from app.curriculum.classroom_quality import (
    validate_teaching_plan,
    validate_teaching_scene,
)
from app.curriculum.runtime_capabilities import authoring_capabilities
from app.schemas.api_models import Track

ESTUARY_ITEM = "reference-estuary-salinity"
ESTUARY_TITLE = "When the River Meets the Sea"
ESTUARY_SOURCE = {
    "id": "noaa-estuary-circulation",
    "title": "Estuaries Tutorial — Water Circulation",
    "url": "https://cdn.oceanservice.noaa.gov/oceanserviceprod/education/tutorial_estuaries/lessons/estuaries_tutorial.pdf",
    "description": "Find the salt-wedge and vertically mixed diagrams in the water circulation section. Compare the salinity patterns in the two cross-sections.",
    "attribution": "NOAA National Ocean Service",
}


def estuary_classroom() -> Classroom:
    start, explain, lab, check, apply = (
        "predict-the-pour",
        "explain-the-layers",
        "test-the-layers",
        "test-a-new-case",
        "brief-a-field-team",
    )
    scenes = [
        Scene(
            id=start,
            title="Will these waters mix?",
            type="pbl",
            content=(
                "A river meets the sea in an estuary. Imagine looking through a glass wall into the channel. "
                "Would the water near the bed taste as salty as the water at the surface? "
                "Set out two clear cups of room-temperature water. In your model one cup will represent river water, the other seawater."
            ),
            actions=[
                Speech(
                    role_id="adeline",
                    kind="pause",
                    focus="task",
                    text=(
                        "Draw a line where you think the boundary will be. If you expect the waters to mix evenly, draw what that would look like. "
                        "Save your prediction so you can compare it with what you see."
                    ),
                )
            ],
            learner_task="Save your first prediction and a reason before viewing the explanation.",
            family_roles={
                "elementary": "Sketch both cups and predict what you would see through the side.",
                "middle": "Predict the top and bottom water at the same spot and explain what might make them different.",
                "high_school": "Predict the vertical salinity profile. Name one condition that could make your prediction fail.",
            },
            success_criteria=[
                "Your prediction names a visible outcome and gives a reason."
            ],
            steps=[
                "Draw the water column.",
                "Label your predicted top and bottom and explain your thinking.",
            ],
        ),
        Scene(
            id=explain,
            title="Same space, different mass",
            type="slide",
            content=(
                "Salinity describes how much dissolved salt water contains. Density is mass divided by volume. "
                "At the same temperature, adding dissolved salt makes water denser. Compare two equal-volume samples. "
                "The one with more mass has greater density. In quiet water, denser water tends to sit below less dense water."
            ),
            worked_example=(
                "Suppose two samples each occupy 100 mL. If one has a mass of 100 g and the other 103 g, "
                "their densities are 1.00 and 1.03 g/mL. The numbers are illustrative. "
                "The difference is small, but the heavier sample has more mass in the same space."
            ),
            actions=[
                Speech(
                    role_id="adeline",
                    kind="pause",
                    focus="visual",
                    text="Picture the estuary sliced from surface to bed. Where would you look for the less dense water?",
                ),
                Speech(
                    role_id="adeline",
                    kind="reveal",
                    target_id="water-column",
                    text=(
                        "Look at the top and bottom. Fresh water from the river can flow over a denser tongue of salty water. "
                        "This is one pattern called a salt wedge."
                    ),
                ),
                Speech(
                    role_id="adeline",
                    kind="annotate",
                    target_id="water-column",
                    text=(
                        "Hold your finger at one spot along the channel and look straight down. A surface reading and a bottom reading can tell different stories."
                    ),
                    note="Compare the layers at the same spot and time.",
                ),
            ],
            visual={
                "reading": "In this simplified salt-wedge cross-section, fresher river water is above denser salty water. The bed is below both layers.",
                "elements": [
                    {
                        "id": "water-column",
                        "type": "layer_stack",
                        "text": "One water column in a salt-wedge estuary",
                        "labels": [
                            "Surface · fresher river water",
                            "Near the bed · saltier seawater",
                        ],
                    }
                ],
            },
            learner_task="Explain how two equal-volume samples can settle at different depths.",
            family_roles={
                "elementary": "Point to the two layers and explain which has more mass for the same cupful.",
                "middle": "Use the equal-volume example to calculate both densities and compare them.",
                "high_school": "Explain why the conclusion holds temperature constant and why sampling depth matters.",
            },
            success_criteria=[
                "Your explanation uses mass per equal volume to account for the layering."
            ],
            source_uses=[
                {
                    "source_id": ESTUARY_SOURCE["id"],
                    "supports": "The salt-wedge cross-section shows fresher outflow above denser, saltier inflow.",
                }
            ],
        ),
        Scene(
            id=lab,
            title="Build two miniature estuaries",
            type="pbl",
            content=(
                "Keep temperature, amounts, and pouring method the same. In one cup the bottom water is salty. "
                "In the other it is fresh. This comparison helps you decide whether the color boundary comes from "
                "differences in salinity or simply from the way you poured."
            ),
            materials=[
                "3 clear cups",
                "Room-temperature water",
                "Table salt",
                "Teaspoon",
                "Food coloring",
                "Timer",
                "Paper or notebook",
            ],
            steps=[
                "Label two cups Salt and Fresh. Put ½ cup of room-temperature water in each. Stir 1 level teaspoon of salt into Salt until dissolved. Stir Fresh for the same amount of time.",
                "In the third cup, color ½ cup of room-temperature fresh water with one drop of food coloring.",
                "Hold the back of a spoon just above the Salt cup’s surface. Slowly pour ¼ cup of colored water over the spoon. Repeat at the same speed with the same amount in Fresh.",
                "From the side, sketch the color at the surface and near the bottom after 10 seconds and again after 2 minutes. If the boundary is faint, record that.",
                "Compare the cups. Stir Salt gently and observe how mixing changes the boundary. Save the before-and-after observations.",
            ],
            actions=[
                Speech(
                    role_id="adeline",
                    focus="task",
                    text="Give the control cup the same pour. The color helps you see where the added water goes.",
                ),
                Speech(
                    role_id="adeline",
                    kind="pause",
                    focus="task",
                    text="Run both pours now. Record the actual color boundaries before you explain what caused them.",
                ),
            ],
            learner_task="Save two timed observations from each cup, then explain what changed when you stirred.",
            family_roles={
                "elementary": "Draw both cups at each time. Mark the strongest color with an arrow.",
                "middle": "Keep a two-by-two time-and-cup table. Cite a difference between the cups when you make your claim.",
                "high_school": "Evaluate the control and identify a source of mixing during pouring. Propose a repeat that would test its effect.",
            },
            success_criteria=[
                "Your record compares both cups at the same times.",
                "Your explanation distinguishes what you saw from what you infer about density.",
            ],
        ),
        Scene(
            id=check,
            title="Where would you sample?",
            type="quiz",
            content=(
                "At a different estuary, a field team measures relatively low salinity in surface water. "
                "A biologist wants to know whether an animal on the bed is in the same conditions. "
                "The team has one more sample to collect."
            ),
            actions=[
                Speech(
                    role_id="adeline",
                    kind="pause",
                    focus="task",
                    text="Choose a sampling plan you can defend with evidence from the lab.",
                )
            ],
            learner_task="Choose your sampling plan independently. After checking, explain why one other option would give weaker evidence.",
            family_roles={
                "elementary": "Point to the animal in a sketch and choose where to measure.",
                "middle": "Choose a sample and explain why matching location and time makes the comparison stronger.",
                "high_school": "Choose a sample and specify a later comparison that would test whether tide or wind changed the layers.",
            },
            question={
                "prompt": "Which single sample best tests the water the animal is actually in?",
                "choices": [
                    {
                        "id": "surface-again",
                        "label": "Take another sample at the surface in the same spot.",
                    },
                    {
                        "id": "near-bed",
                        "label": "Sample near the bed at the same spot and time.",
                    },
                    {
                        "id": "upstream",
                        "label": "Sample river water several miles upstream the next day.",
                    },
                ],
                "answer": "near-bed",
                "explanation": (
                    "A bottom sample measures the water the animal is in. A second surface sample tests repeatability at the surface, "
                    "and an upstream sample changes both the place and time. Neither directly measures the animal’s conditions."
                ),
            },
            success_criteria=[
                "You identify the sample that answers the question and can explain why depth matters."
            ],
        ),
        Scene(
            id=apply,
            title="Write a field-team note",
            type="pbl",
            portfolio_title="Estuary field-team note",
            content=(
                "Real estuaries change with river flow, wind and tides. Stirring the cup illustrates how mixing can weaken a visible boundary. "
                "Your cup has no tide, wind, channel shape or incoming river. Use it to explain a possibility, then say what a real field team should measure."
            ),
            actions=[
                Speech(
                    role_id="adeline",
                    kind="speak",
                    text="A useful field note says what you observed, what you think it means, and what you would measure next.",
                )
            ],
            learner_task="Save a short field-team note for your portfolio with one observation, one inference, and a sampling recommendation.",
            family_roles={
                "elementary": "Use your sketch to tell the team one thing you saw and where to put a sampler.",
                "middle": "Cite your timed observations and recommend a paired depth measurement.",
                "high_school": "Compare the salt-wedge and mixed cases. Propose a repeat across two tide conditions and explain what the results could distinguish.",
            },
            steps=[
                "Choose an observation from your two-cup comparison and label it as an observation.",
                "Explain the mechanism and name one limitation of the cup model.",
                "Recommend locations, depths, or times for a real field measurement.",
            ],
            success_criteria=[
                "The note separates observation from inference and proposes a measurement that could change your conclusion."
            ],
            source_uses=[
                {
                    "source_id": ESTUARY_SOURCE["id"],
                    "supports": "The circulation diagrams show why a single salt-wedge pattern should not be assumed for every estuary.",
                }
            ],
        ),
    ]
    plan = Blueprint(
        title=ESTUARY_TITLE,
        understanding="Differences in density can layer water, so conditions at the surface and bed of an estuary can differ.",
        essential_question="Why can water from the same estuary settle into layers?",
        demonstration="Use a controlled cup investigation to recommend a field measurement at a new estuary.",
        integrated_tracks=[Track.CREATION_SCIENCE],
        roster=[
            {
                "id": "adeline",
                "name": "Adeline",
                "role": "teacher",
                "persona": "Warm, curious, and precise about what the evidence can show.",
            },
            {
                "id": "field-partner",
                "name": "Field partner",
                "role": "assistant",
                "persona": "Checks whether proposed observations would answer the question.",
            },
        ],
        scenes=[
            SceneBrief(
                id=scene.id,
                title=scene.title,
                type=scene.type,
                purpose=purpose,
                objective=scene.success_criteria[0],
                brief=scene.content,
                evidence=scene.learner_task,
            )
            for scene, purpose in zip(
                scenes,
                (
                    "independent_attempt",
                    "explain",
                    "practice",
                    "independent_check",
                    "apply",
                ),
                strict=True,
            )
        ],
        next_revisit="Compare the effect of temperature and salinity using measured density at equal volumes.",
        teaching_design=TeachingDesign(
            approach="workshop",
            rationale="Use a model to explain a real field sampling problem.",
            initial_attempt="Sketch a predicted salinity profile before seeing the model.",
            likely_difficulty="Learners may assume two samples from one location must have the same salinity.",
            support="Compare equal volumes, reveal the cross-section, then run a controlled pour.",
            independent_check="Choose a new field sampling plan and defend it with evidence.",
            learning_strategy="Separate what you observe from what you infer.",
            revisit_adds="Use temperature measurements to test whether salinity alone explains a density difference.",
        ),
    )
    validate_teaching_plan(plan, authoring_capabilities())
    previous = []
    for brief, scene in zip(plan.scenes, scenes, strict=True):
        validate_teaching_scene(
            scene, brief.model_dump(), previous, [ESTUARY_SOURCE]
        )
        previous.append(scene.model_dump())
    return Classroom(blueprint=plan, scenes=scenes)
