"""
SearchWitnesses Tool — Adeline's Auto-Search Capability

Two-layer search for primary evidence:

Layer 1 (Hippocampus): Semantic search in verified corpus
  - Query all source types (PRIMARY_SOURCE, EDUCATIONAL, etc)
  - Return any result >= track-aware threshold (0.82 for history, 0.75 for science)

Layer 2 (Deep Web): Free DuckDuckGo search across primary source domains
  
  For HISTORY tracks (TRUTH_HISTORY, JUSTICE_CHANGEMAKING):
    - Government archives: NARA, CIA FOIA, FBI Vault, Congressional Record, Federal Register, DNSA
    - Primary source repositories: Library of Congress, Internet Archive, DPLA, Europeana
    - Academic collections: Avalon Project (Yale Law), Perseus (Tufts)
    → Returns PRIMARY_SOURCE documents (letters, diaries, speeches, court records, etc.)
  
  For SCIENCE tracks (CREATION_SCIENCE, HOMESTEADING, HEALTH_NATUROPATHY):
    - Educational domains: Khan Academy, Science Buddies, Exploratorium, Nature Education, Smithsonian
    → Returns EDUCATIONAL documents
  
  - Embed results and filter by track-aware threshold
  - Persist newly acquired documents to Hippocampus (self-improving)

Flow:
  1. Embed query
  2. Unified Hippocampus search (all source types)
  3. If results >= threshold: Return as VERIFIED
  4. If empty: Trigger parallel deep web search (track-appropriate domains)
  5. Embed found documents and filter by threshold
  6. Persist acquired docs to Hippocampus
  7. Return newly acquired docs
  8. If both empty: Return [] (triggers RESEARCH_MISSION)

Search backend: DuckDuckGo (100% free, no API key required).
"""
import asyncio
import os
import logging
from typing import Optional

import numpy as np
import openai

from app.schemas.api_models import (
    Evidence, EvidenceVerdict, WitnessCitation, TRUTH_THRESHOLD, SourceType,
)
from app.connections.pgvector_client import hippocampus
from app.protocols.witness import get_witness_threshold
from app.protocols.content_filter import should_return_document

logger = logging.getLogger(__name__)

# Semaphore to cap concurrent DuckDuckGo searches (rate-friendly)
_ddg_semaphore = asyncio.Semaphore(3)

EMBED_MODEL = "text-embedding-3-small"
DDG_MAX_RESULTS = 3  # Per-domain result cap

PRIMARY_SOURCE_DOMAINS = {
    # Government declassified archives
    'NARA': 'catalog.archives.gov',
    'CIA_FOIA': 'cia.gov/information-freedom',
    'FBI_VAULT': 'vault.fbi.gov',
    'CONGRESSIONAL_RECORD': 'congress.gov/congressional-record',
    'FEDERAL_REGISTER': 'federalregister.gov',
    'DNSA': 'nsarchive.gwu.edu',
    
    # Primary source repositories
    'LOC_DIGITAL': 'loc.gov/collections',  # Library of Congress digital collections
    'INTERNET_ARCHIVE': 'archive.org',  # Internet Archive - historical documents
    'DPLA': 'dp.la',  # Digital Public Library of America
    'EUROPEANA': 'europeana.eu',  # European cultural heritage
    'AVALON_PROJECT': 'avalon.law.yale.edu',  # Yale Law School - historical documents
    'PERSEUS': 'perseus.tufts.edu',  # Tufts - classical texts and primary sources
}

