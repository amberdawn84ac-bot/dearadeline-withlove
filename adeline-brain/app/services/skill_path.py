"""Keep exact progression targets bound to teaching and reviewed evidence."""
import hashlib
import json


def request_targets(request) -> list[dict]:
    targets = list(request.learner_progression_targets or request.individual_skill_targets)
    if request.delivery_mode == 'INDIVIDUAL_SKILL' and not targets:
        for code in request.required_standard_codes:
            targets.append({'standard_code': code, 'title': request.topic, 'sequence_state': request.sequence_state})
        if request.concept_id:
            targets.append({'concept_id': request.concept_id, 'title': request.concept_name or request.topic, 'sequence_state': request.sequence_state})
    return targets


def target_ids(target: dict) -> set[str]:
    return {str(target[k]) for k in ('concept_id', 'standard_code') if target.get(k)}


def skill_authoring_context(request) -> str:
    targets = request_targets(request)
    if not targets:
        return ''
    mode = 'SEPARATE MINI-UNIT' if request.delivery_mode == 'INDIVIDUAL_SKILL' else 'FAMILY UNIT FIT CHECK'
    return '\n\n' + mode + ':\n' + json.dumps(targets) + '''
These are exact current targets, not a menu of later skills. Never skip a target
for a convenient theme. Use only supplied concept/standard IDs. For a family
unit, include a skill_opportunity only when the actual work teaches and elicits
that skill; otherwise leave it out so the planner supplies a separate mini-unit.
For a separate mini-unit, teach this exact skill through a coherent progression:
check foundations, explain and model, guide practice, then obtain a fresh independent
demonstration. It may span sessions. Do not manufacture a family-theme connection.
Each included skill_opportunity must declare lesson_id and block_ids pointing to
the independent demonstration block(s), plus task and evidence_requirement.
A teaching block, guided answer, or completion checkbox is not that demonstration.
'''


def bound_skill_tasks(contract: dict, targets: list[dict], blocks: list[dict]) -> list[dict]:
    known = {b.get('block_id') for b in blocks}
    lessons = {lesson.get('lesson_id'): lesson for lesson in (contract.get('unit_plan') or {}).get('lessons', [])}
    tasks = []
    for opportunity in contract.get('skill_opportunities') or []:
        skill_id = str(opportunity.get('skill_id') or '')
        target = next((t for t in targets if skill_id in target_ids(t) and t.get('sequence_state') not in {'LOCKED', 'BRIDGE_REQUIRED'}), None)
        ids = opportunity.get('block_ids') or []
        lesson = lessons.get(opportunity.get('lesson_id'))
        lesson_blocks = {bid for stage in (lesson or {}).get('stages', []) for bid in stage.get('block_ids', [])}
        if target and lesson and ids and set(ids) <= known & lesson_blocks and opportunity.get('task') and opportunity.get('evidence_requirement'):
            tasks.append({**opportunity, 'target': target})
    return tasks


def mini_unit_errors(request, contract: dict) -> list[str]:
    if request.delivery_mode != 'INDIVIDUAL_SKILL':
        return []
    targets = request_targets(request)
    if not targets:
        return ['Separate mini-unit needs an exact concept or standard target from the learning plan']
    tasks = bound_skill_tasks(contract, targets, contract.get('blocks') or [])
    if any(not any(task['skill_id'] in target_ids(t) for task in tasks) for t in targets):
        return ['Mini-unit must teach every exact target and bind its independent demonstration to real lesson_id and block_ids']
    return []


def mini_unit_key(request) -> str:
    return hashlib.sha256(json.dumps([request_targets(request), request.grade_level], sort_keys=True).encode()).hexdigest()[:16]


async def record_skill_response(*, student_id, plan_item_id, session_id, metadata, completed, block_evaluations, block_id, evaluation, user_message):
    if evaluation != 'correct' or not user_message.strip():
        return
    from app.services.curriculum_state import record_demonstration
    from app.connections.curriculum_graph import curriculum_graph
    for task in metadata.get('skill_tasks') or []:
        ids = task['block_ids']
        if block_id not in ids or not all(i in completed and block_evaluations.get(i) == 'correct' for i in ids):
            continue
        target = task['target']
        await record_demonstration(
            student_id=student_id, lesson_id=task['lesson_id'], plan_item_id=plan_item_id,
            sources=[{'type': 'skill_demonstration', 'session_id': session_id, 'block_ids': ids,
                      'skill_id': task['skill_id'], 'learner_response': user_message,
                      'evidence_requirement': task['evidence_requirement']}],
            proficiency='UNDERSTANDING', skills=[task['skill_id']],
        )
        if task['skill_id'] == target.get('standard_code'):
            await curriculum_graph.record_standard_mastery(student_id, target.get('track') or metadata.get('track') or '',
                [{'standard_id': task['skill_id'], 'text': target.get('title') or '', 'grade': int(target.get('working_level') or 0) if str(target.get('working_level') or '').isdigit() else 0}], proficiency='UNDERSTANDING')


async def ensure_skill_ready(request):
    """A stale or edited browser request cannot unlock a prerequisite."""
    from fastapi import HTTPException
    from app.connections.curriculum_graph import curriculum_graph
    targets = request_targets(request)
    if not targets or any(not target_ids(t) for t in targets):
        raise HTTPException(status_code=409, detail="Refresh the learning plan to open the exact next skill.")
    if any(t.get('sequence_state') != 'READY' for t in targets):
        raise HTTPException(status_code=409, detail="This skill needs its foundations first.")
    concepts = {t['concept_id'] for t in targets if t.get('concept_id')}
    if concepts:
        eligible = await curriculum_graph.get_zpd_candidates(request.student_id, request.track.value, limit=1000)
        if not concepts <= {row['concept_id'] for row in eligible}:
            raise HTTPException(status_code=409, detail="Refresh your plan; this skill is completed or needs a prerequisite.")
    standards = {t['standard_code'] for t in targets if t.get('standard_code') and not t.get('concept_id')}
    if standards:
        grade = 0 if request.grade_level == 'K' else int(request.grade_level)
        rows = await curriculum_graph.get_grade_standards(request.student_id, grade, limit=1000, per_subject_limit=None)
        eligible = {r['id'] for r in rows if not r['mastered'] and r['prerequisites_met'] and r['progression_ready']}
        if not standards <= eligible:
            raise HTTPException(status_code=409, detail="Refresh your plan; this skill is completed or needs a prerequisite.")
