"""Evidence-backed skill state over the existing BKT/standards stores.

Legacy probabilities remain scheduling signals. They do not become fresh
proof of mastery merely because a planner reads them.
"""
import json
from app.config import get_db_conn


def select_skill_work(*, subject: str, next_skill: dict | None, opportunities: list[dict], foundations: list[dict] = ()) -> dict:
    """A fit requires an explicit skill identity, task and evidence; nouns do not align standards."""
    eligible = {o['skill_id']: o for o in opportunities if o.get('skill_id') and o.get('task') and o.get('evidence_requirement')}
    if subject in ('math','reading'):
        if not next_skill:
            return {'integrated':[], 'individual':[], 'foundations':[]}
        # The caller supplies the next sequential skill, never a convenient later one.
        if next_skill.get('sequence_state') == 'LOCKED':
            return {'integrated':[], 'individual':[], 'foundations':[], 'locked':next_skill['skill_id']}
        fit = eligible.get(next_skill['skill_id'])
        return {'integrated':[dict(next_skill, opportunity=fit)] if fit else [],
                'individual':[] if fit else [dict(next_skill, sequence_reason='Next ordered skill has no defensible unit fit')], 'foundations':[]}
    if subject == 'science':
        # Foundation order is supplied by the prerequisite graph, not authored by the LLM.
        return {'integrated':list(eligible.values()), 'individual':[], 'foundations':[
            dict(f, instruction='REVIEW' if f.get('status') in ('demonstrated','secure') else 'REINFORCE' if f.get('status') == 'developing' else 'TEACH')
            for f in foundations]}
    return {'integrated':list(eligible.values()), 'individual':[], 'foundations':[]}


async def get_curriculum_state(student_id: str) -> dict:
    conn = await get_db_conn()
    try:
        skills = await conn.fetch('SELECT * FROM "StudentSkillState" WHERE "studentId"=$1', student_id)
        standards = await conn.fetch('SELECT "standardId",proficiency,"evidenceCount","lastEvidenceAt" FROM "StandardMastery" WHERE "studentId"=$1', student_id)
        bkt = await conn.fetch('SELECT "conceptId",track,"masteryLevel","dueAt" FROM "SpacedRepetitionCard" WHERE "studentId"=$1', student_id)
        return {'bkt_scheduling_signals':[dict(r) for r in bkt], 'student_id':student_id, 'skills':[dict(r) for r in skills],
                'legacy_standards':[dict(r) for r in standards], 'mastery_requires_evaluated_evidence':True}
    finally:
        await conn.close()


async def evaluate_evidence(*, attempt_id: str, student_id: str, skill_id: str, evaluator_id: str, result: str, reasoning: str) -> dict:
    if result not in ('developing','demonstrated','secure') or not reasoning.strip():
        raise ValueError('Evaluation requires a valid result and review reasoning')
    conn = await get_db_conn()
    try:
        async with conn.transaction():
            attempt = await conn.fetchrow('SELECT * FROM "EvidenceAttempt" WHERE id=$1 AND "studentId"=$2', attempt_id,student_id)
            if not attempt:
                raise ValueError('Evidence does not belong to this learner')
            content = attempt['content']
            if isinstance(content,str): content=json.loads(content)
            if not content or not any(v for v in content.values()):
                raise ValueError('Empty evidence cannot demonstrate a skill')
            evaluation = await conn.fetchrow('''INSERT INTO "EvidenceEvaluation"("attemptId","evaluatorId","skillId",result,reasoning)
                VALUES ($1,$2,$3,$4,$5) ON CONFLICT ("attemptId","skillId") DO NOTHING RETURNING id''', attempt_id,evaluator_id,skill_id,result,reasoning)
            if not evaluation:
                previous = await conn.fetchrow('SELECT result,reasoning FROM "EvidenceEvaluation" WHERE "attemptId"=$1 AND "skillId"=$2',attempt_id,skill_id)
                if previous and (previous['result'] != result or previous['reasoning'] != reasoning):
                    raise ValueError('This evidence already has a different review; submit a revised attempt before changing the finding')
            if evaluation:
                await conn.execute('''INSERT INTO "StudentSkillState"("studentId","skillId",status,"lastEvidenceId","evidenceCount","lastDemonstratedAt")
                    VALUES ($1,$2,$3,$4,1,CASE WHEN $3 IN ('demonstrated','secure') THEN NOW() END)
                    ON CONFLICT ("studentId","skillId") DO UPDATE SET status=EXCLUDED.status,"lastEvidenceId"=EXCLUDED."lastEvidenceId",
                    "evidenceCount"="StudentSkillState"."evidenceCount"+1,
                    "lastDemonstratedAt"=COALESCE(EXCLUDED."lastDemonstratedAt","StudentSkillState"."lastDemonstratedAt")''',student_id,skill_id,result,attempt_id)
            return {'evaluated':True, 'new_evaluation':bool(evaluation)}
    finally:
        await conn.close()