# Science-focused domains for CREATION_SCIENCE and HOMESTEADING tracks
SCIENCE_DOMAINS = {
    'KHAN_ACADEMY': 'khanacademy.org',
    'SCIENCE_BUDDIES': 'sciencebuddies.org',
    'EXPLORATORIUM': 'exploratorium.edu',
    'NATURE_EDUCATION': 'nature.com/scitable',
    'SMITHSONIAN': 'si.edu',
    'OPENSTAX_SCIENCE': 'openstax.org',
    'WE_ARE_TEACHERS': 'weareteachers.com',
    'STEVE_SPANGLER': 'stevespanglerscience.com',
    'PBS_LEARNING': 'pbslearningmedia.org',
    # Magic School Bus-style narrative science
    'WONDEROPOLIS': 'wonderopolis.org',            # "Wonder of the Day" — narrative science Q&A
    'NASA_SPACE_PLACE': 'spaceplace.nasa.gov',     # NASA's kid-friendly space + earth science
    'NAT_GEO_KIDS': 'kids.nationalgeographic.com', # Animals, ecosystems, earth science
    'SCIENCE_KIDS': 'sciencekids.co.nz',           # Fun facts + experiments by topic
    'DK_FIND_OUT': 'dkfindout.com',               # DK's encyclopedic kid science
    'EASY_SCIENCE': 'easyscienceforkids.com',      # Topic-by-topic narrative explanations
}

# Homesteading-specific domains — seeds, growing, land, food preservation
HOMESTEADING_DOMAINS = {
    'BAKER_CREEK_GROWING': 'rareseeds.com/blog/category/growing-guides',
    'BAKER_CREEK_STORIES': 'rareseeds.com/blog/category/seed-stories',
    'MOUNTAIN_ROSE_HERBS': 'mountainroseherbs.com/blog',  # Herb profiles, remedies, growing
    'EXTENSION_NCHFP': 'nchfp.uga.edu',        # National Center for Home Food Preservation
    'EXTENSION_USDA': 'nrcs.usda.gov',          # USDA soil/land conservation
    'MOTHER_EARTH_NEWS': 'motherearthnews.com',
    'ALMANAC': 'almanac.com',                    # Old Farmer's Almanac planting guides
}

# Math and applied skills domains
MATH_DOMAINS = {
    'OPENSTAX_MATH': 'openstax.org',
    'KHAN_MATH': 'khanacademy.org',
    'PURPLEMATH': 'purplemath.com',
    'MATH_IS_FUN': 'mathsisfun.com',
    'DESMOS': 'desmos.com',
}

# Literature, language, writing domains
LITERATURE_DOMAINS = {
    'GUTENBERG': 'gutenberg.org',
    'STANDARD_EBOOKS': 'standardebooks.org',
    'OPENSTAX_ELA': 'openstax.org',
    'POETS_ORG': 'poets.org',
    'LIBRARY_OF_CONGRESS': 'loc.gov',
}

# Economics, government, civics domains
CIVICS_DOMAINS = {
    'OPENSTAX_ECON': 'openstax.org',
    'KHAN_ECON': 'khanacademy.org',
    'FEDERAL_REGISTER': 'federalregister.gov',
    'CONGRESS': 'congress.gov',
    'USGOVERNMENT': 'usa.gov',
}

# Creative economy, entrepreneurship, making
CREATIVE_DOMAINS = {
    'KHAN_FINANCE': 'khanacademy.org',
    'SBA': 'sba.gov',
    'INSTRUCTABLES': 'instructables.com',
    'WIKIHOW': 'wikihow.com',
}

# Discipleship, worldview, scripture
DISCIPLESHIP_DOMAINS = {
    'SEFARIA': 'sefaria.org',
    'BIBLE_GATEWAY': 'biblegateway.com',
    'OPENBIBLE': 'openbible.info',
    'BLUELETTER': 'blueletterbible.org',
    'GOT_QUESTIONS': 'gotquestions.org',  # Scripture Q&A, theology, Christian worldview
}

# Tracks that should use science domains instead of declassified archives
SCIENCE_TRACKS = {'CREATION_SCIENCE', 'HOMESTEADING', 'HEALTH_NATUROPATHY'}

# Tracks that should use declassified archives (history/justice)
HISTORY_TRACKS = {'TRUTH_HISTORY', 'JUSTICE_CHANGEMAKING'}

