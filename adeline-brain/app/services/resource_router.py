"""Rights-aware search across approved outside learning collections.

Adeline owns the teaching. These results supply evidence, manipulation, games,
creation tools, and practice. Provider failures are isolated and unknown rights
never become permission to import.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import quote_plus

import httpx


@dataclass(frozen=True)
class ResourceQuery:
    topic: str
    track: str
    grade_level: str = "8"
    objective: str = ""
    resource_types: tuple[str, ...] = ()
    interactive_preferred: bool = True
    commercial_context: bool = True
    limit: int = 5


@dataclass
class RoutedResource:
    id: str
    title: str
    provider: str
    resource_type: str
    source_url: str
    description: str
    use_mode: str = "LINK"
    embed_url: str | None = None
    editor_url: str | None = None
    thumbnail_url: str | None = None
    license: str = "UNKNOWN"
    attribution: str = ""
    commercial_use: str = "UNKNOWN"
    account_required: bool = False
    game_mode: str | None = None
    age_range: str = "All ages with family guidance"
    skills_practiced: list[str] = field(default_factory=list)
    estimated_minutes: int = 15
    discovery_prompt: str = "What do you notice before anyone explains it?"
    mastery_prompt: str = "What did you discover, and what evidence supports your answer?"
    portfolio_output: str = "Save an observation or creation that demonstrates what you learned."
    score: float = 0.0


def _terms(text: str) -> set[str]:
    return {word.strip(".,:;!?()[]{}\"'").lower() for word in text.split() if len(word) > 1}


def _score(item: RoutedResource, query: ResourceQuery) -> float:
    wanted = _terms(f"{query.topic} {query.objective}")
    found = _terms(f"{item.title} {item.description} {' '.join(item.skills_practiced)}")
    score = 55 * len(wanted & found) / max(1, len(wanted))
    if item.resource_type in query.resource_types:
        score += 25
    if query.interactive_preferred and item.resource_type in {"GAME", "GAME_BUILDER", "SIMULATION", "ARTIFACT_3D"}:
        score += 18
    if item.license in {"CC0", "PUBLIC_DOMAIN"}:
        score += 7
    return round(score, 2)


async def _loc(query: ResourceQuery, client: httpx.AsyncClient) -> list[RoutedResource]:
    if query.track not in {"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "GOVERNMENT_ECONOMICS", "ENGLISH_LITERATURE"}:
        return []
    response = await client.get("https://www.loc.gov/search/", params={"q": query.topic, "fo": "json", "c": 6})
    response.raise_for_status()
    output = []
    for row in response.json().get("results", []):
        url, title = row.get("id") or row.get("url"), row.get("title")
        if not url or not title:
            continue
        images = row.get("image_url") or []
        description = row.get("description") or "Original item from the Library of Congress."
        if isinstance(description, list):
            description = description[0] if description else ""
        output.append(RoutedResource(
            id=f"loc:{url}", title=title, provider="Library of Congress",
            resource_type="PRIMARY_SOURCE", source_url=url, description=str(description)[:600],
            thumbnail_url=images[0] if images else None, license="ITEM_LEVEL_RIGHTS",
            attribution="Library of Congress; retain the item title, collection, and permanent URL.",
            commercial_use="CHECK_ITEM", skills_practiced=["source analysis", "corroboration"],
            discovery_prompt="Examine the item before reading its description. What can you establish directly?",
            portfolio_output="Save an annotated observation with the permanent Library of Congress URL.",
        ))
    return output


async def _nasa(query: ResourceQuery, client: httpx.AsyncClient) -> list[RoutedResource]:
    if query.track not in {"CREATION_SCIENCE", "APPLIED_MATHEMATICS"}:
        return []
    response = await client.get("https://images-api.nasa.gov/search", params={"q": query.topic, "media_type": "image"})
    response.raise_for_status()
    output = []
    for row in response.json().get("collection", {}).get("items", [])[:6]:
        data, links = (row.get("data") or [{}])[0], row.get("links") or []
        nasa_id, title = data.get("nasa_id"), data.get("title")
        if not nasa_id or not title:
            continue
        output.append(RoutedResource(
            id=f"nasa:{nasa_id}", title=title, provider="NASA", resource_type="IMAGE",
            source_url=f"https://images.nasa.gov/details/{quote_plus(nasa_id)}",
            description=str(data.get("description", ""))[:600],
            thumbnail_url=links[0].get("href") if links else None,
            license="NASA_MEDIA_GUIDELINES", attribution=f"NASA — {data.get('center', 'NASA')}",
            commercial_use="CHECK_ASSET", skills_practiced=["observation", "scientific interpretation"],
            portfolio_output="Annotate what the image shows separately from what you infer.",
        ))
    return output


async def _smithsonian(query: ResourceQuery, client: httpx.AsyncClient) -> list[RoutedResource]:
    if query.track not in {"TRUTH_HISTORY", "CREATION_SCIENCE", "ENGLISH_LITERATURE", "CREATIVE_ECONOMY"}:
        return []
    key = os.getenv("SMITHSONIAN_API_KEY", "")
    if not key:
        return [RoutedResource(
            id="smithsonian:search", title=f"Examine a Smithsonian object about {query.topic}",
            provider="Smithsonian Institution", resource_type="ARTIFACT_3D",
            source_url=f"https://www.si.edu/search?edan_q={quote_plus(query.topic)}",
            description="Search museum objects, specimens, images, records, and selected manipulable 3D models.",
            license="ITEM_LEVEL_CC0", commercial_use="ONLY_WHEN_CC0",
            skills_practiced=["artifact analysis", "observation"],
            discovery_prompt="What do the object's materials, shape, wear, or construction reveal?",
            portfolio_output="Save an object study with the Smithsonian record and its rights statement.",
        )]
    response = await client.get("https://api.si.edu/openaccess/api/v1.0/search", params={"api_key": key, "q": query.topic, "rows": 6})
    response.raise_for_status()
    output = []
    for row in response.json().get("response", {}).get("rows", []):
        url = row.get("url")
        if not url:
            continue
        output.append(RoutedResource(
            id=f"smithsonian:{row.get('id', url)}", title=row.get("title", "Smithsonian object"),
            provider="Smithsonian Institution", resource_type="PRIMARY_SOURCE", source_url=url,
            description="Smithsonian collection object. Verify the item-level CC0 mark before importing media.",
            license="ITEM_LEVEL_CC0", commercial_use="ONLY_WHEN_CC0",
            skills_practiced=["artifact analysis", "observation"],
        ))
    return output


async def _inaturalist(query: ResourceQuery, client: httpx.AsyncClient) -> list[RoutedResource]:
    """Return nearby-capable, real biodiversity observations without OAuth."""
    if query.track not in {"CREATION_SCIENCE", "HOMESTEADING"}:
        return []
    response = await client.get(
        "https://api.inaturalist.org/v1/observations",
        params={"q": query.topic, "quality_grade": "research", "photos": "true", "per_page": 6, "order_by": "votes"},
    )
    response.raise_for_status()
    output = []
    for row in response.json().get("results", []):
        taxon = row.get("taxon") or {}
        photos = row.get("photos") or []
        observation_id = row.get("id")
        title = taxon.get("preferred_common_name") or taxon.get("name")
        if not observation_id or not title:
            continue
        output.append(RoutedResource(
            id=f"inaturalist:{observation_id}", title=f"Observe: {title}", provider="iNaturalist",
            resource_type="DATASET", source_url=f"https://www.inaturalist.org/observations/{observation_id}",
            description=f"Research-grade community observation of {taxon.get('name', title)}. Inspect location, date, photographs, identification history, and uncertainty.",
            thumbnail_url=(photos[0].get("url") if photos else None),
            license="ITEM_LEVEL_LICENSE", commercial_use="CHECK_PHOTO_AND_DATA_LICENSE",
            skills_practiced=["species identification", "field observation", "data quality"], estimated_minutes=20,
            discovery_prompt="Which visible features support this identification, and what could still be mistaken?",
            mastery_prompt="Explain the identification using observable traits rather than relying only on the label.",
            portfolio_output="Save a field-journal comparison or contribute a family observation under the provider's privacy rules.",
        ))
    return output


def _youtube_resources(query: ResourceQuery) -> list[RoutedResource]:
    """Approved-channel searches. YouTube remains link/embed-only content."""
    encoded = quote_plus(query.topic)
    channels: list[tuple[str, str, str, str]] = []
    if query.track in {"CREATION_SCIENCE", "HOMESTEADING", "APPLIED_MATHEMATICS"}:
        channels.extend([
            ("science-buddies", "Science Buddies", "Science.Buddies", "hands-on experiment"),
            ("royal-institution", "The Royal Institution", "TheRoyalInstitution", "science demonstration"),
            ("hhmi-biointeractive", "HHMI BioInteractive", "biointeractive", "biology investigation"),
        ])
    if query.track in {"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "GOVERNMENT_ECONOMICS", "ENGLISH_LITERATURE"}:
        channels.extend([
            ("voices-past", "Voices of the Past", "VoicesofthePast", "first-person historical account"),
            ("national-archives", "U.S. National Archives", "USNationalArchives", "archival film or record"),
            ("world-history", "World History Encyclopedia", "WorldHistoryEncyclopedia", "historical overview"),
            ("smithsonian-archives", "Smithsonian Institution Archives", "siarchives", "museum or archival account"),
        ])
    return [RoutedResource(
        id=f"youtube:{slug}", title=f"Find a {purpose} about {query.topic}", provider=name,
        resource_type="VIDEO", source_url=f"https://www.youtube.com/@{handle}/search?query={encoded}",
        description=f"Search only the approved {name} channel. Use the video as evidence, demonstration, or perspective—not as the lesson itself.",
        license="YOUTUBE_LINK_OR_OFFICIAL_EMBED", commercial_use="LINK_OR_OFFICIAL_EMBED_ONLY",
        skills_practiced=["media analysis", "evidence checking"], estimated_minutes=12,
        discovery_prompt="Before watching, write what evidence would distinguish a demonstration or original account from an unsupported claim.",
        mastery_prompt="Name one observation or quotation from the video, then verify it against the experiment result or original record.",
        portfolio_output="Save a claim-evidence-verification note with the video and original-source links.",
    ) for slug, name, handle, purpose in channels]


async def _curated(query: ResourceQuery, _client: httpx.AsyncClient) -> list[RoutedResource]:
    words = _terms(f"{query.topic} {query.objective}")
    output: list[RoutedResource] = []
    science = bool(words & _terms("physics chemistry energy circuit force waves matter atom molecule math algebra probability"))
    if query.track in {"CREATION_SCIENCE", "APPLIED_MATHEMATICS"} and science:
        output.append(RoutedResource(
            id="phet:search", title=f"Manipulate a PhET simulation about {query.topic}", provider="PhET",
            resource_type="SIMULATION",
            source_url=f"https://phet.colorado.edu/en/simulations/filter?q={quote_plus(query.topic)}",
            description="Change one variable, predict the result, test it, and explain the model.",
            use_mode="LINK" if query.commercial_context else "EMBED", license="CC BY-NC 4.0",
            attribution="PhET Interactive Simulations, University of Colorado Boulder",
            commercial_use="SEPARATE_LICENSE_REQUIRED", estimated_minutes=20,
            skills_practiced=["variable control", "experimental design", "model-based reasoning"],
            discovery_prompt="Change only one variable first. Predict what will happen before you run it.",
            portfolio_output="Save a prediction-results-explanation record naming the controlled variable.",
        ))
    wants_game = bool(words & _terms("game coding program build model simulate interactive arcade")) or bool(set(query.resource_types) & {"GAME", "GAME_BUILDER"})
    if wants_game or (query.interactive_preferred and query.track in {
        "APPLIED_MATHEMATICS", "CREATIVE_ECONOMY", "CREATION_SCIENCE",
        "TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "GOVERNMENT_ECONOMICS",
    }):
        output.append(RoutedResource(
            id="makecode:arcade", title=f"Build or remix a {query.topic} game", provider="Microsoft MakeCode",
            resource_type="GAME_BUILDER", source_url="https://arcade.makecode.com/", editor_url="https://arcade.makecode.com/",
            description="Create a real 2D game with Blocks, JavaScript, or Python and publish the playable result.",
            license="PLATFORM_TERMS", commercial_use="LINK_OR_EMBED_SHARED_PROJECT", game_mode="BUILD",
            age_range="9–18", estimated_minutes=45,
            skills_practiced=["algorithms", "variables", "conditionals", "debugging", "game design"],
            discovery_prompt="What game rule will model the lesson concept instead of merely decorating it?",
            mastery_prompt="Show the rule in your code that represents the concept and explain what changes when you alter it.",
            portfolio_output="Publish the playable project and save its share link with a design or debugging explanation.",
        ))
    if query.track in {"GOVERNMENT_ECONOMICS", "JUSTICE_CHANGEMAKING", "TRUTH_HISTORY"}:
        output.append(RoutedResource(
            id="icivics:games", title=f"Test a government system in an iCivics game", provider="iCivics",
            resource_type="GAME", source_url="https://www.icivics.org/games",
            description="Play the system, then compare the game's model with an actual law or primary historical source.",
            license="LINK_ONLY", commercial_use="LINK_ONLY", game_mode="PLAY", estimated_minutes=35,
            skills_practiced=["systems thinking", "civics", "decision-making"],
            portfolio_output="Save a model-versus-reality comparison citing one primary source.",
        ))
    if query.track in {"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING"}:
        output.append(RoutedResource(
            id="mission-us:games", title=f"Enter a historical decision story connected to {query.topic}",
            provider="Mission US", resource_type="GAME", source_url="https://www.mission-us.org/",
            description="Use historical role-play as a perspective exercise, then verify the game's model against primary sources.",
            license="LINK_ONLY", commercial_use="LINK_ONLY", game_mode="MISSION", estimated_minutes=45,
            skills_practiced=["historical perspective", "decision-making", "source comparison"],
            portfolio_output="Save a choice-and-consequence map and verify one claim with an original source.",
        ))
    if query.track == "CREATION_SCIENCE":
        output.append(RoutedResource(
            id="zooniverse:projects", title=f"Join a real research project related to {query.topic}",
            provider="Zooniverse", resource_type="GAME", source_url="https://www.zooniverse.org/projects",
            description="Classify real research images or records and document the evidence used for each decision.",
            license="PROJECT_LEVEL_TERMS", commercial_use="LINK_ONLY", game_mode="MISSION", estimated_minutes=25,
            skills_practiced=["classification", "observation", "citizen science"],
            portfolio_output="Save a field-journal page showing classifications, evidence, and uncertainty.",
        ))
    if query.track in {"APPLIED_MATHEMATICS", "CREATION_SCIENCE", "GOVERNMENT_ECONOMICS"}:
        output.append(RoutedResource(
            id="khan:practice", title=f"Practice {query.topic} after the investigation", provider="Khan Academy",
            resource_type="PRACTICE", source_url=f"https://www.khanacademy.org/search?page_search_query={quote_plus(query.topic)}",
            description="Use targeted practice after Adeline has taught and the family has investigated the concept.",
            license="LINK_ONLY", commercial_use="LINK_ONLY", estimated_minutes=15,
            skills_practiced=["retrieval practice", "worked examples"],
            discovery_prompt="Use this after the lesson: which problem reveals whether you understand the concept rather than remember a procedure?",
            portfolio_output="Practice supports mastery but is not portfolio evidence by itself.",
        ))
    if query.track == "ENGLISH_LITERATURE":
        output.append(RoutedResource(
            id="gutenberg:books", title=f"Find the original public-domain text for {query.topic}",
            provider="Project Gutenberg", resource_type="READING",
            source_url=f"https://www.gutenberg.org/ebooks/search/?query={quote_plus(query.topic)}",
            description="Read or search an original public-domain edition instead of relying only on a summary.",
            license="PUBLIC_DOMAIN_EDITION_ONLY", commercial_use="VERIFY_EDITION", estimated_minutes=25,
            skills_practiced=["close reading", "annotation", "textual evidence"],
            portfolio_output="Save an annotated passage and an original claim supported by the text.",
        ))
    if query.track in {"TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "GOVERNMENT_ECONOMICS"}:
        output.extend([
            RoutedResource(
                id="docsteach:primary", title=f"Analyze National Archives documents about {query.topic}",
                provider="National Archives DocsTeach", resource_type="PRIMARY_SOURCE",
                source_url="https://docsteach.org/primary-sources/",
                description="Explore letters, photographs, speeches, posters, maps, films, and document-analysis activities.",
                license="MIXED_ITEM_LEVEL; ACTIVITIES_CC0", commercial_use="CHECK_PRIMARY_SOURCE_ITEM",
                skills_practiced=["document analysis", "sequencing", "corroboration"], estimated_minutes=25,
                discovery_prompt="What can the document establish directly, and what remains interpretation?",
                portfolio_output="Save a document-analysis sheet citing the National Archives identifier.",
            ),
            RoutedResource(
                id="dpla:search", title=f"Search American libraries and museums for {query.topic}",
                provider="Digital Public Library of America", resource_type="PRIMARY_SOURCE",
                source_url=f"https://dp.la/search?q={quote_plus(query.topic)}",
                description="Search aggregated photographs, documents, books, maps, and objects from American cultural institutions.",
                license="ITEM_LEVEL_RIGHTS", commercial_use="CHECK_ITEM",
                skills_practiced=["archive discovery", "provenance", "source comparison"], estimated_minutes=20,
                portfolio_output="Save a source dossier containing the owning institution and item-level rights statement.",
            ),
        ])
    if query.track in {"CREATION_SCIENCE", "APPLIED_MATHEMATICS"}:
        output.extend([
            RoutedResource(
                id="concord:models", title=f"Manipulate a Concord model related to {query.topic}",
                provider="Concord Consortium", resource_type="SIMULATION",
                source_url="https://learn.concord.org/", description="Explore scientifically grounded STEM models, simulations, datasets, and systems-building tools.",
                license="RESOURCE_LEVEL_TERMS", commercial_use="LINK; CHECK_ACTIVITY_LICENSE",
                skills_practiced=["systems modeling", "variable control", "prediction"], estimated_minutes=25,
                discovery_prompt="Which variables can you change, and what does the model assume or leave out?",
                portfolio_output="Save a model prediction, test result, and critique of one limitation.",
            ),
            RoutedResource(
                id="science-buddies:projects", title=f"Find a testable family experiment about {query.topic}",
                provider="Science Buddies", resource_type="EXPERIMENT",
                source_url=f"https://www.sciencebuddies.org/science-fair-projects/project-ideas/list?q={quote_plus(query.topic)}",
                description="Search step-by-step K–12 experiments with materials, procedures, safety guidance, and project scaffolding.",
                license="LINK_ONLY_UNLESS_MARKED", commercial_use="LINK_ONLY", skills_practiced=["experimental design", "measurement", "data analysis"], estimated_minutes=45,
                discovery_prompt="Identify the independent variable, dependent variable, controls, and safety needs before beginning.",
                portfolio_output="Save the family's procedure changes, raw observations, graph, and conclusion—not a copied worksheet.",
            ),
        ])
    if query.track == "CREATION_SCIENCE":
        output.extend([
            RoutedResource(
                id="hhmi:biointeractive", title=f"Investigate real biological data about {query.topic}",
                provider="HHMI BioInteractive", resource_type="SIMULATION",
                source_url=f"https://www.biointeractive.org/search?keywords={quote_plus(query.topic)}",
                description="Find virtual labs, interactives, films, case studies, and authentic biological datasets for secondary learners.",
                license="RESOURCE_LEVEL_CREATIVE_COMMONS_OR_LINK", commercial_use="CHECK_RESOURCE",
                skills_practiced=["data analysis", "biological modeling", "scientific argument"], estimated_minutes=30,
                portfolio_output="Save a data-backed claim and identify the limits of the dataset or model.",
            ),
            RoutedResource(
                id="bhl:search", title=f"Read historical biodiversity sources about {query.topic}",
                provider="Biodiversity Heritage Library", resource_type="READING",
                source_url=f"https://www.biodiversitylibrary.org/search?searchTerm={quote_plus(query.topic)}",
                description="Search digitized biological literature, field books, taxonomy, and scientific illustrations.",
                license="ITEM_LEVEL_RIGHTS", commercial_use="CHECK_ITEM",
                skills_practiced=["history of science", "taxonomy", "source comparison"], estimated_minutes=20,
                portfolio_output="Compare a historical description or illustration with a current observation or classification.",
            ),
        ])
    output.extend(_youtube_resources(query))
    return output


class ResourceRouter:
    rules = [
        "Adeline teaches; outside resources provide evidence, experience, simulation, creation, or practice.",
        "Free access is not permission to copy, ingest, remix, or redistribute.",
        "Unknown rights means link-only or blocked, never import.",
        "Never invent a source, quotation, record, embed permission, or rights status.",
    ]

    async def search(self, query: ResourceQuery) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6, connect=3), follow_redirects=True, headers={"User-Agent": "DearAdelineResourceRouter/1.0"}) as client:
            calls = [fn(query, client) for fn in (_loc, _smithsonian, _nasa, _inaturalist, _curated)]
            settled = await asyncio.gather(*calls, return_exceptions=True)
        resources: list[RoutedResource] = []
        failures = []
        for name, result in zip(("loc", "smithsonian", "nasa", "inaturalist", "curated"), settled):
            if isinstance(result, Exception):
                failures.append(name)
                continue
            resources.extend(result)
        for item in resources:
            if query.commercial_context and item.license == "CC BY-NC 4.0":
                item.use_mode = "LINK"
            item.score = _score(item, query)
        resources.sort(key=lambda item: (-item.score, item.provider, item.title))
        return {"query": asdict(query), "resources": [asdict(item) for item in resources[:query.limit]], "rules": self.rules, "provider_failures": failures}


resource_router = ResourceRouter()


async def resource_block_for_lesson(topic: str, track: str, grade_level: str) -> dict[str, Any] | None:
    from app.curriculum.family_style import CANONICAL_FORMAT_VERSION

    packet = await resource_router.search(ResourceQuery(topic=topic, track=track, grade_level=grade_level, limit=4))
    resources = packet["resources"]
    if not resources:
        return None
    return {
        "block_type": "RESOURCE_COLLECTION",
        "title": "Explore the real thing",
        "content": "Choose the outside resource that gives this family the strongest evidence, manipulation, game, or creation experience. Adeline remains the teacher; the resource is the laboratory or archive.",
        "metadata": {"resources": resources, "rights_rules": packet["rules"]},
        "evidence": [], "is_silenced": False, "family_style": True,
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
        "family_roles": {
            "elementary": "notice, manipulate, play, describe, or draw",
            "middle": "compare, test variables, explain systems, or modify",
            "high_school": "evaluate evidence, model, design, build, or critique limitations",
        },
    }
