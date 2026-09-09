"""
Experiments API — /experiments/*

The "Sovereign Lab" engine for CREATION_SCIENCE.
Instead of reading about chemistry, students blow things up.

POST /experiments/start          — Start an experiment session
GET  /experiments                — List available experiments by chaos level
GET  /experiments/{experiment_id} — Single experiment detail
POST /experiments/{experiment_id}/seal — Upload discovery + grant credit
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.middleware import get_current_user_id, require_role, verify_student_access_for_user
from app.schemas.api_models import (
    Experiment, ExperimentResponse, ExperimentStep,
    SocialMediaKit, CreationConnection,
    ChaosLevel, ScienceCredit, UserRole,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/experiments",
    tags=["experiments"],
    dependencies=[Depends(require_role(UserRole.STUDENT, UserRole.PARENT, UserRole.ADMIN))],
)


# ── In-memory experiment catalog (seeded below) ──────────────────────────────

EXPERIMENTS: dict[str, Experiment] = {}


def _register(exp: Experiment) -> None:
    EXPERIMENTS[exp.id] = exp


# ── The First 5 ──────────────────────────────────────────────────────────────

_register(Experiment(
    id="exp-elephant-toothpaste",
    title="Elephant Toothpaste",
    tagline="The loudest way to learn decomposition and exothermic reactions",
    chaos_level=ChaosLevel.SCOUT,
    wow_factor=9,
    scientific_concepts=["exothermic reactions", "decomposition", "catalysts", "hydrogen peroxide"],
    science_credits=[ScienceCredit.CHEMISTRY],
    grade_band="3-12",
    materials=[
        "16 oz empty plastic bottle",
        "1/2 cup 12% hydrogen peroxide (salon grade)",
        "1 packet dry yeast",
        "3 tbsp warm water",
        "Liquid dish soap",
        "Food coloring",
        "Tray or baking sheet",
    ],
    safety_requirements=[
        "Wear safety goggles",
        "Do this outdoors or on a tray",
        "12% hydrogen peroxide can irritate skin — adult handles the pour",
    ],
    steps=[
        ExperimentStep(step_number=1, instruction="Place the bottle on the tray. Add 1/2 cup hydrogen peroxide.", tip="Adult should pour the peroxide."),
        ExperimentStep(step_number=2, instruction="Add a big squirt of dish soap and swirl gently."),
        ExperimentStep(step_number=3, instruction="Add 5-10 drops of food coloring.", tip="Try multiple colors for a striped effect."),
        ExperimentStep(step_number=4, instruction="In a separate cup, mix the yeast packet with 3 tbsp warm water. Stir for 30 seconds."),
        ExperimentStep(step_number=5, instruction="Set up your camera. Pour the yeast mixture into the bottle and STEP BACK.", tip="Use slow-mo for the best replay."),
    ],
    creation_connection=CreationConnection(
        title="Catalysts in the Human Body",
        scripture="Psalm 139:14 — I praise you because I am fearfully and wonderfully made.",
        explanation="The yeast acts as a catalyst — it speeds up the breakdown of hydrogen peroxide without being consumed. Your body uses thousands of enzymes as catalysts every second. Digestion, breathing, even thinking all depend on precision-engineered catalysts inside your cells.",
    ),
    social_media_kit=SocialMediaKit(
        caption_template="Adeline taught us THIS today. Chemistry is loud. 🧪🔥 #DearAdeline",
        filming_tips=["Use slow-mo for the eruption", "Film from the side to see height", "Get the reaction shot of your siblings"],
        hashtags=["#DearAdeline", "#SovereignScience", "#ElephantToothpaste", "#HomeschoolScience"],
    ),
    estimated_minutes=20,
))

_register(Experiment(
    id="exp-mentos-rockets",
    title="Mentos Geyser Rockets",
    tagline="Launch a soda rocket 50 feet — and learn about nucleation",
    chaos_level=ChaosLevel.SOVEREIGN,
    wow_factor=10,
    scientific_concepts=["nucleation", "carbon dioxide", "surface tension", "gas pressure"],
    science_credits=[ScienceCredit.PHYSICS, ScienceCredit.CHEMISTRY],
    grade_band="5-12",
    materials=[
        "2-liter bottle of Diet Coke (cold)",
        "1 roll Mentos mints",
        "Index card or Mentos geyser tube",
        "Open outdoor area",
    ],
    safety_requirements=[
        "Do this in an open field — NOT near buildings or cars",
        "Stand at least 10 feet back after dropping",
        "Fire extinguisher nearby for Sovereign-level experiments",
        "Wear clothes you don't mind getting sticky",
    ],
    steps=[
        ExperimentStep(step_number=1, instruction="Set the 2-liter bottle on flat ground in an open area."),
        ExperimentStep(step_number=2, instruction="Stack 7 Mentos on the index card. Hold the card over the bottle opening.", tip="A Mentos geyser tube makes this easier and more consistent."),
        ExperimentStep(step_number=3, instruction="Set up your camera at a safe distance. Frame the full bottle plus 15 feet of sky."),
        ExperimentStep(step_number=4, instruction="Slide the card away, dropping ALL the Mentos at once. RUN.", tip="The faster they all drop in, the bigger the eruption."),
    ],
    creation_connection=CreationConnection(
        title="Nucleation in Nature",
        scripture="Job 37:5-6 — He says to the snow, 'Fall on the earth,' and to the rain shower, 'Be a mighty downpour.'",
        explanation="Every Mentos has thousands of tiny pits on its surface. CO2 molecules gather at these pits — that is nucleation. Rain forms the same way: water vapor nucleates around dust particles in the sky. These physical laws let water cycle from ocean to cloud to rain to river — sustaining all life.",
    ),
    social_media_kit=SocialMediaKit(
        caption_template="We just launched a soda rocket 50 feet into the air. This is school. 🚀 #DearAdeline",
        filming_tips=["Film from low angle looking up", "Slow-mo the moment of eruption", "Second camera for the reaction shot"],
        hashtags=["#DearAdeline", "#SovereignScience", "#MentosRocket", "#HomeschoolWins"],
    ),
    estimated_minutes=15,
))

_register(Experiment(
    id="exp-oobleck-pool",
    title="Oobleck Pool — Walk on Water",
    tagline="The ultimate viral moment — non-Newtonian fluids you can stand on",
    chaos_level=ChaosLevel.SCOUT,
    wow_factor=10,
    scientific_concepts=["non-Newtonian fluids", "viscosity", "shear thickening", "states of matter"],
    science_credits=[ScienceCredit.PHYSICS, ScienceCredit.CHEMISTRY],
    grade_band="K-12",
    materials=[
        "25 lbs cornstarch (bulk bag from restaurant supply)",
        "Large plastic kiddie pool or storage bin",
        "Water (garden hose)",
        "Old clothes and towels",
    ],
    safety_requirements=[
        "Do this outdoors on grass",
        "Do NOT pour oobleck down drains — it will clog them",
        "Dispose by letting it dry and throwing in trash",
    ],
    steps=[
        ExperimentStep(step_number=1, instruction="Pour 25 lbs of cornstarch into the pool."),
        ExperimentStep(step_number=2, instruction="Slowly add water while mixing with your hands. The ratio is about 2 parts cornstarch to 1 part water.", tip="It should feel solid when you punch it but liquid when you move slowly."),
        ExperimentStep(step_number=3, instruction="Test it: punch the surface HARD. It should feel solid. Now push your hand in slowly. It should sink."),
        ExperimentStep(step_number=4, instruction="Set up your camera. Try to RUN across the surface.", tip="You have to keep moving — stop and you sink."),
        ExperimentStep(step_number=5, instruction="Try placing a heavy object on the surface gently vs. dropping it.", tip="This shows the difference between slow and fast force."),
    ],
    creation_connection=CreationConnection(
        title="States of Matter",
        scripture="Proverbs 8:29 — When He gave the sea its boundary so the waters would not overstep His command.",
        explanation="Oobleck is a shear-thickening fluid — it gets harder when force is applied quickly. Your body uses this same principle: synovial fluid in your joints thickens under impact to protect your bones. Shock absorption is engineered into the skeleton itself.",
    ),
    social_media_kit=SocialMediaKit(
        caption_template="We walked on water today. Well... cornstarch water. 🏃‍♂️💨 #DearAdeline",
        filming_tips=["Film the run from the side", "Slow-mo someone sinking when they stop", "Close-up of punching the surface"],
        hashtags=["#DearAdeline", "#Oobleck", "#WalkOnWater", "#NonNewtonianFluid"],
    ),
    estimated_minutes=45,
))

_register(Experiment(
    id="exp-dry-ice-bubbles",
    title="Dry Ice Crystal Ball Bubbles",
    tagline="Giant fog-filled bubbles that pop with a cloud",
    chaos_level=ChaosLevel.SCOUT,
    wow_factor=8,
    scientific_concepts=["sublimation", "states of matter", "CO2 gas", "surface tension"],
    science_credits=[ScienceCredit.CHEMISTRY, ScienceCredit.PHYSICS],
    grade_band="3-12",
    materials=[
        "Dry ice (from grocery store — adults only)",
        "Large bowl or bucket",
        "Warm water",
        "Liquid dish soap",
        "Strip of fabric or old t-shirt",
        "Thick gloves (never touch dry ice bare-handed)",
    ],
    safety_requirements=[
        "ONLY adults handle dry ice — it causes burns at -109.3 F",
        "Use in a well-ventilated area (CO2 displaces oxygen)",
        "Wear thick gloves at all times",
        "Never seal dry ice in an airtight container",
    ],
    steps=[
        ExperimentStep(step_number=1, instruction="Fill the bowl halfway with warm water."),
        ExperimentStep(step_number=2, instruction="Adult: wearing gloves, add 2-3 chunks of dry ice to the water.", tip="Fog is immediate — get your camera ready."),
        ExperimentStep(step_number=3, instruction="Dip the fabric strip in soapy water. Drag it across the rim of the bowl to create a soap film."),
        ExperimentStep(step_number=4, instruction="Watch the bubble grow as CO2 fills it from below. When it pops, fog spills out.", tip="Poke the bubble with a wet finger for a controlled pop."),
    ],
    creation_connection=CreationConnection(
        title="Sublimation — Skipping a Step",
        scripture="Isaiah 55:9 — As the heavens are higher than the earth, so are my ways higher than your ways.",
        explanation="Dry ice goes directly from solid to gas — skipping the liquid phase entirely. This is called sublimation. These phase transitions make the water cycle, weather, and even food preservation work. The same CO2 gas in your bubbles is what plants take in to make oxygen for you.",
    ),
    social_media_kit=SocialMediaKit(
        caption_template="Giant fog bubbles. Science is magic you can explain. ☁️🫧 #DearAdeline",
        filming_tips=["Film the bubble growing from eye level", "Backlight it for the fog effect", "Pop it in slow-mo"],
        hashtags=["#DearAdeline", "#DryIceScience", "#SovereignScience"],
    ),
    estimated_minutes=25,
))

_register(Experiment(
    id="exp-fire-tornado",
    title="Fire Tornado in a Trash Can",
    tagline="Build a real vortex of fire — and learn how tornadoes form",
    chaos_level=ChaosLevel.SOVEREIGN,
    wow_factor=10,
    scientific_concepts=["convection", "vorticity", "combustion", "fluid dynamics", "Coriolis effect"],
    science_credits=[ScienceCredit.PHYSICS, ScienceCredit.EARTH_SCIENCE],
    grade_band="7-12",
    materials=[
        "Metal trash can (no plastic)",
        "Metal mesh screen or chicken wire",
        "Lazy Susan or rotating platform",
        "Fire-safe fuel (rubbing alcohol in a metal dish)",
        "Long lighter or matches",
        "Fire extinguisher (REQUIRED)",
    ],
    safety_requirements=[
        "SOVEREIGN LEVEL — open field, fire extinguisher, adult supervision MANDATORY",
        "Clear a 15-foot radius of all flammable material",
        "Have a garden hose connected and ready",
        "Never add fuel to an active fire",
        "Wind speed must be under 10 mph",
    ],
    steps=[
        ExperimentStep(step_number=1, instruction="Place the metal dish with 1/4 cup rubbing alcohol in the center of the lazy Susan."),
        ExperimentStep(step_number=2, instruction="Form the chicken wire into a cylinder around the dish, leaving 6 inches of space on all sides."),
        ExperimentStep(step_number=3, instruction="Set up your camera at a safe distance. Adult: use the long lighter to ignite the alcohol."),
        ExperimentStep(step_number=4, instruction="Slowly spin the lazy Susan. Watch the flame stretch into a tornado.", tip="Spin faster for a taller vortex. The fire pulls in air, creating the funnel shape."),
        ExperimentStep(step_number=5, instruction="Observe: the tornado is tallest when spinning fastest. Stop spinning and watch it collapse back to a normal flame."),
    ],
    creation_connection=CreationConnection(
        title="Convection and the Atmosphere",
        scripture="Nahum 1:3 — His way is in the whirlwind and the storm.",
        explanation="The fire tornado forms because spinning air creates a low-pressure core that stretches the flame upward. Real tornadoes form the same way — warm air rises (convection), wind shear adds rotation, and the vortex tightens. These forces drive weather, distribute heat, and sustain the global climate. Understanding them is how we protect our families and steward the land.",
    ),
    social_media_kit=SocialMediaKit(
        caption_template="We built a FIRE TORNADO today. Sovereign-level science. 🔥🌪️ #DearAdeline",
        filming_tips=["Film at dusk for the most dramatic footage", "Use slow-mo on the spin-up", "Wide shot to show scale"],
        hashtags=["#DearAdeline", "#FireTornado", "#SovereignScience", "#Level3Science"],
    ),
    estimated_minutes=40,
))

_register(Experiment(
    id="exp-yeast-balloon",
    title="Yeast Balloon",
    tagline="Watch yeast breathe — the same workers that raise sourdough",
    chaos_level=ChaosLevel.SPROUT,
    wow_factor=8,
    scientific_concepts=["fermentation", "carbon dioxide", "yeast metabolism", "sugar as fuel"],
    science_credits=[ScienceCredit.BIOLOGY, ScienceCredit.CHEMISTRY],
    grade_band="K-12",
    materials=[
        "Empty plastic bottle (water-bottle size)",
        "1 packet dry yeast",
        "1 tsp sugar",
        "Warm water (about 100 F — bath-warm, not hot)",
        "1 balloon",
    ],
    safety_requirements=[
        "Warm water, not boiling — hot water kills the yeast",
        "Do this at the table; the balloon will inflate, it will not pop from this",
    ],
    steps=[
        ExperimentStep(step_number=1, instruction="Stretch the balloon a few times so it inflates easily."),
        ExperimentStep(step_number=2, instruction="Pour about 1 cup of warm water into the bottle. Add the sugar and swirl."),
        ExperimentStep(step_number=3, instruction="Add the yeast, swirl once, then immediately stretch the balloon over the bottle mouth.", tip="Work quickly so the gas does not escape before the balloon is on."),
        ExperimentStep(step_number=4, instruction="Watch for 10–20 minutes. The balloon should stand up as yeast eats the sugar and releases CO2."),
        ExperimentStep(step_number=5, instruction="Write what you saw: how long until it moved, how tall it got, and what you think the yeast was doing.", tip="This is the same gas that lifts sourdough. Compare it to a jar of starter if you have one."),
    ],
    creation_connection=CreationConnection(
        title="Living yeast, living dough",
        scripture="Genesis 1:11 — Elohim said, Let the earth sprout sproutage.",
        explanation="Yeast is alive. It eats sugar and breathes out carbon dioxide, the same gas that raises bread. This is fermentation — a living process, not a recipe trick. The same workers in this bottle are in a sourdough starter.",
    ),
    social_media_kit=SocialMediaKit(
        caption_template="Yeast inflated a balloon in 15 minutes. That is the same gas that raises our bread. #DearAdeline",
        filming_tips=["Time-lapse the balloon", "Set a ruler behind the bottle for height", "Film a starter jar next to it"],
        hashtags=["#DearAdeline", "#YeastBalloon", "#KitchenScience"],
    ),
    estimated_minutes=25,
))

_register(Experiment(
    id="exp-cabbage-ph",
    title="Red Cabbage pH Rainbow",
    tagline="A kitchen indicator that shows acid and base by color",
    chaos_level=ChaosLevel.SPROUT,
    wow_factor=8,
    scientific_concepts=["acids and bases", "pH", "indicators", "anthocyanins"],
    science_credits=[ScienceCredit.CHEMISTRY],
    grade_band="K-12",
    materials=[
        "1/2 small red cabbage",
        "Hot water",
        "Clear cups or jars (4 or more)",
        "Kitchen testers: lemon juice or vinegar, baking soda, soap water, milk if you have it",
        "Spoon",
    ],
    safety_requirements=[
        "Adult handles the hot water",
        "Do not drink the indicator mix after testing",
        "Keep soap and vinegar away from eyes",
    ],
    steps=[
        ExperimentStep(step_number=1, instruction="Chop the cabbage. Cover it with hot water in a bowl. Steep 10 minutes until the water is deep purple. Strain into a pitcher."),
        ExperimentStep(step_number=2, instruction="Pour a little purple liquid into each clear cup."),
        ExperimentStep(step_number=3, instruction="Add a spoon of a different kitchen tester to each cup. Watch the color shift.", tip="Acid goes pink/red. Base goes blue/green. Record the color next to the tester name."),
        ExperimentStep(step_number=4, instruction="Line the cups up from most pink to most green. That is a homemade pH scale."),
        ExperimentStep(step_number=5, instruction="Predict one more tester (pickle brine, soda, dirt water) before you pour, then check."),
    ],
    creation_connection=CreationConnection(
        title="Color as evidence",
        scripture="",
        explanation="Anthocyanins in red cabbage change shape when they meet acid or base, and the new shape reflects different light. The color is the measurement. Food chemists used indicators like this to catch adulterated milk — the same fight as the Poison Squad.",
    ),
    social_media_kit=SocialMediaKit(
        caption_template="Cabbage juice turned into a pH rainbow on our table. #DearAdeline",
        filming_tips=["Film the pour from above", "Hold a white card behind the cups", "Show the lineup from pink to green"],
        hashtags=["#DearAdeline", "#KitchenChemistry", "#pHRainbow"],
    ),
    estimated_minutes=30,
))


def _grade_number(grade: str) -> int:
    g = str(grade or "").strip().upper()
    if not g or g.startswith("K"):
        return 0
    try:
        return max(0, min(12, int(g.split("-")[0])))
    except (TypeError, ValueError):
        return 8


def grade_in_band(grade: str, band: str) -> bool:
    parts = (band or "K-12").split("-")
    low = 0 if parts[0] == "K" else int(parts[0])
    high = int(parts[1]) if len(parts) > 1 else low
    return low <= _grade_number(grade) <= high


def experiments_for_grade(grade: str, limit: int = 1) -> list[Experiment]:
    """Kitchen-first for younger grades; spectacle-first for high school."""
    matching = [exp for exp in EXPERIMENTS.values() if grade_in_band(grade, exp.grade_band)]
    gn = _grade_number(grade)
    if gn <= 8:
        matching.sort(key=lambda exp: (exp.chaos_level.value, -exp.wow_factor))
    else:
        matching.sort(key=lambda exp: (-exp.wow_factor, exp.chaos_level.value))
    return matching[: max(1, limit)]


def experiment_as_block(exp: Experiment) -> dict:
    """Shape a catalog experiment as a conversation EXPERIMENT block."""
    data = exp.model_dump(mode="json")
    steps = "\n".join(
        f"{item['step_number']}. {item['instruction']}"
        for item in data.get("steps") or []
    )
    materials = ", ".join((data.get("materials") or [])[:8])
    return {
        "block_type": "EXPERIMENT",
        "title": exp.title,
        "content": f"{exp.tagline}\n\nMaterials: {materials}\n\n{steps}",
        "experiment_id": exp.id,
        "experiment": data,
        "scientific_concepts": list(exp.scientific_concepts),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[Experiment])
async def list_experiments(
    chaos_level: Optional[int] = Query(None, ge=1, le=3, description="Filter by chaos level (1=Sprout, 2=Scout, 3=Sovereign)"),
    grade: Optional[str] = Query(None, description="Filter by grade level"),
):
    """List all experiments, optionally filtered by chaos level or grade."""
    experiments = list(EXPERIMENTS.values())

    if chaos_level is not None:
        experiments = [e for e in experiments if e.chaos_level.value == chaos_level]

    if grade is not None:
        experiments = [e for e in experiments if grade_in_band(grade, e.grade_band)]

    return sorted(experiments, key=lambda e: e.wow_factor, reverse=True)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str):
    """Fetch a single experiment by ID."""
    exp = EXPERIMENTS.get(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse(experiment=exp)


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(experiment_id: str, student_id: str = ""):
    """
    Student says "I have the materials."
    Returns the full experiment with steps for the Live Guide view.
    """
    exp = EXPERIMENTS.get(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    logger.info(f"[Experiments] Student {student_id} starting: {exp.title}")
    return ExperimentResponse(
        experiment=exp,
        student_materials_ready=True,
    )


class SealExperimentRequest(BaseModel):
    student_id: str
    reflection: str = Field(min_length=12, max_length=4000)
    artifact_refs: list[str] = Field(default_factory=list, max_length=20)


class SealExperimentResponse(BaseModel):
    sealed: bool
    experiment_id: str
    title: str
    learning_status: str
    concepts: list[str] = Field(default_factory=list)


@router.post("/{experiment_id}/seal", response_model=SealExperimentResponse)
async def seal_experiment(
    experiment_id: str,
    body: SealExperimentRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Credit a completed experiment from the family's observation, not from clicking Done."""
    exp = EXPERIMENTS.get(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    await verify_student_access_for_user(current_user_id, body.student_id)

    from app.services.mastery_credit import ConceptCredit, record_mastery_credit

    reflection = body.reflection.strip()
    credits = [
        ConceptCredit(concept_id=f"exp:{exp.id}:{index}", concept_name=name, quality=3)
        for index, name in enumerate(exp.scientific_concepts)
    ]
    evidence = [{"type": "learner_reflection", "content": reflection}]
    evidence.extend({"type": "artifact", "url": ref} for ref in body.artifact_refs)
    try:
        await record_mastery_credit(
            student_id=body.student_id,
            track=exp.track.value,
            lesson_id=f"experiment:{exp.id}",
            completed_blocks=len(exp.steps),
            proficiency="UNDERSTANDING",
            evidence_sources=evidence,
            concept_credits=credits,
        )
    except Exception as exc:
        logger.exception("[Experiments] seal credit failed")
        raise HTTPException(
            status_code=500,
            detail=f"Could not record this experiment; retrying is safe: {exc}",
        ) from exc
    return SealExperimentResponse(
        sealed=True,
        experiment_id=exp.id,
        title=exp.title,
        learning_status="UNDERSTANDING",
        concepts=list(exp.scientific_concepts),
    )
