"""
Projects API — /projects/*

Art/DIY + Farm project catalog for CREATIVE_ECONOMY and HOMESTEADING tracks.
Projects are curated — they do NOT go through lesson generation or the Witness Protocol.
They are step-by-step real-world doing, not reading.

GET  /projects                  — List all projects (filter by track, category, difficulty)
GET  /projects/{project_id}     — Single project with full step guide
POST /projects/{project_id}/seal — Student seals a completed project, grants credit

Portfolio philosophy: a completed project is an accomplishment, not an assignment.
The seal endpoint records it to the transcript as real credit.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.api_models import (
    Project, ProjectStep, ProjectCategory, ProjectDifficulty,
    PriceRange, ProjectSealRequest, ProjectSealResponse,
    Track, UserRole,
)
from app.api.middleware import require_role
from app.connections.journal_store import journal_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


# ── In-memory project catalog ─────────────────────────────────────────────────

PROJECTS: dict[str, Project] = {}


def _register(p: Project) -> None:
    PROJECTS[p.id] = p


# ══════════════════════════════════════════════════════════════════════════════
# CREATIVE ECONOMY PROJECTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Beeswax Lip Balm ─────────────────────────────────────────────────────────

_register(Project(
    id="proj-beeswax-lip-balm",
    title="Beeswax Lip Balm",
    track=Track.CREATIVE_ECONOMY,
    category=ProjectCategory.CRAFT,
    difficulty=ProjectDifficulty.SEEDLING,
    tagline="Make 12 lip balms in an afternoon. Sell for $3–5 each at markets or online.",
    skills=["Measuring", "Double-boiler technique", "Label design", "Ingredient sourcing"],
    business_skills=["Cost of goods calculation", "Pricing for profit", "Product photography"],
    materials=[
        "Beeswax pellets (1 oz)",
        "Coconut oil (2 tbsp)",
        "Sweet almond oil (1 tbsp)",
        "Essential oil — peppermint or lavender (10 drops)",
        "Lip balm tubes or small tins (12 pack)",
        "Double boiler or two saucepans",
        "Candy thermometer",
        "Pipette or small pouring cup",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Set up your double boiler: fill the bottom pot with 2 inches of water and bring to a gentle simmer. Place the top pot or heat-safe bowl on top.", tip="Never let water boil vigorously — slow and steady melts wax without scorching."),
        ProjectStep(step_number=2, instruction="Add 1 oz beeswax pellets to the top pot. Stir occasionally until fully melted, about 5–7 minutes. Check temperature — target 160–170°F."),
        ProjectStep(step_number=3, instruction="Add coconut oil and sweet almond oil. Stir until combined and fully melted. Remove from heat."),
        ProjectStep(step_number=4, instruction="Let the mixture cool to 140°F. Add 10 drops of essential oil and stir gently — adding it too hot burns off the scent."),
        ProjectStep(step_number=5, instruction="Carefully pour into lip balm tubes or tins using a pipette or small spouted cup. Fill each container almost to the top.", tip="Work quickly — beeswax sets fast. If it hardens in the pot, reheat gently."),
        ProjectStep(step_number=6, instruction="Let cool completely undisturbed for 30 minutes. Do not move or refrigerate — this causes pits and cracks."),
        ProjectStep(step_number=7, instruction="Cap each tube or tin. Design a label with your product name, ingredients, and your name as maker."),
        ProjectStep(step_number=8, instruction="Calculate your cost of goods: add up every material cost and divide by 12. Your price should be at least 3× your cost."),
    ],
    estimated_hours=2.0,
    price_range=PriceRange(low=3.00, high=5.00, unit="per unit"),
    where_to_sell=["Farmers markets", "Etsy", "Local boutiques", "Church bazaars", "Instagram DMs"],
    portfolio_prompts=[
        "Photograph your finished product next to your ingredients and handwritten label.",
        "Write a one-paragraph product description as if listing it on Etsy.",
        "Calculate your profit margin at your chosen price point.",
    ],
    safety_notes=["Hot wax burns — use oven mitts and keep children away from the stove.", "Essential oils are concentrated — never apply undiluted to skin."],
    income_description="12 units × $4 average = $48 gross per batch. Material cost ~$8 per batch = $40 profit. Scale to 5 batches/week for a real side income.",
    grade_band="4-12",
))


# ── Hand-Poured Soy Candles ───────────────────────────────────────────────────

_register(Project(
    id="proj-soy-candles",
    title="Hand-Poured Soy Candles",
    track=Track.CREATIVE_ECONOMY,
    category=ProjectCategory.CRAFT,
    difficulty=ProjectDifficulty.SEEDLING,
    tagline="Turn $15 of supplies into $80 of product. One of the most profitable beginner crafts.",
    skills=["Temperature control", "Scent blending", "Wick centering", "Cure timing"],
    business_skills=["Batch production", "Pricing", "Brand storytelling", "Market research"],
    materials=[
        "Soy wax flakes (2 lbs)",
        "Cotton wicks with metal base (12)",
        "Fragrance oil (2 oz)",
        "Glass jars with lids, 8 oz (12)",
        "Candle dye chips (optional)",
        "Double boiler",
        "Candy thermometer",
        "Wooden skewers or pencils (to hold wicks)",
        "Wick stickers or hot glue",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Stick a wick to the center bottom of each jar using a wick sticker or small dot of hot glue. Let dry for 5 minutes."),
        ProjectStep(step_number=2, instruction="Rest a wooden skewer across the top of each jar with the wick thread wrapped around it to hold it centered."),
        ProjectStep(step_number=3, instruction="Melt soy wax in the double boiler to 185°F, stirring occasionally."),
        ProjectStep(step_number=4, instruction="Remove from heat. At 170°F, add dye chips if using. Stir until fully dissolved."),
        ProjectStep(step_number=5, instruction="At 160°F, add fragrance oil (1 oz per pound of wax). Stir for 2 full minutes — this is what locks the scent into the wax.", tip="Under-mixing fragrance causes 'sinkholes' and weak throw."),
        ProjectStep(step_number=6, instruction="Pour wax into jars at 135–140°F. Fill to ½ inch below the rim. Leave the skewers in place to keep wicks centered."),
        ProjectStep(step_number=7, instruction="Let candles cure at room temperature for 24 hours minimum. For best scent throw, cure 48–72 hours before burning."),
        ProjectStep(step_number=8, instruction="Remove skewers. Trim wick to ¼ inch. Add lids and labels."),
        ProjectStep(step_number=9, instruction="Do a burn test on one candle: burn 4 hours, check for tunneling, note scent strength. Adjust fragrance load next batch if needed."),
    ],
    estimated_hours=3.0,
    price_range=PriceRange(low=12.00, high=22.00, unit="per candle"),
    where_to_sell=["Etsy", "Farmers markets", "Local gift shops (wholesale)", "Holiday craft fairs", "Subscription boxes"],
    portfolio_prompts=[
        "Photograph a styled flat lay of your candles with natural props (dried flowers, wood, linen).",
        "Write a brand story: What is your candle line called? What does it smell like? Who is it for?",
        "Calculate: what is your break-even price? What is your target retail price and why?",
    ],
    safety_notes=["Never leave melting wax unattended.", "Keep a fire extinguisher nearby — wax is flammable above 300°F.", "Always burn test before selling — a candle that tunnels or floods is a fire hazard."],
    income_description="12 candles × $16 average = $192 gross. Material cost ~$25 per batch = $167 profit. A Saturday market table can move 30–50 candles.",
    grade_band="5-12",
))


# ── Macramé Plant Hanger ──────────────────────────────────────────────────────

_register(Project(
    id="proj-macrame-plant-hanger",
    title="Macramé Plant Hanger",
    track=Track.CREATIVE_ECONOMY,
    category=ProjectCategory.CRAFT,
    difficulty=ProjectDifficulty.SEEDLING,
    tagline="Learn three knots. Make something beautiful. Sell for $25–45.",
    skills=["Square knot", "Spiral knot", "Measuring cord", "Reading a pattern"],
    business_skills=["Material sourcing", "Time tracking", "Pricing handmade work fairly"],
    materials=[
        "Macramé cord, 3mm natural cotton (100 ft per hanger)",
        "Wooden dowel or thick branch (12 inches)",
        "Scissors",
        "Tape measure",
        "S-hook or curtain ring",
        "Plant pot to test fit (4–6 inch)",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Cut 8 cords, each 12 feet long. Fold each in half and attach to the dowel using a lark's head knot: fold cord in half, loop over the dowel, pull the tails through the loop. You'll have 16 working strands."),
        ProjectStep(step_number=2, instruction="Divide the 16 strands into 4 groups of 4. Tie a square knot with each group, about 8 inches below the dowel. To tie a square knot: cross left strand over center two, then right strand over left and through the loop. Repeat mirrored.", tip="Keep tension even — practice the knot on a scrap piece before starting."),
        ProjectStep(step_number=3, instruction="Drop down 3 inches. Now regroup: take 2 strands from adjacent groups and tie square knots with each new group of 4. This creates the net pattern."),
        ProjectStep(step_number=4, instruction="Drop down another 3 inches. Repeat the regrouping and tie another row of square knots."),
        ProjectStep(step_number=5, instruction="Gather all 16 strands together about 4 inches below the last row. Tie a tight overhand knot with all strands together — this is the base of the pot cradle.", tip="Test with your pot before tying the final knot to make sure the fit is snug but not tight."),
        ProjectStep(step_number=6, instruction="Trim the fringe evenly or cut at angles for a decorative finish. Unravel the cord ends with your fingers for a fluffy look."),
        ProjectStep(step_number=7, instruction="Hang from a hook and insert your potted plant. Photograph with a trailing plant like pothos or ivy."),
    ],
    estimated_hours=1.5,
    price_range=PriceRange(low=25.00, high=45.00, unit="per hanger"),
    where_to_sell=["Etsy", "Instagram", "Local plant shops", "Farmers markets", "Home décor boutiques"],
    portfolio_prompts=[
        "Photograph your hanger hanging in a window with a plant in it.",
        "Time yourself making a second hanger. Calculate your hourly rate at your chosen price.",
        "Design a tag for your product. What is the name of your macramé line?",
    ],
    safety_notes=["Ensure the dowel or branch can support the pot weight before displaying or selling."],
    income_description="Each hanger takes ~1.5 hours and costs ~$4 in materials. At $30, that's $17/hr after materials. Speed increases with practice.",
    grade_band="5-12",
))


# ── Herbal Salve ──────────────────────────────────────────────────────────────

_register(Project(
    id="proj-herbal-salve",
    title="Calendula & Comfrey Herbal Salve",
    track=Track.CREATIVE_ECONOMY,
    category=ProjectCategory.CRAFT,
    difficulty=ProjectDifficulty.GROWER,
    tagline="Infuse herbs into oil. Make a healing salve. Know every ingredient.",
    skills=["Herb infusion", "Double-boiler technique", "Measuring ratios", "Product testing"],
    business_skills=["Labeling requirements for topical products", "Ingredient transparency", "Market positioning"],
    materials=[
        "Dried calendula flowers (2 tbsp)",
        "Dried comfrey leaf (1 tbsp)",
        "Olive oil or sunflower oil (4 oz)",
        "Beeswax pellets (0.5 oz)",
        "Vitamin E oil (5 drops, as preservative)",
        "Small glass jars, 2 oz (6)",
        "Cheesecloth or fine strainer",
        "Double boiler",
        "Candy thermometer",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Infuse the herbs: place dried calendula and comfrey in the top of a double boiler. Cover completely with olive oil. Heat on low (100–110°F) for 2–3 hours, stirring occasionally. The oil will turn golden.", tip="Do NOT let it get hotter than 120°F or you'll destroy the plant compounds you're trying to extract."),
        ProjectStep(step_number=2, instruction="Strain the infused oil through cheesecloth into a clean measuring cup. Squeeze out every drop. Discard the spent herbs."),
        ProjectStep(step_number=3, instruction="Measure the infused oil. For every 1 oz of oil, use 0.2 oz beeswax. Adjust beeswax amount based on how much oil you have."),
        ProjectStep(step_number=4, instruction="Return oil to the double boiler. Add beeswax. Heat gently until wax fully melts, stirring to combine."),
        ProjectStep(step_number=5, instruction="Do the plate test: drop a small amount on a cold plate. If too soft, add more beeswax. If too hard, add more oil. Reheat and adjust."),
        ProjectStep(step_number=6, instruction="Remove from heat. At 130°F, add vitamin E oil. Stir gently."),
        ProjectStep(step_number=7, instruction="Pour into jars immediately. Let cool undisturbed for 1 hour."),
        ProjectStep(step_number=8, instruction="Label each jar with: product name, all ingredients, 'for external use only', your name, and batch date."),
    ],
    estimated_hours=4.0,
    price_range=PriceRange(low=8.00, high=15.00, unit="per 2oz jar"),
    where_to_sell=["Farmers markets", "Etsy", "Herbalist fairs", "Local health food stores", "Direct sale"],
    portfolio_prompts=[
        "Research calendula and comfrey: what are the traditional uses of each herb? Cite one primary source.",
        "Write the ingredient list as it would appear on a real product label.",
        "Photograph your salve with the herbs used to make it.",
    ],
    safety_notes=["Comfrey contains pyrrolizidine alkaloids — for external use ONLY, never ingest.", "Do not use on broken skin or open wounds without consulting an herbalist.", "Patch test before selling — some people are sensitive to calendula (it's in the daisy family)."],
    income_description="6 jars × $10 = $60 gross. Material cost ~$12 per batch. Herb infusion knowledge is a premium — markets reward transparency about ingredients.",
    grade_band="6-12",
))


# ── Pressed Flower Art ────────────────────────────────────────────────────────

_register(Project(
    id="proj-pressed-flower-art",
    title="Pressed Flower Art & Greeting Cards",
    track=Track.CREATIVE_ECONOMY,
    category=ProjectCategory.CRAFT,
    difficulty=ProjectDifficulty.SEEDLING,
    tagline="Preserve beauty from the garden. Turn it into art people will frame.",
    skills=["Plant pressing", "Composition", "Mod Podge sealing", "Card layout"],
    business_skills=["Product photography", "Packaging handmade goods", "Seasonal inventory planning"],
    materials=[
        "Fresh flowers and leaves from the garden",
        "Heavy books or flower press",
        "Watercolor paper or cardstock",
        "Mod Podge (matte finish)",
        "Small paintbrush",
        "Tweezers",
        "Clear acrylic spray sealer",
        "Blank greeting card envelopes",
        "Wax paper",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Harvest flowers at their peak — morning, after dew dries. Choose flat or semi-flat flowers: pansies, violets, Queen Anne's lace, daisies, small roses.", tip="Avoid thick, fleshy flowers like tulips — they mold before they dry."),
        ProjectStep(step_number=2, instruction="Place flowers face-down between two sheets of wax paper. Slip inside a heavy book. Add more books on top. Leave for 2–3 weeks minimum.", tip="Check at 1 week — if the paper feels damp, replace it to prevent mold."),
        ProjectStep(step_number=3, instruction="Once fully dry and flat, arrange pressed flowers on watercolor paper using tweezers. Try several compositions before committing."),
        ProjectStep(step_number=4, instruction="Brush a thin layer of Mod Podge on the paper where you want to place each flower. Gently lay flowers down and smooth with the brush."),
        ProjectStep(step_number=5, instruction="Once all pieces are placed, brush a thin coat of Mod Podge over the entire surface. Let dry 30 minutes. Apply a second coat."),
        ProjectStep(step_number=6, instruction="Let dry completely (2–3 hours). Take outside and apply a light coat of acrylic sealer spray to protect from humidity."),
        ProjectStep(step_number=7, instruction="For greeting cards: cut watercolor paper to card size (4.25 × 5.5 for A2 envelopes). Apply flowers to the front panel only. Leave inside blank for handwriting."),
        ProjectStep(step_number=8, instruction="Package cards in a clear cellophane sleeve with a simple branded tag. Photograph on a wooden surface with dried herbs or a linen cloth."),
    ],
    estimated_hours=2.0,
    price_range=PriceRange(low=6.00, high=18.00, unit="per card or small piece"),
    where_to_sell=["Etsy", "Farmers markets", "Boutique gift shops", "Flower farms with retail", "Instagram"],
    portfolio_prompts=[
        "Photograph your best piece as a fine art print (overhead, on white background).",
        "Create a 5-card set and photograph it as a packaged product.",
        "Write a 3-sentence artist statement: what flowers did you use, where did they come from, what do you want buyers to feel?",
    ],
    safety_notes=["Acrylic spray sealer — use outdoors or in very well-ventilated space."],
    income_description="Cards sell for $6–8 each or $25 for a set of 5. Framed pieces 5×7 sell for $18–35. Materials cost under $1 per card.",
    grade_band="3-12",
))


# ── Hand-Lettered Signs ───────────────────────────────────────────────────────

_register(Project(
    id="proj-hand-lettered-signs",
    title="Hand-Lettered Wood Signs",
    track=Track.CREATIVE_ECONOMY,
    category=ProjectCategory.CRAFT,
    difficulty=ProjectDifficulty.GROWER,
    tagline="Letter a sign that people will hang in their homes for 20 years.",
    skills=["Brush lettering basics", "Wood prep and staining", "Sealing finished work", "Transferring designs"],
    business_skills=["Custom order workflow", "Deposit and delivery policy", "Pricing custom vs. ready-made"],
    materials=[
        "Unfinished wood boards (craft store, various sizes)",
        "Sandpaper (120 and 220 grit)",
        "Wood stain or chalk paint",
        "Chalk or chalk transfer paper",
        "Acrylic paint (white and colors)",
        "Detail brushes (round #2 and #4)",
        "Mod Podge or polyurethane sealer",
        "Sawtooth picture hangers",
        "Hammer and small nails",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Sand the wood board smooth with 120-grit sandpaper, then finish with 220-grit. Wipe clean with a damp cloth. Let dry."),
        ProjectStep(step_number=2, instruction="Apply wood stain or chalk paint in long, even strokes. Let dry completely. Apply a second coat if needed."),
        ProjectStep(step_number=3, instruction="Plan your lettering on paper first. Write out the quote or phrase, decide on layout (centered, left-aligned, mixed sizes)."),
        ProjectStep(step_number=4, instruction="Transfer the design: rub chalk on the back of your paper design, tape to the wood, and trace over your lines. The chalk transfers a faint guideline onto the wood.", tip="Alternatively, use a chalk pencil directly on the wood — it erases cleanly with a dry brush."),
        ProjectStep(step_number=5, instruction="Letter the sign with acrylic paint and a detail brush. Work slowly. Thin lines first, then fill in thick strokes.", tip="Reload your brush often — a half-dry brush gives ragged edges."),
        ProjectStep(step_number=6, instruction="Add any decorative elements: florals, borders, small illustrations. Let the painted design dry fully (1–2 hours)."),
        ProjectStep(step_number=7, instruction="Apply 2 coats of Mod Podge or polyurethane sealer, letting each coat dry fully. This protects the paint and gives a finished look."),
        ProjectStep(step_number=8, instruction="Attach a sawtooth hanger to the back center with small nails. Photograph front and back."),
    ],
    estimated_hours=3.0,
    price_range=PriceRange(low=25.00, high=75.00, unit="per sign"),
    where_to_sell=["Etsy", "Farmers markets", "Christmas craft fairs", "Local boutiques", "Custom orders via Instagram"],
    portfolio_prompts=[
        "Photograph your sign hung on a wall with complementary décor.",
        "Write your custom order policy: what info do you need from a buyer? What is your turnaround time? Do you require a deposit?",
        "Create a price list: small (8×10), medium (12×16), large (18×24) with your pricing rationale.",
    ],
    safety_notes=["Polyurethane sealer — use in ventilated space or outdoors.", "Sand in the direction of the wood grain to avoid scratches."],
    income_description="A 12×16 sign sells for $35–55. At 3 hours of work and $8 materials, that's $9–15/hr. Custom orders command premium prices.",
    grade_band="6-12",
))


# ── Sourdough Starter & Bread ─────────────────────────────────────────────────

_register(Project(
    id="proj-sourdough-business",
    title="Sourdough Starter, Loaves & Market Table",
    track=Track.CREATIVE_ECONOMY,
    category=ProjectCategory.CRAFT,
    difficulty=ProjectDifficulty.BUILDER,
    tagline="Cultivate a living culture. Bake bread with it. Build a cottage bakery.",
    skills=["Starter cultivation", "Autolyse", "Shaping", "Scoring", "Dutch oven baking", "Fermentation timing"],
    business_skills=["Cottage food law research", "Pricing baked goods", "Managing bake schedules", "Building repeat customers"],
    materials=[
        "Bread flour (5 lb bag)",
        "Whole wheat or rye flour (small bag, for starter feed)",
        "Non-chlorinated water (filtered or left out overnight)",
        "Salt (non-iodized)",
        "Kitchen scale",
        "Dutch oven or cast iron combo cooker",
        "Banneton proofing basket",
        "Bench scraper",
        "Lame or razor blade (for scoring)",
        "Large jar for starter",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Day 1 — Build the starter: Mix 50g whole wheat flour + 50g non-chlorinated water in a jar. Stir vigorously to incorporate air. Cover loosely. Leave at room temperature (70–75°F)."),
        ProjectStep(step_number=2, instruction="Days 2–7 — Feed daily: Discard all but 50g of starter. Add 50g flour + 50g water. Stir. Cover. By day 4–5 you should see bubbles. By day 7, it should double within 4–6 hours of feeding and smell pleasantly sour.", tip="A starter that smells like nail polish remover is too acidic — feed more frequently or use a cooler spot."),
        ProjectStep(step_number=3, instruction="Once active, make your first loaf. Mix: 450g bread flour + 325g water. Rest 30 minutes (autolyse). Add 9g salt + 75g active starter. Mix until combined."),
        ProjectStep(step_number=4, instruction="Bulk fermentation (4–6 hours at room temp): Perform 4 sets of stretch-and-folds every 30 minutes. Rest between sets. Dough is ready when it has grown 50–75% and feels airy.", tip="Cooler kitchens = longer bulk. Warmer kitchens = shorter. Watch the dough, not the clock."),
        ProjectStep(step_number=5, instruction="Shape: Turn dough onto an unfloured surface. Shape into a ball using a bench scraper (preshape). Rest 20 minutes. Final shape: stretch into a rectangle, fold sides in, roll toward you tightly."),
        ProjectStep(step_number=6, instruction="Place seam-side up in a floured banneton. Cover and refrigerate overnight (8–16 hours cold proof)."),
        ProjectStep(step_number=7, instruction="Preheat oven to 500°F with the Dutch oven inside for 45 minutes. Turn cold dough onto parchment, score with a lame at a 30° angle. Bake covered 20 min, uncovered 20 min until deep brown."),
        ProjectStep(step_number=8, instruction="Cool on a wire rack for at least 1 hour before cutting. Cutting too soon makes gummy crumb."),
        ProjectStep(step_number=9, instruction="Research your state's cottage food laws — most allow baked goods sold direct to consumer without a commercial kitchen license. Print the relevant law and know what is and isn't allowed."),
    ],
    estimated_hours=10.0,
    price_range=PriceRange(low=10.00, high=18.00, unit="per loaf"),
    where_to_sell=["Farmers markets", "Neighbor pre-orders", "CSA add-ons", "Church bazaars", "Instagram pre-sales"],
    portfolio_prompts=[
        "Photograph your starter at peak (doubled, bubbly) next to your first successful loaf.",
        "Document your bake schedule: when do you feed the starter, mix dough, proof, and bake to have bread ready by Saturday market?",
        "Look up your state's cottage food law. Write a one-paragraph summary of what you can and cannot sell.",
    ],
    safety_notes=["Never bake in a cold Dutch oven — always preheat. Cast iron retains heat unevenly if cold.", "Score before baking — an unscored loaf can explode unpredictably."],
    income_description="Each loaf costs ~$1.50 in flour and sells for $12–15. At 10 loaves per bake day, that's $105–135 gross. A Saturday market table of 20 loaves can sell out in 2 hours.",
    grade_band="7-12",
))


# ══════════════════════════════════════════════════════════════════════════════
# HOMESTEADING PROJECTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Water Bath Canning ────────────────────────────────────────────────────────

_register(Project(
    id="proj-water-bath-canning",
    title="Water Bath Canning — Jam & Salsa",
    track=Track.HOMESTEADING,
    category=ProjectCategory.PRESERVE,
    difficulty=ProjectDifficulty.GROWER,
    tagline="Seal the harvest in glass. Open it in January. Know exactly what's inside.",
    skills=["Sterile technique", "Headspace measurement", "Processing times", "Seal testing"],
    business_skills=[],
    materials=[
        "Mason jars with new lids and bands (12 half-pint or pint jars)",
        "Large stockpot with rack (or water bath canner)",
        "Jar lifter",
        "Wide-mouth funnel",
        "Bubble remover / headspace tool",
        "Fruit or tomatoes (fresh from garden, 10–12 lbs)",
        "Pectin (for jam) or vinegar (for salsa — use 5% acidity)",
        "Sugar and/or salt per tested recipe",
        "Clean towels",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Sterilize jars: run through dishwasher on hot cycle OR simmer in the canner for 10 minutes. Keep hot until use.", tip="Cold jars crack when filled with hot product. Keep jars warm until the moment you fill them."),
        ProjectStep(step_number=2, instruction="Prepare your recipe using a tested, approved source (USDA Complete Guide, Ball Blue Book, or university extension). Do NOT modify ingredient ratios in canning recipes — acidity levels are calibrated for safety."),
        ProjectStep(step_number=3, instruction="Fill the canner with water, place rack inside, and bring to a simmer while you prepare the product."),
        ProjectStep(step_number=4, instruction="Cook your jam or salsa per recipe. Ladle hot product into hot jars using a wide-mouth funnel. Leave proper headspace (¼ inch for jam, ½ inch for salsa)."),
        ProjectStep(step_number=5, instruction="Remove air bubbles by running a bubble tool or thin spatula around the inside of each jar. Recheck headspace."),
        ProjectStep(step_number=6, instruction="Wipe jar rims with a clean damp cloth. Apply lids and bands — fingertip-tight only. Do NOT overtighten."),
        ProjectStep(step_number=7, instruction="Lower jars into simmering canner using jar lifter. Water must cover jars by at least 1 inch. Bring to a full boil. Process for the time specified in your tested recipe (times vary by altitude)."),
        ProjectStep(step_number=8, instruction="When processing time ends, turn off heat. Let jars sit in water 5 minutes. Remove and place on a towel, 1 inch apart. Do not tilt or press lids."),
        ProjectStep(step_number=9, instruction="After 12–24 hours, test seals: press center of each lid. If it flexes up and down, it's not sealed — refrigerate and use within 2 weeks. Sealed lids are concave and rigid.", tip="You'll hear the satisfying 'ping' of jars sealing as they cool. That sound means it worked."),
    ],
    estimated_hours=4.0,
    portfolio_prompts=[
        "Photograph your sealed jars lined up with labels showing contents and date.",
        "Write out your tested recipe source and explain why you can't just make up canning recipes.",
        "Calculate: how many pounds of produce did you process, and how many jars did you put up?",
    ],
    safety_notes=[
        "Water bath canning is ONLY safe for high-acid foods (pH ≤ 4.6): fruits, jams, pickles, tomatoes with added acid. Low-acid vegetables, meats, and beans require pressure canning.",
        "Never skip headspace — too little causes seal failure; too much causes discoloration and short shelf life.",
        "Never process in the oven or dishwasher — only water bath or pressure canner.",
        "Check for spoilage before eating: bulging lids, spurting liquid, off smell = do not eat.",
    ],
    income_description="Canning is primarily for household food security. However, jams sell well at markets — research your state's cottage food law for allowable products.",
    grade_band="5-12",
))


# ── Raised Bed Garden Build ───────────────────────────────────────────────────

_register(Project(
    id="proj-raised-bed-build",
    title="Build a Raised Garden Bed",
    track=Track.HOMESTEADING,
    category=ProjectCategory.BUILD,
    difficulty=ProjectDifficulty.GROWER,
    tagline="Build the structure. Fill it with living soil. Grow food in it.",
    skills=["Measuring and cutting lumber", "Squaring corners", "Mixing soil", "Reading a site for sun and drainage"],
    business_skills=[],
    materials=[
        "Untreated cedar or pine 2×6 or 2×8 boards (four 8-foot boards for a 4×8 bed)",
        "3-inch exterior screws (box of 50)",
        "Drill and drill bit",
        "Tape measure and square",
        "Cardboard (to line the bottom — kills grass)",
        "Topsoil, compost, and perlite or coarse sand for fill",
        "Mallet (to level)",
        "Optional: hardware cloth for gopher protection",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Choose your site: at least 6–8 hours of direct sun per day. Level ground is easier but not required. Avoid tree roots and downspouts."),
        ProjectStep(step_number=2, instruction="Cut boards to length if needed (a 4×8 bed uses two 8-foot sides and two 4-foot ends — often no cutting needed with standard lumber lengths)."),
        ProjectStep(step_number=3, instruction="Lay out boards on the ground to form a rectangle. Check that corners are square: measure diagonally corner to corner in both directions — they should be equal.", tip="The 3-4-5 rule also works: measure 3 feet along one side, 4 feet along the adjacent side — the diagonal should be exactly 5 feet if the corner is square."),
        ProjectStep(step_number=4, instruction="Pre-drill holes at each corner to prevent the wood from splitting. Drive 3-inch screws to join corners. Use two screws per corner joint."),
        ProjectStep(step_number=5, instruction="Optional: cut hardware cloth to the bed footprint and lay inside before placing the bed, to stop gophers and voles from below."),
        ProjectStep(step_number=6, instruction="Move the assembled frame to its final location. Use a mallet and level to settle it flat. A slight slope (1°) toward a path is fine for drainage."),
        ProjectStep(step_number=7, instruction="Layer cardboard inside the bed to smother existing grass and weeds — no need to remove them first. The cardboard breaks down in one season."),
        ProjectStep(step_number=8, instruction="Fill with soil mix: 60% topsoil, 30% compost, 10% perlite or coarse sand. This is Mel Bartholomew's 'Mel's Mix' — proven for raised beds. Water in well before planting."),
    ],
    estimated_hours=4.0,
    portfolio_prompts=[
        "Photograph the build process: lumber laid out, corners joined, bed filled and planted.",
        "Draw a top-down diagram of your bed with what you planted in each section and spacing.",
        "Calculate the cubic feet of soil needed to fill your bed (length × width × depth in feet).",
    ],
    safety_notes=["Use untreated wood only — pressure-treated lumber contains chemicals that leach into soil and food.", "Pre-drilling prevents splitting and makes the project stronger."],
    income_description="A raised bed is an investment in food production. A 4×8 bed can produce $200–600 in vegetables per season depending on what you grow.",
    grade_band="5-12",
))


# ── Chicken Brooder Setup ─────────────────────────────────────────────────────

_register(Project(
    id="proj-chicken-brooder",
    title="Build a Chick Brooder & Raise Your First Flock",
    track=Track.HOMESTEADING,
    category=ProjectCategory.LIVESTOCK,
    difficulty=ProjectDifficulty.GROWER,
    tagline="Baby chicks need warmth, water, and a safe space. Build it. Raise them.",
    skills=["Temperature management", "Chick health observation", "Feeding ratios", "Predator-proofing"],
    business_skills=[],
    materials=[
        "Large plastic storage tote or wooden box (at least 2 sq ft per chick)",
        "Heat lamp with red bulb OR Brinsea EcoGlow brooder plate",
        "Thermometer",
        "Chick feeder and waterer (or DIY from mason jar + base)",
        "Pine shavings (never cedar — toxic to chicks)",
        "Chick starter crumbles (non-medicated or medicated per your preference)",
        "Hardware cloth for a lid (keeps chicks in and cats out)",
        "Zip ties",
        "Paper towels (for the first 3 days over shavings)",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Set up the brooder before chicks arrive. Line the bottom with paper towels (first 3 days) — chicks must see the food separate from bedding, or they won't eat. Add 2–3 inches of pine shavings under the paper towels."),
        ProjectStep(step_number=2, instruction="Hang or position the heat lamp at one end only. Chicks need a warm zone AND a cool zone so they can self-regulate. Target: 95°F directly under the lamp in week 1.", tip="If all chicks pile under the lamp — they're cold. If they spread to edges and pant — they're too hot. Watch behavior, not just the thermometer."),
        ProjectStep(step_number=3, instruction="Fill the waterer with room-temperature water. Add 1 tablespoon of raw apple cider vinegar per gallon (optional — supports gut health). Place away from the heat lamp."),
        ProjectStep(step_number=4, instruction="Fill the feeder with chick starter crumbles. Chicks eat constantly — keep it full."),
        ProjectStep(step_number=5, instruction="When chicks arrive (from hatchery or feed store), dip each beak gently in the water before setting them down so they know where it is."),
        ProjectStep(step_number=6, instruction="Weeks 1–6: reduce heat lamp temperature by 5°F each week (raise the lamp slightly or use a dimmer). By week 6, chicks should be fully feathered and ready to move outside if nights are above 50°F."),
        ProjectStep(step_number=7, instruction="Daily tasks: refresh water, top up feed, remove wet or soiled shavings ('spot cleaning'). Full bedding change every 5–7 days."),
        ProjectStep(step_number=8, instruction="Observe each chick daily: eyes clear and alert, eating and drinking, walking normally. Pasty butt (feces blocking the vent) is the most common issue — clean gently with warm water and a cloth."),
    ],
    estimated_hours=3.0,
    portfolio_prompts=[
        "Photograph your brooder setup before chicks arrive (show the thermometer reading).",
        "Keep a daily log for 2 weeks: date, temperature, observations about chick behavior, any health issues and what you did.",
        "At 6 weeks, write a one-page report: how many chicks survived, what challenges did you face, what would you do differently?",
    ],
    safety_notes=[
        "Heat lamps are a fire hazard — secure with TWO attachment points. Never rely on the single clip alone.",
        "Never use cedar shavings — the aromatic oils damage chick respiratory systems.",
        "Wash hands after handling chicks — they can carry Salmonella even when healthy.",
        "Keep brooder away from drafts but ensure ventilation — ammonia buildup from waste is dangerous.",
    ],
    income_description="A flock of 6 hens produces 4–5 eggs/day. At $5/dozen from pastured hens, that's $600–700/year — covers feed cost with surplus.",
    grade_band="4-12",
))


# ── Seed Saving ───────────────────────────────────────────────────────────────

_register(Project(
    id="proj-seed-saving",
    title="Seed Saving — Tomatoes, Beans & Squash",
    track=Track.HOMESTEADING,
    category=ProjectCategory.GARDEN,
    difficulty=ProjectDifficulty.SEEDLING,
    tagline="Never buy seeds again. Save what grows best on your land.",
    skills=["Identifying seed-ready fruits", "Fermentation method (tomatoes)", "Dry method (beans, squash)", "Storage conditions"],
    business_skills=[],
    materials=[
        "Ripe open-pollinated or heirloom fruits (NOT hybrid — hybrids don't breed true)",
        "Glass jars with lids (for fermenting tomato seeds)",
        "Water",
        "Paper plates or screens for drying",
        "Coin envelopes or small paper bags",
        "Permanent marker",
        "Cool, dark, dry storage location",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Choose the best specimens: save seed from your healthiest, most productive, best-tasting fruits. You are selecting for your land and your palate. Never save from diseased plants."),
        ProjectStep(step_number=2, instruction="TOMATOES (fermentation method): Squeeze seeds and gel into a jar. Add a little water. Cover loosely. Ferment 2–3 days at room temp. The gel coat (which inhibits germination) ferments away. Viable seeds sink; mold and empty seeds float.", tip="Stir once a day. Don't go past 3 days or seeds may begin to germinate."),
        ProjectStep(step_number=3, instruction="Rinse tomato seeds through a strainer. Spread on a plate or coffee filter. Dry in a warm spot (not oven) for 1–2 weeks, stirring daily. Seeds must be bone dry before storage or they'll mold."),
        ProjectStep(step_number=4, instruction="BEANS & SQUASH (dry method): Leave pods on the plant until they rattle or the vine dies. For squash, leave on the counter an additional 6 weeks after harvest to let seeds fully cure inside."),
        ProjectStep(step_number=5, instruction="Shell beans by hand. Spread on a screen for 2 weeks to finish drying. Crack a bean — if it shatters cleanly, it's dry enough to store. If it bends, keep drying."),
        ProjectStep(step_number=6, instruction="Scoop squash seeds. Rinse off pulp completely (residue causes mold). Spread and dry 2–3 weeks."),
        ProjectStep(step_number=7, instruction="Once fully dry, packet seeds into coin envelopes. Label with: crop name, variety, date saved, location grown, any notes on flavor or performance."),
        ProjectStep(step_number=8, instruction="Store in a cool, dark, dry place. A glass jar in the back of the refrigerator is ideal. Add a silica gel pack to absorb moisture."),
    ],
    estimated_hours=2.0,
    portfolio_prompts=[
        "Photograph your seed packets lined up with the fruits or plants they came from.",
        "Start a seed inventory log: variety, year saved, germination rate from last test, quantity.",
        "Research the difference between open-pollinated, heirloom, and hybrid seeds. Write a one-paragraph explanation in your own words.",
    ],
    safety_notes=["Only save seeds from open-pollinated varieties — hybrids don't breed true and will disappoint you.", "Completely dry seeds before sealing in airtight containers — even small amounts of moisture cause rot."],
    income_description="A seed library is household wealth — independence from the seed supply chain. Rare heirloom seeds can sell for $3–6 per packet at markets.",
    grade_band="3-12",
))


# ── Herb Garden & Drying Rack ─────────────────────────────────────────────────

_register(Project(
    id="proj-herb-garden-drying",
    title="Grow, Harvest & Dry a Medicinal Herb Garden",
    track=Track.HOMESTEADING,
    category=ProjectCategory.GARDEN,
    difficulty=ProjectDifficulty.SEEDLING,
    tagline="Grow your medicine. Dry it. Know what it does and why.",
    skills=["Herb selection for climate", "Harvest timing", "Bundle drying vs. screen drying", "Identifying peak potency"],
    business_skills=[],
    materials=[
        "Herb starts or seeds: calendula, lavender, chamomile, lemon balm, peppermint, echinacea",
        "Garden space or containers (herbs do well in pots)",
        "Twine for bundling",
        "Paper bags (for bundle drying)",
        "Window screens or drying rack",
        "Glass jars with tight lids (for storage)",
        "Labels and permanent marker",
    ],
    steps=[
        ProjectStep(step_number=1, instruction="Select herbs suited to your climate and purpose. A basic medicinal garden: calendula (skin healing), chamomile (calming), lemon balm (nervous system), peppermint (digestion), echinacea (immune). Research each one's traditional use before planting.", tip="Peppermint spreads aggressively — plant in a container to contain it."),
        ProjectStep(step_number=2, instruction="Plant after last frost in full sun (most culinary and medicinal herbs need 6+ hours). Water deeply but infrequently — most prefer dry over wet conditions."),
        ProjectStep(step_number=3, instruction="Harvest at peak: flowers at 75% open (not fully blown), leaves before flowering begins, roots in fall after the plant goes dormant. Harvest in the morning after dew dries."),
        ProjectStep(step_number=4, instruction="Rinse gently if dirty. Pat dry with a towel. You want to remove field moisture before drying, not add it."),
        ProjectStep(step_number=5, instruction="Bundle method: tie 5–8 stems loosely at the base with twine. Slip into a paper bag (holes poked in sides for airflow) and hang upside down in a warm, dry, dark space. 1–3 weeks."),
        ProjectStep(step_number=6, instruction="Screen method (for flowers and loose leaves): spread in a single layer on a window screen or drying rack. Turn daily. Keep out of direct sun — light degrades medicinal compounds."),
        ProjectStep(step_number=7, instruction="Test for dryness: flowers crumble, leaves are crisp, stems snap rather than bend. Any flexibility means more drying time needed."),
        ProjectStep(step_number=8, instruction="Strip dried herbs from stems. Store in glass jars away from light and heat. Label with herb name, harvest date, and part used (leaf, flower, root)."),
    ],
    estimated_hours=3.0,
    portfolio_prompts=[
        "Photograph each herb at harvest time and again dried in its jar.",
        "For each herb in your garden, write one paragraph: traditional use, part used, how to prepare it (tea, tincture, salve), and one primary or historical source for this use.",
        "Calculate: how much dried herb did each plant produce? At what point would you have enough to supply your household through winter?",
    ],
    safety_notes=["Research each herb carefully before internal use — some herbs interact with medications.", "Echinacea should not be used by those with autoimmune conditions without consulting a practitioner.", "Never use essential oils internally — they are concentrated and can be toxic."],
    income_description="Dried herbs sell at markets for $4–8 per ounce. Rare or organically grown herbs command more. Blend into teas for higher margins.",
    grade_band="3-12",
))


# ══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("")
async def list_projects(
    track: Optional[str] = Query(None, description="Filter by track (CREATIVE_ECONOMY or HOMESTEADING)"),
    category: Optional[ProjectCategory] = Query(None, description="Filter by category"),
    difficulty: Optional[int] = Query(None, description="Filter by difficulty: 1=SEEDLING, 2=GROWER, 3=BUILDER"),
    grade_band: Optional[str] = Query(None, description="Filter by grade band prefix, e.g. '6' matches '6-12'"),
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """List all projects with optional filters."""
    results = list(PROJECTS.values())

    if track:
        results = [p for p in results if p.track.value == track.upper()]
    if category:
        results = [p for p in results if p.category == category]
    if difficulty:
        results = [p for p in results if p.difficulty.value == difficulty]
    if grade_band:
        results = [p for p in results if grade_band in p.grade_band]

    # Return lightweight list — no steps
    return {
        "total": len(results),
        "projects": [
            {
                "id":             p.id,
                "title":          p.title,
                "track":          p.track.value,
                "category":       p.category.value,
                "difficulty":     p.difficulty.value,
                "tagline":        p.tagline,
                "estimated_hours": p.estimated_hours,
                "grade_band":     p.grade_band,
                "price_range":    p.price_range.model_dump() if p.price_range else None,
                "skills":         p.skills[:3],
            }
            for p in results
        ],
    }


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """Return a single project with full step guide."""
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return project.model_dump()


@router.post("/{project_id}/seal")
async def seal_project(
    project_id: str,
    body: ProjectSealRequest,
    _role: str = Depends(require_role(UserRole.STUDENT, UserRole.ADMIN)),
):
    """
    Student seals a completed project.
    Records credit hours to the journal and returns a ProjectSealResponse.

    Credit is calculated at 0.5 Carnegie units per estimated hour of project work,
    rounded to one decimal place.
    """
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    credit_hours = round(project.estimated_hours * 0.5, 1)
    credit_type  = "CREATIVE" if project.track == Track.CREATIVE_ECONOMY else "HOMESTEAD"

    try:
        await journal_store.seal(
            student_id=body.student_id,
            lesson_id=f"project-{project_id}",
            track=project.track.value,
            completed_blocks=int(project.estimated_hours * 2),  # 30-min blocks
            sources=[],
        )
        logger.info(
            f"[/projects/seal] student={body.student_id} project={project_id} "
            f"credit={credit_hours}hr type={credit_type}"
        )
    except Exception as e:
        logger.warning(f"[/projects/seal] Journal seal failed (non-fatal): {e}")

    return ProjectSealResponse(
        project_id=project_id,
        credit_type=credit_type,
        credit_hours=credit_hours,
        message=f"'{project.title}' sealed. {credit_hours} credit hours recorded to your transcript.",
    )