async def record_demonstration(*, student_id: str, lesson_id: str, plan_item_id: str | None, sources: list[dict], proficiency: str, skills: list[str]) -> None:
    """Shared Space/journal writer: preserve evaluated work before updating skill state."""
    import hashlib
    if not sources:
        raise ValueError('Demonstrated learning requires preserved evidence')
    payload = {'sources':sources,'proficiency':proficiency}
    key = 'demonstration:' + hashlib.sha256(json.dumps([student_id,plan_item_id,lesson_id,payload],sort_keys=True,default=str).encode()).hexdigest()
    conn=await get_db_conn()
    try:
        row=await conn.fetchrow('SELECT "canonicalSlug","metadataJson" FROM "StudentExperience" WHERE "studentId"=$1 AND "planItemId"=$2',student_id,plan_item_id or lesson_id)
        metadata=(row['metadataJson'] if row else {}) or {}
        if isinstance(metadata,str): metadata=json.loads(metadata)
        slug=row['canonicalSlug'] if row else lesson_id
        attempt_id=await conn.fetchval('''INSERT INTO "EvidenceAttempt"("studentId","canonicalSlug","canonicalRevision","lessonId",kind,content,"submissionKey")
            VALUES ($1,$2,$3,$4,'observation',$5::jsonb,$6) ON CONFLICT ("studentId","submissionKey") DO NOTHING RETURNING id''',student_id,slug,metadata.get('canonical_revision',''),lesson_id,json.dumps(payload),key)
        if not attempt_id:
            attempt_id=await conn.fetchval('SELECT id FROM "EvidenceAttempt" WHERE "studentId"=$1 AND "submissionKey"=$2',student_id,key)
    finally:
        await conn.close()
    result = 'secure' if proficiency=='EXTENDING' else 'demonstrated' if proficiency=='UNDERSTANDING' else 'developing'
    for skill in dict.fromkeys(skills):
        await evaluate_evidence(attempt_id=attempt_id,student_id=student_id,skill_id=skill,evaluator_id='adeline-evidence-review',result=result,reasoning=f'Preserved reviewed demonstration: {proficiency}')


async def science_foundations(student_id: str, concept_ids: list[str]) -> list[dict]:
    """Walk real prerequisite edges, oldest foundations first; do not invent gaps."""
    if not concept_ids:
        return []
    conn=await get_db_conn()
    try:
        rows=await conn.fetch('''WITH RECURSIVE foundations AS (
          SELECT "prerequisiteId" AS id,1 AS depth,ARRAY["conceptId","prerequisiteId"]::text[] AS path
          FROM "CurriculumConceptPrerequisite" WHERE "conceptId"=ANY($1::text[])
          UNION ALL SELECT p."prerequisiteId",f.depth+1,f.path||p."prerequisiteId"
          FROM foundations f JOIN "CurriculumConceptPrerequisite" p ON p."conceptId"=f.id
          WHERE NOT p."prerequisiteId"=ANY(f.path) AND f.depth<50
        ) SELECT c.id,c.title,COALESCE(s.status,'missing') AS status,MAX(f.depth) AS depth
          FROM foundations f JOIN "CurriculumConcept" c ON c.id=f.id
          LEFT JOIN "StudentSkillState" s ON s."studentId"=$2 AND s."skillId"=c.id
          GROUP BY c.id,c.title,s.status ORDER BY MAX(f.depth) DESC,c.id''',concept_ids,student_id)
        return select_skill_work(subject='science',next_skill=None,opportunities=[],foundations=[{'skill_id':r['id'],'title':r['title'],'status':r['status']} for r in rows])['foundations']
    finally:
        await conn.close()
