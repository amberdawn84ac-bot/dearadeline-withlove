"""Check exhaustive coverage and the meaningful source/runtime boundaries."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.curriculum.progression_import import load_progression_file, prerequisite_cycles
from app.curriculum.progression_placement import build_progression_placements
from app.services.curriculum_state import science_foundations

SEEDS = Path(__file__).resolve().parents[1] / 'data' / 'seeds'


def test_complete_catalog_and_all_published_source_objectives_are_accounted_for():
    catalog = json.loads((SEEDS / 'oas_to_8track.json').read_text())['mappings']
    review = json.loads((SEEDS / 'standard_progression_review.json').read_text())
    placements = build_progression_placements(catalog)
    ids = [(r.get('standard_node') or r.get('neo4j_node'))['properties']['id'] for r in catalog]
    assert len(ids) == len(set(ids))
    assert set(ids) == set(review['standards']) == set(placements)
    assert review['source_counts'] == {'social2026': 1025, 'health2026': 170, 'ela2021': 772, 'math2022': 649, 'science2026': 245}
    for subject, count in [('English Language Arts', 772), ('Mathematics', 649), ('Science', 245), ('Social Studies', 1025), ('Health', 170)]:
        current = [row for row in catalog if row['subject'] == subject and row.get('source_record') and not row.get('authored_subskill')]
        assert len(current) == count
        assert all(row['source_record']['page'] > 0 and len(row['source_record']['sha256']) == 64 for row in current)
    assert all(row['dependency_disposition'] for row in review['standards'].values())
    assert all(not placements[sid]['progression_is_terminal'] for sid, row in review['standards'].items() if row['review_status'] in {'LEGACY_OR_CONTAINER', 'SUPPORTING'})


def test_corrected_math_courses_keep_original_mastery_ids_and_prek_is_present():
    catalog = json.loads((SEEDS / 'oas_to_8track.json').read_text())['mappings']
    math = {row['standard_id']: row for row in catalog if row['subject'] == 'Mathematics'}
    for code, grade in [('PA.N.1.1', 8), ('A1.A.1.1', 9), ('G.2D.1.1', 10), ('A2.A.1.1', 10), ('PC.F.1.1', 11), ('S.DA.1.1', 11)]:
        assert math[code]['grade'] == grade
        assert math[code]['neo4j_node']['properties']['id'].startswith('MATHEM_G7_')
    assert math['PK.N.1.1']['grade'] == -1
    assert '3.GM.1.1' in math  # Printed code uses a space; reviewed normalization is explicit.


def test_sequential_subskills_are_real_dependencies_but_science_stays_flexible():
    edges = load_progression_file(SEEDS / 'verified_standard_progressions.json')
    assert prerequisite_cycles(edges) == []
    assert any(e.from_standard_id.endswith('1.2.PWS.2::step:1') and e.to_standard_id.endswith('1.2.PWS.2::step:2') and e.relation_type == 'PREREQUISITE_FOR' for e in edges)
    science = [e for e in edges if e.from_standard_id.startswith('SCIENC_')]
    assert len(science) == 369
    assert all(e.relation_type == 'FEEDS_INTO' for e in science)
    review = json.loads((SEEDS / 'standard_progression_review.json').read_text())
    assert all(r['disposition'] == 'REJECTED_SOURCE_REFERENCE' for r in review['unresolved_source_references'])


@pytest.mark.asyncio
async def test_science_standard_connections_reach_the_bridge_with_own_evidence_and_provenance():
    conn = AsyncMock()
    conn.fetch.side_effect = [[], [dict(id='source', title='Particle model', status='developing', relation_type='FEEDS_INTO', source_title='DCI progression', source_url='https://example.org/source', evidence_note='Published adjacent band')]]
    with patch('app.services.curriculum_state.get_db_conn', return_value=conn):
        result = await science_foundations('child', [], standard_ids=['target'])
    assert result[0]['instruction'] == 'REINFORCE'
    assert result[0]['hard_prerequisite'] is False
    assert result[0]['source_title'] == 'DCI progression'
    assert conn.fetch.call_args.args[1:] == (['target'], 'child')
    conn.close.assert_awaited_once()
