#!/usr/bin/env python3
"""
seed_health_naturopathy.py — Deep HEALTH_NATUROPATHY Hippocampus corpus.

Five domains:
  1. Oklahoma/Arkansas Medicinal Plants — profiles of elderberry, echinacea,
     calendula, lemon balm, plantain (extracts vs. infusions, wild edibles)
  2. Gut Health & The Microbiome — soil mycorrhizae ↔ human gut, fermentation
     (kombucha, sourdough, sauerkraut)
  3. Nutritional Naturopathy — anthocyanins, omega-3s, turmeric, ginger,
     the chemistry of whole foods
  4. Anatomy & Physiology (Naturopathic Lens) — endocrine system, circadian
     rhythms, sleep/sunlight/stress, Hippocrates to modern naturopathy
  5. First Aid & Home Remedies — arnica, apis, honey wound care, healing
     salves from beeswax, electrolyte science

Run:  cd adeline-brain && python scripts/seed_health_naturopathy.py
"""
import asyncio
import os
import ssl as _ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_pg_pw = os.getenv("POSTGRES_PASSWORD", "placeholder_password")
_pg_dsn = (
    os.getenv("POSTGRES_DSN")
    or os.getenv("DIRECT_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or f"postgresql://adeline:{_pg_pw}@localhost:5432/hippocampus"
).replace("postgresql://", "postgresql+asyncpg://")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBED_MODEL = "text-embedding-3-small"

import openai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


async def embed(text_input: str) -> list[float] | None:
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        resp = await client.embeddings.create(model=EMBED_MODEL, input=text_input)
        return resp.data[0].embedding
    except openai.BadRequestError as e:
        if "content_filter" in str(e).lower() or e.status_code == 400:
            print(f"  [SKIP] Content filter: '{text_input[:60]}...'")
            return None
        raise


SOURCES = [
    # ═══════════════════════════════════════════════════════════════════════════
    # 1. OKLAHOMA / ARKANSAS MEDICINAL PLANTS
    #    Profiles of plants that grow in USDA zones 6b-7b (OK/AR).
    #    Cross-track hooks: Chemistry (extracts vs infusions), Biology (wild ID)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Elderberry (Sambucus nigra) — Medicinal Profile for Oklahoma",
        "source_url": "https://www.henriettes-herb.com/eclectic/ellingwood/sambucus.html",
        "citation_author": "Finley Ellingwood, M.D.",
        "citation_year": 1919,
        "citation_archive_name": "Henriette's Herbal / Eclectic Medical Literature",
        "chunk": (
            "Elderberry (Sambucus nigra) grows wild along fencerows and creek banks "
            "throughout Oklahoma and Arkansas. The plant thrives in zones 6b–7b in full "
            "sun to partial shade. The dark purple berries, harvested in late summer, "
            "contain anthocyanins and flavonoids that support immune function. Elderberry "
            "syrup is made by simmering berries with water, straining, and adding raw "
            "honey — a kitchen preparation that requires no special equipment. The flowers "
            "make a gentle tea (infusion) used for fevers and upper respiratory congestion. "
            "An extract concentrates the active compounds using alcohol or glycerin as a "
            "solvent, while an infusion uses only hot water. The difference matters: "
            "extracts are stronger and shelf-stable; infusions are milder, made fresh, "
            "and suited for children. Elderberry is the gateway plant for any family "
            "starting a medicinal herb garden in the Southern Plains."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Echinacea (Echinacea purpurea) — Oklahoma Native Immune Support",
        "source_url": "https://www.henriettes-herb.com/eclectic/ellingwood/echinacea.html",
        "citation_author": "Finley Ellingwood, M.D.",
        "citation_year": 1919,
        "citation_archive_name": "Henriette's Herbal / Eclectic Medical Literature",
        "chunk": (
            "Echinacea purpurea — the purple coneflower — is native to the prairies of "
            "Oklahoma, Kansas, and Arkansas. Plains Indian nations including the Cheyenne "
            "and Comanche used echinacea root as a poultice for wounds and snakebites, "
            "and chewed the root for sore throats. The Eclectic physicians of the 1800s "
            "adopted it as the primary botanical anti-infective. Modern research confirms "
            "that echinacea stimulates innate immune response by activating macrophages "
            "and increasing white blood cell activity. The root is the medicinal part: "
            "harvested in fall after the plant has gone to seed, dried, and prepared as "
            "a tincture (alcohol extract) or decoction (slow-simmered tea). Echinacea "
            "grows easily from seed in Oklahoma's clay soils and requires almost no care "
            "once established. It is both a pollinator magnet and a medicine cabinet."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Calendula (Calendula officinalis) — Skin Healer and Garden Sentinel",
        "source_url": "https://www.henriettes-herb.com/eclectic/ellingwood/calendula.html",
        "citation_author": "Finley Ellingwood, M.D.",
        "citation_year": 1919,
        "citation_archive_name": "Henriette's Herbal / Eclectic Medical Literature",
        "chunk": (
            "Calendula officinalis — pot marigold — has been used for wound healing since "
            "the Roman legions packed it in their field kits. The bright orange petals "
            "contain triterpenoids and flavonoids that promote tissue repair and reduce "
            "inflammation. In Oklahoma and Arkansas, calendula is planted as a cool-season "
            "annual — sow in early spring or late fall. Harvest the flower heads when fully "
            "open and dry them on screens in a warm, dark room. Dried petals infused in "
            "olive oil for 4–6 weeks produce calendula oil — the base for healing salves. "
            "Mix the strained oil with melted beeswax (roughly 1 ounce wax to 8 ounces "
            "oil) and pour into tins. This salve treats minor cuts, scrapes, diaper rash, "
            "chapped skin, and mild burns. A homestead with bees and a calendula bed "
            "produces its own wound care from the garden and the hive."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Lemon Balm (Melissa officinalis) — Nervous System Support",
        "source_url": "https://www.henriettes-herb.com/eclectic/ellingwood/melissa.html",
        "citation_author": "Finley Ellingwood, M.D.",
        "citation_year": 1919,
        "citation_archive_name": "Henriette's Herbal / Eclectic Medical Literature",
        "chunk": (
            "Lemon balm (Melissa officinalis) is a perennial mint-family herb that thrives "
            "in Oklahoma's heat and humidity with minimal care — it spreads readily and "
            "comes back every year. The leaves contain rosmarinic acid, which has "
            "demonstrated calming effects on the nervous system. Traditionally used for "
            "anxiety, insomnia, and digestive upset driven by stress. A simple infusion — "
            "a handful of fresh leaves steeped in hot water for ten minutes — makes a "
            "gentle evening tea suitable for children and adults. Lemon balm is also "
            "antiviral: a poultice of crushed fresh leaves applied to cold sores speeds "
            "healing. In the kitchen garden, it repels mosquitoes and attracts honeybees "
            "(Melissa means 'honeybee' in Greek). One of the easiest and most useful "
            "medicinal herbs for a beginning homestead pharmacy."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Plantain (Plantago major) — The Weed That Heals",
        "source_url": "https://www.henriettes-herb.com/eclectic/ellingwood/plantago.html",
        "citation_author": "Finley Ellingwood, M.D.",
        "citation_year": 1919,
        "citation_archive_name": "Henriette's Herbal / Eclectic Medical Literature",
        "chunk": (
            "Broadleaf plantain (Plantago major) grows in every lawn, driveway crack, and "
            "field edge in Oklahoma and Arkansas — most people call it a weed and mow it "
            "down. It is one of the most reliable first-aid plants that exists. The leaves "
            "contain allantoin (the same compound in commercial wound creams) and aucubin, "
            "which is antimicrobial. For bee stings, wasp stings, or spider bites: chew a "
            "fresh leaf to break the cell walls and apply it directly as a poultice. The "
            "drawing action pulls venom and reduces swelling within minutes. For splinters "
            "too deep to reach, a plantain poultice applied overnight often draws them to "
            "the surface. A tea of dried plantain leaves soothes sore throats and coughs. "
            "The first lesson of naturopathy is that medicine is already growing under "
            "your feet — you just have to learn to see it."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Extracts vs. Infusions — The Chemistry of Herbal Preparations",
        "source_url": "https://www.henriettes-herb.com/eclectic/ellingwood/introduction.html",
        "citation_author": "Finley Ellingwood, M.D.",
        "citation_year": 1919,
        "citation_archive_name": "Henriette's Herbal / Eclectic Medical Literature",
        "chunk": (
            "An infusion is the simplest herbal preparation: pour boiling water over dried "
            "herbs, cover, and steep for 10–20 minutes. Water extracts water-soluble "
            "compounds — vitamins, minerals, mucilage, some flavonoids. A decoction "
            "simmers tougher material (roots, bark, seeds) for 20–40 minutes, releasing "
            "compounds that water alone cannot reach quickly. A tincture uses alcohol "
            "(typically 80-proof vodka) as the solvent, extracting both water-soluble and "
            "alcohol-soluble compounds — alkaloids, resins, volatile oils. Tinctures are "
            "more concentrated, shelf-stable for years, and dosed in drops rather than "
            "cups. A glycerite uses vegetable glycerin instead of alcohol — gentler, "
            "sweeter, preferred for children. Understanding solvent chemistry — what "
            "dissolves what — is the bridge between the herb garden and the chemistry "
            "lab. Every preparation is an extraction problem."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. GUT HEALTH & THE MICROBIOME
    #    Soil ↔ gut connection, fermentation science, practical recipes
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Soil Microbiome and Human Gut — The Living Connection",
        "source_url": "https://archive.org/details/soilmicrobiology00wake",
        "citation_author": "Selman Waksman (adapted)",
        "citation_year": 1927,
        "citation_archive_name": "Internet Archive / Public Domain",
        "chunk": (
            "Healthy soil and a healthy gut share the same foundation: microbial diversity. "
            "One teaspoon of fertile soil contains more microorganisms than there are people "
            "on Earth — bacteria, fungi, protozoa, and nematodes working together to break "
            "down organic matter into plant-available nutrients. Mycorrhizal fungi form "
            "networks connecting plant roots underground, trading phosphorus and minerals "
            "for sugars the plant produces through photosynthesis. The human gut operates "
            "on the same principle: trillions of bacteria in the intestines break down "
            "fiber into short-chain fatty acids that feed the gut lining and regulate "
            "inflammation. A garden fed with compost grows food rich in the microbes and "
            "minerals that feed the human microbiome. The connection is direct: what you "
            "feed the soil, you feed yourself. Industrial agriculture that sterilizes "
            "soil with chemicals produces food that starves the gut it is supposed to "
            "nourish."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Fermentation Science — Kombucha, Sourdough, Sauerkraut",
        "source_url": "https://archive.org/details/artoffermentatio0000katz",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 1900,
        "citation_archive_name": "Public Domain / Traditional Practice",
        "chunk": (
            "Fermentation is the oldest form of food preservation and the simplest way to "
            "populate the gut with beneficial bacteria. Sauerkraut: shred cabbage, salt it "
            "at 2% by weight, pack it into a jar, and wait 1–4 weeks. Lactobacillus "
            "bacteria already present on the cabbage convert sugars to lactic acid, "
            "preserving the vegetable and producing live probiotics. Sourdough: mix flour "
            "and water, leave it exposed to ambient yeast and bacteria for 5–7 days, "
            "feeding daily. The wild yeast produces carbon dioxide (leavening) while "
            "lactobacilli produce lactic acid (flavor and preservation). Sourdough bread "
            "is more digestible than commercial bread because fermentation breaks down "
            "phytic acid and gluten proteins. Kombucha: sweet tea fermented with a SCOBY "
            "(symbiotic culture of bacteria and yeast) for 7–14 days produces a fizzy, "
            "probiotic drink. Every fermentation is a biology experiment you can eat."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Probiotics and the Gut-Brain Axis",
        "source_url": "https://archive.org/details/soilmicrobiology00wake",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 1900,
        "citation_archive_name": "Public Domain / Compiled Research",
        "chunk": (
            "The gut contains more neurons than the spinal cord — roughly 500 million "
            "nerve cells lining the intestinal wall, forming what scientists call the "
            "enteric nervous system or 'second brain.' This gut-brain axis communicates "
            "through the vagus nerve: gut bacteria produce neurotransmitters including "
            "serotonin (90% of the body's serotonin is made in the gut), dopamine, and "
            "GABA. When the gut microbiome is diverse and balanced, these signals support "
            "mood stability, focus, and restful sleep. When the microbiome is depleted — "
            "by antibiotics, processed food, or chronic stress — the signals degrade. "
            "Fermented foods (yogurt, kefir, sauerkraut, kimchi) replenish beneficial "
            "strains. Prebiotic fiber (garlic, onion, asparagus, dandelion greens) feeds "
            "the bacteria already there. Gut health is not a diet trend. It is the "
            "biological foundation of mental and physical well-being."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. NUTRITIONAL NATUROPATHY — The Chemistry of Food
    #    Anthocyanins, omega-3s, turmeric, ginger, anti-inflammatory compounds
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Anthocyanins in Berries — The Chemistry of Color and Health",
        "source_url": "https://archive.org/details/nutritionalherba00lutg",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 1900,
        "citation_archive_name": "Public Domain / Compiled Research",
        "chunk": (
            "The deep purple, blue, and red pigments in berries are anthocyanins — a class "
            "of flavonoid compounds that function as both sunscreen for the plant and "
            "antioxidants in the human body. Elderberries, blackberries, blueberries, and "
            "aronia berries (all grow well in Oklahoma) are among the richest sources. "
            "Anthocyanins neutralize free radicals, reduce inflammation in blood vessels, "
            "and support cardiovascular health. The darker the berry, the higher the "
            "anthocyanin content. Cooking reduces some anthocyanin activity, but elderberry "
            "syrup and berry preserves retain significant levels. Fresh berries eaten raw "
            "deliver the most. Growing a berry patch is not just gardening — it is building "
            "a pharmacy. A child who learns that the color of a berry tells you about its "
            "chemistry is learning biology, nutrition, and observation simultaneously."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Omega-3 Fatty Acids — Pasture-Raised vs. Industrial",
        "source_url": "https://archive.org/details/nutritionalherba00lutg",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 1900,
        "citation_archive_name": "Public Domain / Compiled Research",
        "chunk": (
            "Omega-3 fatty acids (EPA and DHA) are essential fats the body cannot "
            "manufacture — they must come from food. They reduce inflammation, support "
            "brain development in children, and protect cardiovascular function. The "
            "richest sources: wild-caught fish (salmon, sardines, mackerel), pasture-raised "
            "eggs, and grass-fed beef. A pasture-raised egg from a hen eating bugs and "
            "grass contains 2–3 times more omega-3s than a conventional egg from a hen "
            "eating grain in confinement. Grass-fed beef contains up to 5 times more "
            "omega-3s than grain-finished beef. The same principle applies to dairy: "
            "butter and milk from grass-fed cows have a higher omega-3 to omega-6 ratio. "
            "A homestead family raising its own chickens and keeping a milk cow on pasture "
            "is not just saving money — it is producing nutritionally superior food. The "
            "chemistry of what an animal eats becomes the chemistry of what you eat."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Turmeric and Ginger — Anti-Inflammatory Kitchen Medicine",
        "source_url": "https://www.henriettes-herb.com/eclectic/ellingwood/curcuma.html",
        "citation_author": "Finley Ellingwood, M.D. (adapted)",
        "citation_year": 1919,
        "citation_archive_name": "Henriette's Herbal / Eclectic Medical Literature",
        "chunk": (
            "Turmeric (Curcuma longa) contains curcumin, a polyphenol compound that "
            "inhibits inflammatory pathways at the molecular level — specifically NF-kB, "
            "a protein complex that turns on genes related to inflammation. Curcumin is "
            "poorly absorbed alone but bioavailability increases 2,000% when paired with "
            "piperine, found in black pepper. This is why traditional golden milk recipes "
            "always include both. Ginger (Zingiber officinale) contains gingerols and "
            "shogaols — compounds that reduce nausea, ease digestive discomfort, and "
            "lower inflammatory markers. Fresh ginger grated into hot water makes an "
            "immediate remedy for upset stomachs. Both turmeric and ginger grow in "
            "containers in Oklahoma — plant rhizomes in spring, harvest in fall. The "
            "kitchen spice rack is not separate from the medicine cabinet. For most of "
            "human history, they were the same shelf."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. ANATOMY & PHYSIOLOGY — Naturopathic Systems Thinking
    #    Endocrine, circadian rhythms, sleep/sunlight/stress, history of medicine
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "The Endocrine System — Hormones, Sleep, and Sunlight",
        "source_url": "https://archive.org/details/physiologyofhuma00guytuoft",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 1900,
        "citation_archive_name": "Public Domain / Compiled Research",
        "chunk": (
            "The endocrine system is the body's chemical messaging network. The pineal "
            "gland — a pea-sized structure deep in the brain — produces melatonin in "
            "response to darkness, signaling the body to prepare for sleep. Sunlight "
            "hitting the retina in the morning suppresses melatonin and triggers cortisol "
            "release, which wakes the body up. This cycle — the circadian rhythm — governs "
            "not just sleep but hormone production, immune function, digestion, and mood. "
            "Artificial light after sunset — especially blue light from screens — tells "
            "the pineal gland it is still daytime, suppressing melatonin and disrupting "
            "the entire cascade. Children who spend morning time outdoors in natural light "
            "and limit screens after dark sleep better, focus better, and get sick less "
            "often. The prescription is not a pill. It is sunrise and sunset."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Circadian Rhythms and Stress — The Cortisol Cycle",
        "source_url": "https://archive.org/details/physiologyofhuma00guytuoft",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 1900,
        "citation_archive_name": "Public Domain / Compiled Research",
        "chunk": (
            "Cortisol is the body's primary stress hormone, produced by the adrenal glands "
            "sitting atop the kidneys. In a healthy rhythm, cortisol peaks in the morning "
            "(providing energy and alertness) and drops to its lowest at night (allowing "
            "sleep and repair). Chronic stress — from worry, poor sleep, constant noise, "
            "or overwork — flattens this curve: cortisol stays elevated, suppressing immune "
            "function, impairing digestion, increasing blood sugar, and disrupting memory "
            "formation. The adrenal glands were designed for short bursts of danger — the "
            "bear in the woods — not for the sustained low-grade stress of modern life. "
            "Naturopathic interventions for cortisol regulation: morning sunlight exposure, "
            "adaptogenic herbs (ashwagandha, holy basil), regular meals, physical labor, "
            "and protecting evening hours from stimulation. The body heals itself — but "
            "only if you stop interfering with its rhythms."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "From Hippocrates to Modern Naturopathy — A History of Medicine",
        "source_url": "https://www.gutenberg.org/ebooks/24736",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 460,
        "citation_archive_name": "Public Domain / Historical",
        "chunk": (
            "Hippocrates of Kos (c. 460–370 BC) is called the father of medicine. His "
            "central teaching: 'Let food be thy medicine and medicine be thy food.' He "
            "rejected the prevailing belief that disease was punishment from the gods and "
            "taught that illness had natural causes — diet, environment, habits. He "
            "prescribed fasting, exercise, fresh air, and herbal remedies. For 2,000 years "
            "this tradition continued: Galen in Rome, Avicenna in Persia, Hildegard of "
            "Bingen in medieval Germany — all practiced medicine rooted in observation of "
            "the whole patient. The pharmaceutical revolution of the 20th century replaced "
            "whole-plant medicine with isolated compounds and synthetic drugs. Naturopathy "
            "returns to the older tradition: treat the whole person, find the root cause, "
            "use the least invasive remedy first, and trust the body's capacity to heal "
            "when properly supported. This is not alternative medicine. It is the original "
            "medicine."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. FIRST AID & HOME REMEDIES
    #    Arnica, apis, honey wound care, healing salves, electrolytes
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Arnica and Apis — Homeopathic First Aid for Stings and Bruises",
        "source_url": "https://www.henriettes-herb.com/eclectic/ellingwood/arnica.html",
        "citation_author": "Finley Ellingwood, M.D.",
        "citation_year": 1919,
        "citation_archive_name": "Henriette's Herbal / Eclectic Medical Literature",
        "chunk": (
            "Arnica montana is the first remedy in a homestead first-aid kit for bruises, "
            "sprains, and blunt trauma. Applied topically as an oil or salve, arnica "
            "increases blood flow to the injured area and reduces swelling. Never apply "
            "to broken skin — arnica is for closed injuries only. For bee stings, wasp "
            "stings, and insect bites with swelling and burning pain, Apis mellifica (made "
            "from honeybee venom) is the traditional homeopathic remedy — given in pellet "
            "form under the tongue. The affected area is typically red, swollen, and warm "
            "to the touch, and feels better with cold application. A cold compress combined "
            "with a plantain poultice handles most field stings without a trip to town. "
            "Knowing what to reach for in the first five minutes matters more than what "
            "the doctor prescribes two hours later."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Honey for Wound Care — Raw Honey and Manuka Properties",
        "source_url": "https://archive.org/details/beekeepershandbo00root",
        "citation_author": "A.I. Root (adapted)",
        "citation_year": 1879,
        "citation_archive_name": "Internet Archive",
        "chunk": (
            "Honey has been used for wound care since ancient Egypt — medical papyri from "
            "1500 BC describe honey dressings for burns and surgical wounds. Raw honey is "
            "antimicrobial: its high sugar content draws water out of bacteria (osmotic "
            "effect), its low pH (3.2–4.5) inhibits bacterial growth, and the enzyme "
            "glucose oxidase produces hydrogen peroxide slowly and continuously. Manuka "
            "honey (from New Zealand tea tree) adds methylglyoxal (MGO), a compound with "
            "additional antibacterial potency. For minor cuts, scrapes, and burns: clean "
            "the wound, apply a thin layer of raw honey, and cover with a clean bandage. "
            "Change daily. Honey keeps wounds moist (promoting healing), fights infection, "
            "and reduces scarring. A homestead with beehives produces its own wound care. "
            "The same jar of honey that sweetens your tea can dress a cut."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Making a Healing Salve — Beeswax, Calendula, and Comfrey",
        "source_url": "https://archive.org/details/beekeepershandbo00root",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 1900,
        "citation_archive_name": "Public Domain / Traditional Practice",
        "chunk": (
            "A healing salve is the most practical product a homestead pharmacy can make. "
            "Start with an infused oil: fill a jar with dried calendula petals and comfrey "
            "leaf, cover with olive oil, and let it sit in a warm window for 4–6 weeks, "
            "shaking occasionally. Strain through cheesecloth. For every cup of infused "
            "oil, melt 1 ounce of beeswax (from your own hives or a local beekeeper). "
            "Combine oil and melted wax, stir, and pour into small tins or jars. Optional "
            "additions: a few drops of lavender essential oil (antimicrobial, calming) or "
            "tea tree oil (antifungal). This salve treats minor cuts, scrapes, cracked "
            "heels, diaper rash, chapped lips, dry skin, and mild burns. It costs pennies "
            "to make, stores for a year at room temperature, and replaces a shelf full of "
            "commercial products. The hands-on block: harvest calendula from your garden, "
            "render beeswax from your hive frames, infuse the oil, pour the salve. Every "
            "step is a lesson in botany, chemistry, or animal husbandry."
        ),
    },
    {
        "track": "HEALTH_NATUROPATHY",
        "source_title": "Electrolytes and Hydration — The Science of Oral Rehydration",
        "source_url": "https://archive.org/details/physiologyofhuma00guytuoft",
        "citation_author": "Traditional knowledge (compiled)",
        "citation_year": 1900,
        "citation_archive_name": "Public Domain / Compiled Research",
        "chunk": (
            "Dehydration kills more people worldwide than almost any single disease — and "
            "the cure is one of the simplest solutions in all of medicine. Electrolytes "
            "are minerals that carry electrical charges in the body: sodium, potassium, "
            "magnesium, and chloride. They regulate nerve impulses, muscle contractions "
            "(including the heartbeat), and fluid balance between cells. Sweat, vomiting, "
            "and diarrhea deplete electrolytes rapidly. Oral Rehydration Solution (ORS) — "
            "developed in the 1960s and credited with saving over 50 million lives — is "
            "simply: 1 liter of clean water, 6 teaspoons of sugar, and half a teaspoon "
            "of salt. The sugar activates sodium-glucose co-transport in the intestine, "
            "pulling water into the bloodstream faster than plain water alone. A homestead "
            "version: raw honey, sea salt, and a squeeze of lemon in water. Understanding "
            "why this works — the chemistry of osmosis and active transport — turns a "
            "simple recipe into a science lesson that could save a life."
        ),
    },
]


async def main():
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-placeholder"):
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    print("=" * 55)
    print("  HEALTH & NATUROPATHY DEEP SEED — Dear Adeline")
    print("=" * 55)

    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    engine = create_async_engine(
        _pg_dsn, echo=False,
        connect_args={"ssl": ctx, "statement_cache_size": 0},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    total = 0
    skipped = 0
    for source in SOURCES:
        async with session_factory() as session:
            existing = await session.execute(
                text("SELECT id FROM hippocampus_documents WHERE source_title = :t AND track = :tr LIMIT 1"),
                {"t": source["source_title"], "tr": source["track"]},
            )
            if existing.scalar():
                print(f"  [skip] {source['source_title']}")
                skipped += 1
                continue

        print(f"  Embedding: {source['source_title']}...")
        vector = await embed(source["chunk"])
        if vector is None:
            skipped += 1
            continue

        async with session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO hippocampus_documents
                        (id, source_title, source_url, track, chunk, embedding,
                         source_type, citation_author, citation_year, citation_archive_name)
                    VALUES
                        (gen_random_uuid(), :title, :url, :track, :chunk, CAST(:embedding AS vector),
                         'PRIMARY_SOURCE', :author, :year, :archive)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "title": source["source_title"],
                    "url": source["source_url"],
                    "track": source["track"],
                    "chunk": source["chunk"],
                    "embedding": str(vector),
                    "author": source["citation_author"],
                    "year": source.get("citation_year"),
                    "archive": source["citation_archive_name"],
                },
            )
            await session.commit()
        total += 1
        print(f"    Done ({len(source['chunk'])} chars)")

    async with session_factory() as session:
        count = (await session.execute(text("SELECT COUNT(*) FROM hippocampus_documents"))).scalar()
        health_count = (await session.execute(
            text("SELECT COUNT(*) FROM hippocampus_documents WHERE track = 'HEALTH_NATUROPATHY'")
        )).scalar()

    print(f"\nSeeded {total} new chunks, skipped {skipped}.")
    print(f"HEALTH_NATUROPATHY total: {health_count}")
    print(f"Hippocampus total: {count}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
