"""Rights-aware search across approved outside learning collections.

Adeline owns the teaching. These results supply evidence, manipulation, games,
creation tools, and practice. Provider failures are isolated and unknown rights
never become permission to import.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
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
    source_item_id: str | None = None
    creator_or_issuer: str | None = None
    source_date: str | None = None
    holding_institution: str | None = None
    source_identifier: str | None = None
    evidence_scope: str | None = None
    rights_url: str | None = None
    availability: str = "COLLECTION_SEARCH"
    verified_at: str | None = None


def _terms(text: str) -> set[str]:
    return {word.strip(".,:;!?()[]{}\"'").lower() for word in text.split() if len(word) > 1}


def _grade_number(value: str) -> int:
    normalized = str(value).strip().upper()
    if normalized in {"K", "KINDERGARTEN", "K-2", "PLACEMENT"}:
        return 0
    try:
        return max(0, min(12, int(normalized)))
    except ValueError:
        return 8


def _score(item: RoutedResource, query: ResourceQuery) -> float:
    wanted = _terms(f"{query.topic} {query.objective}")
    found = _terms(f"{item.title} {item.description} {' '.join(item.skills_practiced)}")
    score = 55 * len(wanted & found) / max(1, len(wanted))
    if item.resource_type in query.resource_types:
        score += 25
    # A real item page outranks a generated archive-search link. This keeps the
    # records the author can actually inspect inside the bounded prompt even
    # when a search-page title happens to repeat every query word.
    if item.availability in {"VERIFIED_API_ITEM", "VERIFIED_ARCHIVE_ITEM"}:
        score += 50
    if query.interactive_preferred and item.resource_type in {
        "GAME", "GAME_BUILDER", "SIMULATION", "ARTIFACT_3D", "INTERACTIVE", "MANIPULATIVE",
    }:
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
            source_item_id=str(row.get("id") or url),
            rights_url=(row.get("rights") or [None])[0] if isinstance(row.get("rights"), list) else None,
            availability="VERIFIED_API_ITEM", verified_at=datetime.now(timezone.utc).isoformat(),
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
            source_item_id=nasa_id, availability="VERIFIED_API_ITEM",
            verified_at=datetime.now(timezone.utc).isoformat(),
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
            source_item_id=str(row.get("id") or url), availability="VERIFIED_API_ITEM",
            verified_at=datetime.now(timezone.utc).isoformat(),
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
            source_item_id=str(observation_id), availability="VERIFIED_API_ITEM",
            verified_at=datetime.now(timezone.utc).isoformat(),
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
    grade = _grade_number(query.grade_level)
    output: list[RoutedResource] = []
    if query.track == "APPLIED_MATHEMATICS":
        output.extend([
            RoutedResource(
                id="mathigon:polypad",
                title=f"Build and move a model of {query.topic}",
                provider="Mathigon / Amplify",
                resource_type="MANIPULATIVE",
                source_url="https://mathigon.org/polypad",
                description=(
                    "Use virtual fraction bars, algebra tiles, balance scales, number tools, geometry pieces, "
                    "dice, spinners, charts, and other manipulatives to make the relationship visible."
                ),
                license="PLATFORM_TERMS",
                commercial_use="LINK_ONLY",
                estimated_minutes=20,
                skills_practiced=["mathematical modeling", "conjecture", "visual reasoning"],
                discovery_prompt="Build the idea with objects before writing a rule. What changes when you move one piece or value?",
                mastery_prompt="Create and solve one fresh model, then explain how the objects prove the answer.",
                portfolio_output="Save the model beside the matching equation and your explanation.",
            ),
            RoutedResource(
                id="nrich:investigations",
                title=f"Find a strategy game or rich problem for {query.topic}",
                provider="University of Cambridge NRICH",
                resource_type="GAME",
                source_url="https://nrich.maths.org/home",
                description=(
                    "Choose a curriculum-linked game, puzzle, or investigation that makes the learner test "
                    "strategies and explain a pattern rather than repeat a worksheet procedure."
                ),
                license="LINK_ONLY",
                commercial_use="LINK_ONLY",
                estimated_minutes=25,
                skills_practiced=["problem solving", "strategy", "mathematical explanation"],
                discovery_prompt="Which moves or examples work, and what pattern explains them?",
                mastery_prompt="State the strategy as a rule and test it on a changed version of the problem.",
                portfolio_output="Save the strategy, one revision, and a successful test case.",
            ),
        ])
        if words & _terms("algebra equation function graph geometry angle transformation statistics probability calculus"):
            output.append(RoutedResource(
                id="geogebra:math",
                title=f"Model {query.topic} dynamically",
                provider="GeoGebra",
                resource_type="INTERACTIVE",
                source_url="https://www.geogebra.org/math",
                description="Use an interactive graph, construction, or data model to test how quantities and relationships change.",
                license="PLATFORM_TERMS",
                commercial_use="LINK_ONLY",
                estimated_minutes=20,
                skills_practiced=["graphing", "dynamic geometry", "mathematical modeling"],
                discovery_prompt="Change one value or construction at a time. What stays invariant?",
                mastery_prompt="Build a new graph, construction, or data model and explain the relationship it demonstrates.",
                portfolio_output="Save the model with a short explanation of the relationship you tested.",
            ))
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
    if grade >= 3 and (wants_game or (not query.resource_types and query.interactive_preferred and query.track in {
        "APPLIED_MATHEMATICS", "CREATIVE_ECONOMY", "CREATION_SCIENCE",
        "TRUTH_HISTORY", "JUSTICE_CHANGEMAKING", "GOVERNMENT_ECONOMICS",
    })):
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
    if wants_game and grade <= 2:
        output.append(RoutedResource(
            id="pbskids:games", title=f"Explore a playful {query.topic} challenge", provider="PBS KIDS",
            resource_type="GAME", source_url="https://pbskids.org/games/",
            description="Choose a short, age-appropriate game with a parent, then explain the rule, pattern, fact, or strategy you discovered.",
            license="LINK_ONLY", commercial_use="LINK_ONLY", game_mode="PLAY", age_range="5–8",
            skills_practiced=["patterns", "problem solving", "explanation"], estimated_minutes=15,
            mastery_prompt="Show or explain one rule, pattern, or idea you understand now that you did not notice at first.",
            portfolio_output="Save a drawing or spoken explanation of the strategy or concept—not a screenshot of time played.",
        ))
    if bool(words & _terms("code coding program programming makecode arcade")):
        output.append(RoutedResource(
            id="codeorg:learn", title=f"Learn coding through a {query.topic} puzzle", provider="Code.org",
            resource_type="GAME_BUILDER", source_url="https://studio.code.org/courses",
            description="Choose an age-appropriate coding course, solve a puzzle, then explain the sequence, loop, condition, or debugging decision you used.",
            license="PLATFORM_TERMS", commercial_use="LINK_ONLY", game_mode="BUILD",
            age_range="5–18", skills_practiced=["sequencing", "loops", "conditionals", "debugging"],
            mastery_prompt="Explain one piece of your program and why it behaves that way; if it failed, show how you debugged it.",
            portfolio_output="Save the project or course share link with a brief code explanation.",
        ))
    if query.track in {"GOVERNMENT_ECONOMICS", "JUSTICE_CHANGEMAKING", "TRUTH_HISTORY"}:
        output.append(RoutedResource(
            id="icivics:games", title="Test a government system in an iCivics game", provider="iCivics",
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


def _curated_archive_evidence(query: ResourceQuery) -> list[RoutedResource]:
    """Return verified item pages for a narrowly matched history investigation.

    These records are deliberately item-level, not archive search pages. They
    keep history authoring evidence-grounded when a live collection API is
    temporarily unreachable, while their evidence_scope prevents a political
    cartoon from being treated as proof of every claim drawn in it.
    """
    words = _terms(query.topic)
    robber_baron_topic = (
        query.track == "TRUTH_HISTORY"
        and bool(words & {"railroad", "railroads"})
        and bool(words & {"oil", "standard", "monopoly"})
    )
    if not robber_baron_topic:
        return []

    verified_at = datetime.now(timezone.utc).isoformat()
    shared = {
        "resource_type": "PRIMARY_SOURCE",
        "use_mode": "LINK",
        "skills_practiced": ["source analysis", "corroboration", "claim boundaries"],
        "availability": "VERIFIED_ARCHIVE_ITEM",
        "verified_at": verified_at,
    }
    return [
        RoutedResource(
            id="archives:pacific-railway-act-1862",
            title="Pacific Railway Act (1862)",
            provider="U.S. National Archives",
            source_url="https://www.archives.gov/milestone-documents/pacific-railway-act",
            description=(
                "Digitized enrolled federal law chartering the Union Pacific Railroad and granting "
                "rights-of-way, alternate public-land sections, and government bonds for construction."
            ),
            creator_or_issuer="United States Congress",
            source_date="1862-07-01",
            holding_institution="U.S. National Archives",
            source_identifier="12 Stat. 489; Record Group 11",
            source_item_id="12-stat-489",
            evidence_scope=(
                "Establishes what federal law authorized and subsidized. It does not by itself prove "
                "how every railroad used that power or how affected communities experienced it."
            ),
            license="PUBLIC_DOMAIN_US_GOVERNMENT",
            commercial_use="LINK_OR_PUBLIC_DOMAIN_TEXT",
            discovery_prompt="Mark every corporate power, public subsidy, condition, and reference to Indigenous land title in the act.",
            portfolio_output="Cite section numbers in a public-subsidy versus public-obligation evidence table.",
            **shared,
        ),
        RoutedResource(
            id="archives:interstate-commerce-act-1887",
            title="Interstate Commerce Act (1887)",
            provider="U.S. National Archives",
            source_url="https://www.archives.gov/milestone-documents/interstate-commerce-act",
            description=(
                "Digitized enrolled federal law making railroads the first U.S. industry subject to "
                "federal regulation and creating the Interstate Commerce Commission."
            ),
            creator_or_issuer="United States Congress",
            source_date="1887-02-04",
            holding_institution="U.S. National Archives",
            source_identifier="Public Law 49-41; Record Group 11",
            source_item_id="public-law-49-41",
            evidence_scope=(
                "Establishes the regulation Congress enacted. Compare its prohibitions and enforcement "
                "powers with other records before judging whether regulation worked."
            ),
            license="PUBLIC_DOMAIN_US_GOVERNMENT",
            commercial_use="LINK_OR_PUBLIC_DOMAIN_TEXT",
            discovery_prompt="Identify the railroad practices Congress prohibited and the enforcement power it actually created.",
            portfolio_output="Add a law-and-enforcement timeline card that distinguishes the rule on paper from evidence of implementation.",
            **shared,
        ),
        RoutedResource(
            id="loc:2001695241",
            title="Next!",
            provider="Library of Congress",
            source_url="https://www.loc.gov/pictures/item/2001695241/",
            description=(
                "Udo J. Keppler's 1904 Puck cartoon depicts Standard Oil as an octopus reaching into "
                "shipping, railroads, industry, government, and public institutions."
            ),
            creator_or_issuer="Udo J. Keppler; published by Puck",
            source_date="1904-09-07",
            holding_institution="Library of Congress Prints and Photographs Division",
            source_identifier="Library of Congress Control Number 2001695241",
            source_item_id="2001695241",
            evidence_scope=(
                "Primary evidence of a contemporary anti-monopoly argument and its visual rhetoric; "
                "the cartoon's accusations require corroboration with laws, testimony, and company records."
            ),
            license="ITEM_LEVEL_RIGHTS",
            commercial_use="CHECK_ITEM",
            discovery_prompt="Inventory every tentacle, label, scale choice, and institution before interpreting the cartoon's argument.",
            portfolio_output="Annotate the cartoon and test two depicted claims against documentary records.",
            **shared,
        ),
        RoutedResource(
            id="loc:2007675471",
            title="The Trust Giant's Point of View",
            provider="Library of Congress",
            source_url="https://www.loc.gov/pictures/item/2007675471/",
            description=(
                "A 1900 caricature portrays John D. Rockefeller holding the White House and President "
                "McKinley in his hand, with the Capitol and Treasury behind him."
            ),
            creator_or_issuer="Unknown cartoonist; contemporary caricature",
            source_date="1900",
            holding_institution="Library of Congress Prints and Photographs Division",
            source_identifier="Library of Congress Control Number 2007675471",
            source_item_id="2007675471",
            evidence_scope=(
                "Primary evidence of a contemporary claim about corporate influence over government; "
                "it is not proof of a specific corrupt transaction without corroborating records."
            ),
            license="ITEM_LEVEL_RIGHTS",
            commercial_use="CHECK_ITEM",
            discovery_prompt="Separate what the image literally shows from the political claim its symbols ask viewers to accept.",
            portfolio_output="Compare its power claim with the Pacific Railway and Interstate Commerce Acts and record agreements and limits.",
            **shared,
        ),
    ]


class ResourceRouter:
    rules = [
        "Adeline teaches; outside resources provide evidence, experience, simulation, creation, or practice.",
        "Free access is not permission to copy, ingest, remix, or redistribute.",
        "Unknown rights means link-only or blocked, never import.",
        "Never invent a source, quotation, record, embed permission, or rights status.",
    ]

    async def search(self, query: ResourceQuery) -> dict[str, Any]:
        cache_key = "resource-router:v5:" + hashlib.sha256(
            json.dumps(asdict(query), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        try:
            from app.connections.redis_client import redis_client
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

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
        resources.extend(_curated_archive_evidence(query))
        for item in resources:
            if query.commercial_context and item.license == "CC BY-NC 4.0":
                item.use_mode = "LINK"
            item.score = _score(item, query)
        resources.sort(key=lambda item: (
            item.availability not in {"VERIFIED_API_ITEM", "VERIFIED_ARCHIVE_ITEM"},
            -item.score,
            item.provider,
            item.title,
        ))
        packet = {"query": asdict(query), "resources": [asdict(item) for item in resources[:query.limit]], "rules": self.rules, "provider_failures": failures}
        try:
            from app.connections.redis_client import redis_client
            await redis_client.set(cache_key, json.dumps(packet), ex=3600)
        except Exception:
            pass
        return packet


resource_router = ResourceRouter()


def resource_block_from_packet(packet: dict[str, Any]) -> dict[str, Any] | None:
    from app.curriculum.family_style import CANONICAL_FORMAT_VERSION
    resources = packet.get("resources") or []
    if not resources:
        return None
    track = str(packet.get("track") or packet.get("query", {}).get("track") or "")
    is_math = track == "APPLIED_MATHEMATICS"
    return {
        "block_type": "RESOURCE_COLLECTION",
        "experience_stage": "RESOURCE",
        "title": "Play with the idea, then prove it" if is_math else "Explore the real thing",
        "content": (
            "Choose the game, puzzle, or manipulative matched to this exact math target. Try strategies, change the problem, and notice the pattern. Then solve or model one fresh case and explain why your strategy works; time played alone is never mastery."
            if is_math else
            "Choose the outside resource that gives this family the strongest evidence, manipulation, game, or creation experience. Adeline remains the teacher; the resource is the laboratory or archive."
        ),
        "metadata": {
            "resources": resources,
            "rights_rules": packet.get("rules") or [],
            "requires_evidence": is_math,
            "exact_target_required": is_math,
        },
        "evidence": [], "is_silenced": False, "family_style": True,
        "canonical_format_version": CANONICAL_FORMAT_VERSION,
        "family_roles": {
            "elementary": "notice, manipulate, play, describe, or draw",
            "middle": "compare, test variables, explain systems, or modify",
            "high_school": "evaluate evidence, model, design, build, or critique limitations",
        },
    }


async def resource_block_for_lesson(
    topic: str, track: str, grade_level: str, objective: str = "",
    resource_types: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    packet = await resource_router.search(ResourceQuery(
        topic=topic, track=track, grade_level=grade_level, objective=objective,
        resource_types=resource_types, limit=4,
    ))
    return resource_block_from_packet(packet)
