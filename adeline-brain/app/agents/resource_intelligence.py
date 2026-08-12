"""Resource intelligence for mission-building agents.

Curates trustworthy external learning sources and enforces conservative reuse rules.
The agent never treats "free" as permission to copy. It recommends sources and
returns the safest allowed use mode for mission builders.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class ResourceSource:
    id: str
    title: str
    provider: str
    url: str
    kinds: tuple[str, ...]
    tracks: tuple[str, ...]
    keywords: tuple[str, ...]
    use_mode: str
    rights_note: str
    mission_use: str
    authority: str = "primary_or_institutional"


SOURCES: tuple[ResourceSource, ...] = (
    ResourceSource(
        id="loc-primary",
        title="Library of Congress Primary Source Sets",
        provider="Library of Congress",
        url="https://www.loc.gov/programs/teachers/classroom-materials/primary-source-sets/",
        kinds=("primary_sources", "history", "maps", "photographs"),
        tracks=("TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "GOVERNMENT_ECONOMICS", "ENGLISH_LITERATURE"),
        keywords=("history", "child labor", "immigration", "civil rights", "labor", "photograph", "newspaper", "map"),
        use_mode="CHECK_ITEM_RIGHTS",
        rights_note="Prefer Library of Congress Free to Use and Reuse sets; verify each item's rights statement before republishing.",
        mission_use="Evidence boards, competing accounts, historical photographs, maps, newspapers, and source analysis.",
    ),
    ResourceSource(
        id="loc-sanborn",
        title="Sanborn Fire Insurance Maps",
        provider="Library of Congress",
        url="https://www.loc.gov/collections/sanborn-maps/",
        kinds=("historical_maps", "primary_sources"),
        tracks=("TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "APPLIED_MATHEMATICS", "HOMESTEADING"),
        keywords=("town", "city", "map", "fire", "railroad", "factory", "land use", "neighborhood", "oklahoma"),
        use_mode="OPEN_REUSE_WITH_SOURCE_CHECK",
        rights_note="The Library describes the online Sanborn collection as public domain; retain source metadata and verify the specific item page.",
        mission_use="Compare towns across time, investigate industry and housing patterns, calculate scale and distance, or reconstruct a historical neighborhood.",
    ),
    ResourceSource(
        id="national-archives",
        title="National Archives Education / DocsTeach",
        provider="U.S. National Archives",
        url="https://www.archives.gov/education",
        kinds=("primary_sources", "government_records", "documents"),
        tracks=("TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "GOVERNMENT_ECONOMICS"),
        keywords=("government", "federal", "treaty", "law", "executive order", "court", "indian", "native", "civil rights", "war"),
        use_mode="CHECK_ITEM_RIGHTS",
        rights_note="Many federal records are public domain, but not every item in National Archives holdings is automatically unrestricted. Check item-level rights.",
        mission_use="Original government records, document analysis, timelines, hearings, policy investigations, and treaty work.",
    ),
    ResourceSource(
        id="smithsonian-open",
        title="Smithsonian Open Access",
        provider="Smithsonian Institution",
        url="https://www.si.edu/openaccess",
        kinds=("museum", "3d", "artifacts", "images", "datasets"),
        tracks=("TRUTH_HISTORY", "CREATION_SCIENCE", "ENGLISH_LITERATURE", "CREATIVE_ECONOMY"),
        keywords=("artifact", "museum", "3d", "history", "science", "art", "culture", "object"),
        use_mode="CC0_WHEN_MARKED",
        rights_note="Only treat assets carrying the CC0 designation as unrestricted Open Access assets. Preserve source information even when attribution is not legally required.",
        mission_use="Virtual exhibits, artifact investigation, 3D-object study, visual source analysis, and new educational artwork built around authentic objects.",
    ),
    ResourceSource(
        id="nasa-learning",
        title="NASA Learning Resources",
        provider="NASA",
        url="https://www.nasa.gov/learning-resources/",
        kinds=("science", "engineering", "datasets", "activities"),
        tracks=("CREATION_SCIENCE", "APPLIED_MATHEMATICS"),
        keywords=("space", "astronomy", "moon", "mars", "rocket", "physics", "engineering", "earth", "climate", "satellite"),
        use_mode="LINK_OR_CHECK_ASSET_RIGHTS",
        rights_note="NASA material is often reusable, but logos, third-party material, people, and some media have separate restrictions. Check the exact asset/use guidance.",
        mission_use="Engineering challenges, astronomy investigations, Earth observation, mission planning, measurements, and authentic datasets.",
    ),
    ResourceSource(
        id="census-sis",
        title="Statistics in Schools",
        provider="U.S. Census Bureau",
        url="https://www.census.gov/schools/",
        kinds=("datasets", "math", "geography", "economics"),
        tracks=("APPLIED_MATHEMATICS", "GOVERNMENT_ECONOMICS", "TRUTH_HISTORY"),
        keywords=("population", "income", "county", "state", "demographics", "statistics", "graph", "data", "economics"),
        use_mode="LINK_OR_PUBLIC_DATA",
        rights_note="Use official Census data with clear source attribution; check individual educational assets for any separate terms.",
        mission_use="Real graphs, demographic comparisons, budgeting, population change, economic investigations, and data-literacy missions.",
    ),
    ResourceSource(
        id="zooniverse",
        title="Zooniverse",
        provider="Zooniverse",
        url="https://www.zooniverse.org/",
        kinds=("citizen_science", "research"),
        tracks=("CREATION_SCIENCE", "TRUTH_HISTORY"),
        keywords=("citizen science", "research", "animals", "space", "archives", "classification", "ecology"),
        use_mode="LINK",
        rights_note="Send learners to the live project unless a specific project explicitly licenses its materials for reuse.",
        mission_use="Participate in real research, make classifications, keep a field journal, and compare student observations with project findings.",
    ),
    ResourceSource(
        id="project-gutenberg",
        title="Project Gutenberg",
        provider="Project Gutenberg",
        url="https://www.gutenberg.org/",
        kinds=("public_domain_books", "literature", "historical_books"),
        tracks=("ENGLISH_LITERATURE", "TRUTH_HISTORY", "HOMESTEADING", "HEALTH_NATUROPATHY"),
        keywords=("book", "literature", "classic", "gardening", "herbs", "botany", "history", "public domain"),
        use_mode="PUBLIC_DOMAIN_EDITION_ONLY",
        rights_note="Verify the exact U.S. edition is public domain. Reuse the underlying public-domain text, not Project Gutenberg trademarks or unrelated copyrighted material.",
        mission_use="In-app reading, Dear Adeline reillustrated editions, annotation, vocabulary support, historical comparison, and project hooks.",
    ),
    ResourceSource(
        id="makecode-arcade",
        title="MakeCode Arcade",
        provider="Microsoft MakeCode",
        url="https://arcade.makecode.com/",
        kinds=("coding", "game_creation"),
        tracks=("APPLIED_MATHEMATICS", "CREATIVE_ECONOMY"),
        keywords=("coding", "game", "programming", "variables", "loops", "functions", "pixel art"),
        use_mode="LINK",
        rights_note="Use the live creation tool; do not copy Microsoft branding, proprietary assets, or course material without verifying its license.",
        mission_use="Build and publish playable games, remix code, debug projects, and bring student-created work back into the portfolio.",
    ),
    ResourceSource(
        id="geogebra",
        title="GeoGebra",
        provider="GeoGebra",
        url="https://www.geogebra.org/",
        kinds=("math", "interactive"),
        tracks=("APPLIED_MATHEMATICS",),
        keywords=("geometry", "algebra", "graph", "function", "statistics", "probability", "measurement"),
        use_mode="LINK",
        rights_note="Link to the live tool by default. Commercial and redistribution rights differ from free educational use.",
        mission_use="Model geometry, graph real measurements, explore functions, test conjectures, and visualize data.",
    ),
    ResourceSource(
        id="baker-creek",
        title="Baker Creek / RareSeeds Articles",
        provider="Baker Creek Heirloom Seed Company",
        url="https://www.rareseeds.com/blog",
        kinds=("homesteading", "gardening", "seed_saving"),
        tracks=("HOMESTEADING", "CREATION_SCIENCE"),
        keywords=("seed", "heirloom", "garden", "tomato", "pollination", "plant breeding", "seed saving"),
        use_mode="LINK_ONLY",
        rights_note="Treat current articles as copyrighted unless explicit permission says otherwise. Link and cite; do not ingest or republish article text.",
        mission_use="Research portals for seed saving, varieties, crop history, open pollination, and garden planning.",
        authority="specialist_commercial_source",
    ),
    ResourceSource(
        id="mountain-rose",
        title="Mountain Rose Herbs Educational Resources",
        provider="Mountain Rose Herbs",
        url="https://mountainroseherbs.com/",
        kinds=("homesteading", "herbalism", "botany"),
        tracks=("HOMESTEADING", "HEALTH_NATUROPATHY", "CREATION_SCIENCE"),
        keywords=("herb", "herbal", "plant", "tea", "salve", "botany", "garden", "remedy"),
        use_mode="LINK_ONLY",
        rights_note="Treat current educational articles and recipes as copyrighted unless permission is granted. Link and cite rather than copying into Dear Adeline.",
        mission_use="Plant identification, historical herbal-use research, garden projects, preparation methods, and evidence-comparison missions.",
        authority="specialist_commercial_source",
    ),
)


class ResourceIntelligenceAgent:
    """Select a small, rights-aware source packet for a mission."""

    def select(self, topic: str, track: str, limit: int = 4) -> dict:
        words = {w.strip(".,:;!?()[]{}\"'").lower() for w in topic.split() if w.strip()}
        scored: list[tuple[int, ResourceSource]] = []
        for source in SOURCES:
            score = 0
            if track in source.tracks:
                score += 5
            for keyword in source.keywords:
                key_words = set(keyword.lower().split())
                if key_words and key_words.issubset(words):
                    score += 4
                elif words.intersection(key_words):
                    score += 1
            if score:
                scored.append((score, source))
        scored.sort(key=lambda pair: (-pair[0], pair[1].provider, pair[1].title))
        selected = [source for _, source in scored[:limit]]
        return {
            "topic": topic,
            "track": track,
            "sources": [asdict(source) for source in selected],
            "rules": [
                "Primary/open institutional sources outrank commercial explainers for factual claims.",
                "Free access is not permission to copy, ingest, remix, or redistribute.",
                "Mission builders must obey each source's use_mode and rights_note.",
                "Label fact, interpretation, claim, disputed point, and unknown separately when evidence warrants it.",
                "Never invent a source, quotation, record, dataset, or rights status.",
            ],
        }

    def all_sources(self) -> Iterable[ResourceSource]:
        return SOURCES


resource_intelligence = ResourceIntelligenceAgent()