# Domain map per track
TRACK_DOMAINS = {
    'TRUTH_HISTORY':        PRIMARY_SOURCE_DOMAINS,
    'JUSTICE_CHANGEMAKING': PRIMARY_SOURCE_DOMAINS,
    'CREATION_SCIENCE':     SCIENCE_DOMAINS,
    'HOMESTEADING':         HOMESTEADING_DOMAINS,
    'HEALTH_NATUROPATHY':   {**SCIENCE_DOMAINS, 'MOUNTAIN_ROSE_HERBS': 'mountainroseherbs.com/blog'},
    'APPLIED_MATHEMATICS':  MATH_DOMAINS,
    'ENGLISH_LITERATURE':   LITERATURE_DOMAINS,
    'GOVERNMENT_ECONOMICS': CIVICS_DOMAINS,
    'CREATIVE_ECONOMY':     CREATIVE_DOMAINS,
    'DISCIPLESHIP':         DISCIPLESHIP_DOMAINS,
}


# ── Cosine similarity helper ───────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


# ── OpenAI embedding helper ────────────────────────────────────────────────────

async def _embed(text: str) -> list[float]:
    """Embed text using text-embedding-3-small."""
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return resp.data[0].embedding


# ── Deep web search helpers ────────────────────────────────────────────────────

def _parse_ddg_results(raw: str, archive_name: str) -> list[dict]:
    """
    Parse DuckDuckGoSearchResults string output into structured dicts.

    DDG returns a string like:
      snippet: ..., title: ..., link: ..., date: ...\nsnippet: ...
    We parse each result into {title, url, archive, snippet}.
    """
    results = []
    # Each result block is separated by a blank line or starts with 'snippet:'
    import re
    # DuckDuckGoSearchResults returns a comma-separated string of result dicts repr
    # Try to parse as a Python literal first (langchain_community format)
    try:
        import ast
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            for item in parsed[:DDG_MAX_RESULTS]:
                if isinstance(item, dict):
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('link', item.get('url', '')),
                        'archive': archive_name,
                        'snippet': item.get('snippet', ''),
                    })
            return results
    except Exception:
        pass

    # Fallback: parse the flat string format
    # Format: [snippet: ..., title: ..., link: ...]
    for block in re.split(r'(?=\[snippet:)', raw):
        block = block.strip().strip('[]')
        if not block:
            continue
        title_m  = re.search(r'title:\s*([^,\]]+)', block)
        link_m   = re.search(r'link:\s*(https?://\S+)', block)
        snip_m   = re.search(r'snippet:\s*(.+?)(?=,\s*title:|,\s*link:|$)', block, re.DOTALL)
        results.append({
            'title':   title_m.group(1).strip()  if title_m  else '',
            'url':     link_m.group(1).strip()   if link_m   else '',
            'archive': archive_name,
            'snippet': snip_m.group(1).strip()   if snip_m   else block[:500],
        })
        if len(results) >= DDG_MAX_RESULTS:
            break
    return results


async def search_archive_async(query: str, archive_name: str, domains_map: dict = None) -> list[dict]:
    """
    Search a single archive/domain via DuckDuckGo (free, no API key).
    Returns list of documents with title, url, archive, snippet.
    """
    if domains_map is None:
        domains_map = PRIMARY_SOURCE_DOMAINS

    domain = domains_map.get(archive_name)
    if not domain:
        return []

    # Build a site-scoped query
    search_query = f'{query} site:{domain}'

    for attempt in range(3):
        try:
            from langchain_community.tools import DuckDuckGoSearchResults
            ddg = DuckDuckGoSearchResults(num_results=DDG_MAX_RESULTS, output_format="list")
            # Run synchronously in thread pool to avoid blocking the event loop
            raw = await asyncio.get_event_loop().run_in_executor(
                None, ddg.run, search_query
            )
            results = _parse_ddg_results(str(raw), archive_name)
            logger.info(f"[Researcher/DDG] {archive_name}: {len(results)} results for '{query[:60]}'")
            return results
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(
                f"[Researcher/DDG] Failed searching {archive_name} (attempt {attempt + 1}): {e} "
                f"— retrying in {wait}s"
            )
            await asyncio.sleep(wait)
    return []


