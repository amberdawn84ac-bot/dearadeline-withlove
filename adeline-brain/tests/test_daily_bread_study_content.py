from unittest.mock import AsyncMock

import pytest

from app.api import daily_bread as api

GUIDANCE = 'Compare named translations with the source wording. Record only documented variants or changes; label disputed claims and unknown motives honestly.'


def arguments(**changes):
    return dict(reference='Psalms 19:2', fox_text='The heavens declare the glory of God.',
                hebrew_text='הַשָּׁמַיִם מְסַפְּרִים כְּבוֹד־אֵל', original='El',
                original_meaning='God', context='A psalm about creation and instruction.',
                grade_level='8', source_version='Supplied published version') | changes


@pytest.mark.asyncio
@pytest.mark.parametrize('missing', ['key', 'source', 'failure'])
async def test_unavailable_study_has_no_instruction_fallback(monkeypatch, missing):
    monkeypatch.setattr(api, 'GEMINI_API_KEY', '' if missing == 'key' else 'test-key')
    monkeypatch.setattr(api, 'GOOGLE_API_KEY', '')
    generate = AsyncMock(side_effect=RuntimeError('provider unavailable'))
    monkeypatch.setattr(api, '_gemini_json', generate)
    result = await api._build_deep_dive_study(**arguments(hebrew_text=None if missing == 'source' else arguments()['hebrew_text']))
    assert result == (None, [])
    assert generate.await_count == (1 if missing == 'failure' else 0)


@pytest.mark.asyncio
async def test_finished_comparison_survives_and_prompt_copy_is_removed(monkeypatch):
    monkeypatch.setattr(api, 'GEMINI_API_KEY', 'test-key')
    monkeypatch.setattr(api, 'GOOGLE_API_KEY', '')
    comparison = 'The Hebrew uses El; the supplied English version renders that word as God. That is a translation choice, not evidence of a manuscript alteration.'
    generate = AsyncMock(return_value={'direct_translation': 'The heavens recount the glory of El.', 'sections': [
        {'heading': 'Translation and Textual History', 'content': comparison},
        {'heading': 'Translation and Textual History', 'content': GUIDANCE},
        {'heading': 'The Key Word', 'content': 'Explain the original Hebrew or Greek word in depth — its root, its physical image, how it was used in everyday ancient life.'},
        {'heading': 'Context', 'content': '  '},
    ]})
    monkeypatch.setattr(api, '_gemini_json', generate)
    rendering, sections = await api._build_deep_dive_study(**arguments())
    assert rendering.endswith('El.')
    assert [section.content for section in sections] == [comparison]
    assert 'Supplied published version' in generate.call_args.args[1]


@pytest.mark.asyncio
async def test_no_translation_comparison_without_supplied_english(monkeypatch):
    monkeypatch.setattr(api, 'GEMINI_API_KEY', 'test-key')
    monkeypatch.setattr(api, '_gemini_json', AsyncMock(return_value={'sections': [
        {'heading': 'Translation and Textual History', 'content': 'An unsupported comparison.'},
        {'heading': 'What the Source Text Says', 'content': 'The supplied Hebrew describes the heavens recounting glory.'},
    ]}))
    _, sections = await api._build_deep_dive_study(**arguments(fox_text=None))
    assert [section.heading for section in sections] == ['What the Source Text Says']
