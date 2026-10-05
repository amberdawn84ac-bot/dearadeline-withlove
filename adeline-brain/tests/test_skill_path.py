from copy import deepcopy
from unittest.mock import AsyncMock, patch
import pytest
from app.api.learning_plan import IndividualSkillTarget, IndividualLesson, personalize_lessons
from app.api.experience_builder import shared_family_canonical_slug
from app.schemas.api_models import LessonRequest, Track
from app.services.skill_path import bound_skill_tasks, mini_unit_errors, record_skill_response, skill_authoring_context


def target():
    return IndividualSkillTarget(suggestion_id='ratio-work', domain='math', title='Compare ratios',
        track='APPLIED_MATHEMATICS', concept_id='ratio-1', standard_code='MATH.6.R.1',
        working_level='6', sequence_state='READY', mastery_eligible=True, prerequisite_ids=['fraction-1'])


def contract():
    return {'blocks': [{'block_id': 'teach', 'content': 'A ratio compares quantities.'},
                       {'block_id': 'try', 'content': 'Independently compare these two mixtures.'}],
        'unit_plan': {'lessons': [{'lesson_id': 'mix', 'stages': [{'stage': 'READ', 'block_ids': ['teach']},
            {'stage': 'EXPERIENCE', 'block_ids': ['try']}]}]},
        'skill_opportunities': [{'skill_id': 'ratio-1', 'lesson_id': 'mix', 'block_ids': ['try'],
            'task': 'Compare the mixtures.', 'evidence_requirement': 'Correct ratio with an explanation.'}]}


def request(mode='INDIVIDUAL_SKILL'):
    return LessonRequest(student_id='learner', plan_item_id='ratio-work', topic='Compare ratios',
        track=Track.APPLIED_MATHEMATICS, grade_level='6', delivery_mode=mode,
        sequence_policy='HARD', sequence_state='READY', learner_progression_targets=[target().model_dump()])


@pytest.mark.parametrize('fits', [True, False])
@pytest.mark.asyncio
async def test_route_author_binding_and_independent_evidence(fits):
    unit = IndividualLesson(id='unit:mix', investigation_id='unit', investigation_title='Mixtures',
        lesson_id='mix', index=1, count=1, title='Mix and measure', assignment='Compare mixtures.',
        track='CREATION_SCIENCE', skill_opportunities=contract()['skill_opportunities'] if fits else [])
    lessons = personalize_lessons([unit], [target()], '6', {'CREATION_SCIENCE'})
    if fits:
        assert lessons[0].core_activities[0].suggestion_id == 'ratio-work'
        assert len(lessons) == 1
    else:
        assert lessons[1].skill_target.concept_id == 'ratio-1'
        assert lessons[1].skill_target.prerequisite_ids == ['fraction-1']
    req = request('FAMILY_INVESTIGATION' if fits else 'INDIVIDUAL_SKILL')
    assert 'ratio-1' in skill_authoring_context(req)
    assert not mini_unit_errors(req, contract())
    tasks = bound_skill_tasks(contract(), req.learner_progression_targets, contract()['blocks'])
    kwargs = dict(student_id='learner', plan_item_id='ratio-work', session_id='session',
        metadata={'skill_tasks': tasks}, completed=['try'], block_evaluations={'try': 'correct'},
        block_id='try', user_message='The ratios are 1:2 and 1:3, so the first mixture has more concentrate.')
    with patch('app.services.curriculum_state.record_demonstration', new_callable=AsyncMock) as write:
        await record_skill_response(**kwargs, evaluation='partial')
        write.assert_not_awaited()
        await record_skill_response(**kwargs, evaluation='correct')
        assert write.await_args.kwargs['skills'] == ['ratio-1']
        assert write.await_args.kwargs['sources'][0]['learner_response'] == kwargs['user_message']
        assert write.await_args.kwargs['proficiency'] == 'UNDERSTANDING'


def test_mini_unit_rejects_unbound_and_later_skills():
    data = contract()
    data['skill_opportunities'][0]['skill_id'] = 'ratio-2'
    assert mini_unit_errors(request(), data)
    data = contract()
    data['skill_opportunities'][0]['block_ids'] = ['not-authored']
    assert mini_unit_errors(request(), data)
    data = contract()
    data['skill_opportunities'][0]['lesson_id'] = 'other'
    assert mini_unit_errors(request(), data)
    locked = target().model_copy(update={'sequence_state': 'LOCKED'}).model_dump()
    assert not bound_skill_tasks(contract(), [locked], contract()['blocks'])


def test_mini_cache_identity_includes_exact_skill_and_level_not_child():
    first = request()
    second = first.model_copy(update={'student_id': 'sibling'})
    assert shared_family_canonical_slug(first) == shared_family_canonical_slug(second)
    changed = deepcopy(first.learner_progression_targets)
    changed[0]['concept_id'] = 'ratio-2'
    assert shared_family_canonical_slug(first) != shared_family_canonical_slug(first.model_copy(update={'learner_progression_targets': changed}))
    assert shared_family_canonical_slug(first) != shared_family_canonical_slug(first.model_copy(update={'grade_level': '8'}))


@pytest.mark.asyncio
async def test_stale_ready_request_cannot_unlock_prerequisite():
    from app.services.skill_path import ensure_skill_ready
    from fastapi import HTTPException
    with patch('app.connections.curriculum_graph.curriculum_graph.get_zpd_candidates', new_callable=AsyncMock) as candidates:
        candidates.return_value = []
        with pytest.raises(HTTPException) as blocked:
            await ensure_skill_ready(request())
        assert blocked.value.status_code == 409
        candidates.return_value = [{'concept_id': 'ratio-1'}]
        await ensure_skill_ready(request())


@pytest.mark.asyncio
async def test_only_the_independent_bound_block_can_record_evidence():
    tasks = bound_skill_tasks(contract(), [target().model_dump()], contract()['blocks'])
    with patch('app.services.curriculum_state.record_demonstration', new_callable=AsyncMock) as write:
        await record_skill_response(student_id='learner', plan_item_id='unit', session_id='session',
            metadata={'skill_tasks': tasks}, completed=['teach'], block_evaluations={'teach': 'correct'},
            block_id='teach', evaluation='correct', user_message='Yes, I understand.')
        write.assert_not_awaited()
