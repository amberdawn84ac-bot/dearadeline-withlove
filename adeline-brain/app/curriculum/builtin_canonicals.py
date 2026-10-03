"""Repository canonicals served when the database has no approved copy.

Hand-authored lessons are not a second pipeline. CanonicalStore checks the
database first. This module only supplies investigations that already satisfy
the current family contract so a household can open them before background
authoring has stored a copy.
"""
from typing import Any
from copy import deepcopy
from app.curriculum.kitchen_case_file import _lessons

from app.curriculum.kitchen_case_file import TOPIC, TRACK, _slug, build_kitchen_case_canonical


_SLUG = _slug(TOPIC, TRACK)


def unit_experiences(topic: str, track: str) -> list[dict]:
    if topic == TOPIC and track == TRACK:
        return [{"canonical_topic": f"{TOPIC} / {lesson['title']}", "track":TRACK} for lesson in _lessons()]
    return [{"canonical_topic":topic,"track":track}]


def builtin_canonical(slug: str) -> dict[str, Any] | None:
    if slug == _SLUG:
        return build_kitchen_case_canonical()  # retain existing family records
    for lesson in _lessons():
        topic = f"{TOPIC} / {lesson['title']}"
        if _slug(topic,TRACK) == slug:
            return _kitchen_experience(topic,lesson,slug)
    return None


def _kitchen_experience(topic: str, lesson: dict, slug: str) -> dict:
    record = deepcopy(build_kitchen_case_canonical())
    original_contract = record['blocks'][0]['metadata']['canonical_contract']
    teaching = {b['block_id']:b for b in record['blocks']}
    original_ids = lesson['block_ids']
    # These three prompts are explicitly authored in the repository lesson.
    extras = []
    for stage in lesson['stages'][1:4]:
        block_id=f"kcf-{lesson['lesson_id']}-{stage['stage'].lower()}"
        extras.append(dict(block_id=block_id,block_type='TEXT',experience_stage='DISCOVERY',title=stage['stage'].title(),content=stage['prompt'],evidence=[],family_style=True,canonical_format_version=12,track=TRACK,family_roles=record['blocks'][0]['family_roles'],metadata={'parent_directed':True,'content_revision':record['content_revision']}))
    blocks=[teaching[original_ids[0]],*extras,teaching[original_ids[1]]]
    adapted_lesson=deepcopy(lesson)
    adapted_lesson['block_ids']=[b['block_id'] for b in blocks]
    for index,stage in enumerate(adapted_lesson['stages']):
        stage['block_ids']=[blocks[index]['block_id']]
    contract=deepcopy(original_contract)
    contract["curriculum_contract_version"]=2
    contract['unit_plan']['lessons']=[adapted_lesson]
    contract['unit_plan']['essential_concepts']=[c for c in contract['unit_plan']['essential_concepts'] if c['concept_id'] in lesson['concept_ids']]
    contract['experience_design']['flow']=[{'node_id':f"{lesson['lesson_id']}-{stage['stage'].lower()}",'label':stage['stage'].title(),'block_ids':stage['block_ids']} for stage in adapted_lesson['stages']]
    contract['mastery_evidence_map']=[m for m in contract.get('mastery_evidence_map') or [] if m.get('concept') in lesson['concept_ids']]
    for block in blocks:
        block['metadata'].pop('canonical_contract',None)
    blocks[0]['metadata']['canonical_contract']=contract
    record.update(contract_version=2,id=f"kcf-experience-{lesson['lesson_id']}",topic_slug=slug,topic=topic,title=lesson['title'],blocks=blocks,stages=adapted_lesson['stages'])
    return record
