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


@pytest.mark.asyncio
async def test_returning_to_today_selects_next_skill_without_regenerating_family_unit():
    from app.api.learning_plan import LearningPlanResponse, _advance_evaluated_targets
    from app.tools.graph_query import ZPDCandidate
    from tests.test_today_persistence import _saved_plan
    data = _saved_plan()
    data['progression_checklist'] = [target().model_dump()]
    plan = LearningPlanResponse(**data)
    candidate = ZPDCandidate(concept_id='ratio-2', title='Equivalent ratios', description='Compare equivalent ratios',
        track='APPLIED_MATHEMATICS', difficulty='', standard_code='', grade_band='6', dependent_count=0, prereq_count=1,
        prerequisite_ids=['ratio-1'])
    with patch('app.services.curriculum_state.get_curriculum_state', new=AsyncMock(return_value={'skills': [{'skillId': 'ratio-1', 'status': 'developing'}]})) as state, patch('app.api.learning_plan.tool_get_zpd_candidates', new=AsyncMock(return_value=[candidate])) as query:
        unchanged = await _advance_evaluated_targets(plan, '6')
        assert unchanged is plan
        query.assert_not_awaited()
        state.return_value = {'skills': [{'skillId': 'ratio-1', 'status': 'demonstrated'}]}
        updated = await _advance_evaluated_targets(plan, '6')
        assert updated.progression_checklist[0].concept_id == 'ratio-2'
        assert updated.suggestions[0] == plan.suggestions[0]
        assert updated.family_investigation == plan.family_investigation


def test_a_lower_subject_working_level_still_gets_its_next_step():
    lower = target().model_copy(update={'working_level': '3'})
    lesson = IndividualLesson(id='unit', investigation_id='unit', investigation_title='Plants',
        lesson_id='plants', index=1, count=1, title='Observe plants', assignment='Measure growth.', track='CREATION_SCIENCE')
    work = personalize_lessons([lesson], [lower], '8', {'CREATION_SCIENCE'})
    assert work[1].skill_target.working_level == '3'
    assert work[1].skill_target.concept_id == 'ratio-1'


@pytest.mark.asyncio
async def test_finished_lower_grade_prerequisite_resumes_placed_subject_path():
    from app.api.learning_plan import GradeLevelStandard, LearningPlanResponse, _advance_evaluated_targets
    from tests.test_today_persistence import _saved_plan
    data = _saved_plan()
    data['progression_checklist'] = [target().model_copy(update={
        'concept_id': None, 'standard_code': 'MATHEM_G5_5.N.1.3', 'working_level': '5',
    }).model_dump()]
    data['placement'] = {'declared_level': '8', 'working_grade': '8',
                         'placement_required': False, 'subject_levels': {'math': 6}}
    plan = LearningPlanResponse(**data)
    successor = GradeLevelStandard(standard_id='MATHEM_G6_6.N.3.1', subject='Mathematics',
        grade=6, description='Identify and use ratios.', mastered=False, priority=1,
        track='APPLIED_MATHEMATICS', prerequisites_met=True, progression_ready=True,
        prerequisite_standard_ids=['MATHEM_G5_5.N.1.3'])
    with patch('app.services.curriculum_state.get_curriculum_state', new=AsyncMock(return_value={
        'skills': [{'skillId': 'MATHEM_G5_5.N.1.3', 'status': 'demonstrated'}],
    })), patch('app.api.learning_plan._get_grade_level_standards', new=AsyncMock(return_value=[successor])) as query:
        updated = await _advance_evaluated_targets(plan, '8')
        query.assert_awaited_once_with(plan.student_id, '6')
        assert updated.progression_checklist[0].standard_code == successor.standard_id
        assert updated.progression_checklist[0].working_level == '6'