async def search_with_fallback(query: str, track: str = None) -> tuple[list[dict], bool]:
    """
    Search archives with fallback detection.

    Returns (results, fallback_flag) where fallback_flag is True if all archives
    returned empty results (no matches found).
    """
    results = await search_all_archives_parallel(query, track)
    fallback = len(results) == 0
    if fallback:
        logger.warning(
            f"[Researcher] search_with_fallback returned empty for "
            f"query='{query}' track={track} — no matches found"
        )
    return results, fallback


async def search_all_archives_parallel(query: str, track: str = None) -> list[dict]:
    """
    Search archives in parallel based on track type.

    - TRUTH_HISTORY, JUSTICE_CHANGEMAKING: Search primary source repositories (government archives,
      Library of Congress, Internet Archive, university digital collections, etc.)
    - CREATION_SCIENCE, HOMESTEADING, HEALTH_NATUROPATHY: Search science education domains
    - Other tracks: Search science domains (more general content)

    Returns deduplicated list of documents across all searched domains.
    """
    # Choose domains based on track — each track has appropriate sources
    domains_map = TRACK_DOMAINS.get(track, SCIENCE_DOMAINS)
    logger.info(f"[Researcher] Using {len(domains_map)} domain(s) for track={track}")

    archives = list(domains_map.keys())

    async def _search_with_semaphore(archive: str) -> list[dict]:
        async with _ddg_semaphore:
            return await search_archive_async(query, archive, domains_map)

    tasks = [_search_with_semaphore(archive) for archive in archives]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Deduplicate by URL
    seen_urls = set()
    deduplicated = []
    for result_list in all_results:
        if isinstance(result_list, list):
            for result in result_list:
                if result['url'] not in seen_urls:
                    seen_urls.add(result['url'])
                    deduplicated.append(result)

    return deduplicated


# ── Main search_witnesses() API ────────────────────────────────────────────────

async def search_witnesses(
    query: str,
    track: str,
    top_k: int = 5,
    student_age: Optional[int] = None,
) -> list[dict]:
    """
    Search for evidence to answer a student question.

    Flow:
    1. Embed query
    2. Search Hippocampus (all source types at >= 0.82)
    3. If found: Filter by age appropriateness and return results
    4. If empty: Deep web search across 6 declassified archives
    5. Embed + persist found docs to Hippocampus
    6. Filter and return newly acquired docs
    7. If still empty: Return empty (triggers RESEARCH_MISSION)

    Args:
        query: Search query string
        track: Curriculum track (e.g., 'TRUTH_HISTORY', 'JUSTICE_CHANGEMAKING')
        top_k: Number of results to return (default: 5)
        student_age: Student's age in years. If provided, filters by content appropriateness.
                    If None, no age filtering is applied.

    Returns list of Evidence dicts with verdict, source_type, etc.
    """
    try:
        logger.info(f"[Researcher] Searching for witnesses — query='{query}' track={track}")
        
        logger.info("[Researcher] Deep web search via DuckDuckGo (free — no API key required)")

        # Step 1: Embed the query
        embedding_response = await _embed(query)
        query_embedding = embedding_response

        # Step 2: Unified Hippocampus search (all source types)
        hippo_results = await hippocampus.similarity_search(
            query_embedding=query_embedding,
            track=track,
            top_k=top_k,
        )

        # Step 3: Filter by track-aware threshold
        threshold = get_witness_threshold(track)
        logger.info(f"[Researcher] Using threshold {threshold} for track {track}")
        verified_results = [
            r for r in hippo_results
            if r.get('similarity_score', 0) >= threshold
        ]

        if verified_results:
            # Convert to Evidence format
            evidence_list = []
            for result in verified_results:
                evidence = {
                    'source_id': result['id'],
                    'source_title': result['source_title'],
                    'source_url': result['source_url'],
                    'source_type': result.get('source_type', 'PRIMARY_SOURCE'),
                    'witness_citation': {
                        'author': result.get('citation_author', ''),
                        'year': result.get('citation_year'),
                        'archive_name': result.get('citation_archive_name', ''),
                    },
                    'similarity_score': result['similarity_score'],
                    'verdict': 'VERIFIED',
                    'chunk': result['chunk'],
                }
                evidence_list.append(evidence)

            # Filter by student age
            filtered_evidence = [
                e for e in evidence_list
                if should_return_document(e, student_age=student_age)
            ]

            logger.debug(f"[Researcher] Filtered {len(evidence_list)} results to {len(filtered_evidence)} for age {student_age}")
            logger.info(f"[Researcher] Found {len(filtered_evidence)} verified in Hippocampus after age filtering")
            return filtered_evidence

        # Step 4: No verified results → deep web search
        # This triggers when Hippocampus is empty OR when results exist but are below threshold
        if hippo_results:
            best_score = max(r.get('similarity_score', 0) for r in hippo_results)
            logger.info(f"[Researcher] Hippocampus returned {len(hippo_results)} results (best score: {best_score:.3f}) but none met {threshold} threshold. Triggering deep web search.")
        else:
            logger.info(f"[Researcher] Hippocampus empty for track={track}. Triggering deep web search.")
        
        archive_results, fallback = await search_with_fallback(query, track=track)
        logger.info(f"[Researcher] Deep web search returned {len(archive_results)} raw results")

        if fallback:
            logger.warning(
                f"[Researcher/DDG] All archives returned empty — assigning RESEARCH_MISSION for "
                f"topic='{query}' track={track}"
            )

        if not archive_results:
            logger.info(f"[Researcher] No results from deep web search either. Student gets RESEARCH_MISSION.")
            return []

        # Step 5: Embed and score found documents
        acquired_evidence = []
        for doc in archive_results:
            try:
                # Embed the document snippet
                doc_embedding = await _embed(doc['snippet'][:8000])

                # Cosine similarity
                similarity_score = _cosine_similarity(query_embedding, doc_embedding)

                # Step 5b: Persist to Hippocampus if meets track threshold
                if similarity_score >= threshold:
                    # Use appropriate source type based on track
                    if track in HISTORY_TRACKS:
                        source_type = SourceType.PRIMARY_SOURCE.value
                    else:
                        source_type = "EDUCATIONAL"  # Science/education content
                    
                    doc_id = await hippocampus.upsert_document(
                        source_title=doc['title'],
                        track=track,
                        chunk=doc['snippet'],
                        embedding=doc_embedding,
                        source_url=doc['url'],
                        source_type=source_type,
                        citation_author='',
                        citation_year=None,
                        citation_archive_name=doc['archive'],
                    )

                    acquired_evidence.append({
                        'source_id': doc_id,
                        'source_title': doc['title'],
                        'source_url': doc['url'],
                        'source_type': source_type,
                        'witness_citation': {
                            'author': '',
                            'year': None,
                            'archive_name': doc['archive'],
                        },
                        'similarity_score': similarity_score,
                        'verdict': 'VERIFIED',
                        'chunk': doc['snippet'][:1000],
                    })

                    logger.info(f"[Researcher] Acquired document: {doc['title']} from {doc['archive']}")

            except Exception as e:
                logger.warning(f"[Researcher] Failed to process document {doc['title']}: {e}")
                continue

        if acquired_evidence:
            # Filter by student age
            filtered_acquired = [
                e for e in acquired_evidence
                if should_return_document(e, student_age=student_age)
            ]

            logger.debug(f"[Researcher] Filtered {len(acquired_evidence)} acquired results to {len(filtered_acquired)} for age {student_age}")
            logger.info(f"[Researcher] Acquired {len(filtered_acquired)} documents from deep web search after age filtering")
            return filtered_acquired

        # Step 7: Both empty → return empty
        logger.info(f"[Researcher] No results from any source. Student gets RESEARCH_MISSION.")
        return []

    except Exception as e:
        logger.error(f"[Researcher] Error in search_witnesses: {e}")
        return []
