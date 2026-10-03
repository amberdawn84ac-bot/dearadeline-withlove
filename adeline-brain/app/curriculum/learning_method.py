"""The semantic five-stage contract, separate from rendering block types."""
from copy import deepcopy

STAGES = ('READ', 'EXPLORE', 'WRITE', 'APPLY', 'EXPERIENCE')


def validate_learning_method(stages: list[dict], block_ids: set[str]) -> list[str]:
    errors = []
    if [s.get('stage') for s in stages] != list(STAGES):
        errors.append('Stages must be READ, EXPLORE, WRITE, APPLY, EXPERIENCE in that order')
        return errors
    for stage in stages:
        if not str(stage.get('prompt') or '').strip() and not stage.get('block_ids'):
            errors.append(f"{stage['stage']} needs authored teaching or a prompt")
        if not set(stage.get('block_ids') or []) <= block_ids:
            errors.append(f"{stage['stage']} references unknown blocks")
    if not stages[2].get('evidence_required'):
        errors.append('WRITE requires preserved notes')
    if not stages[4].get('activity') or not stages[4].get('evidence_required'):
        errors.append('EXPERIENCE requires an authored activity and evidence')
    return errors


def validate_real_world_contract(contract: dict | None, *, claims_service: bool = False) -> list[str]:
    if not contract:
        return ['Claimed service needs a real-world contract'] if claims_service else []
    return [f'Real-world contract requires {key}' for key in
            ('recipient','need','deliverable','delivery_method','success_signal','evidence_required')
            if not contract.get(key)]


def academic_projection(blocks: list[dict]) -> list[dict]:
    """Character state never enters this immutable academic projection."""
    fields = ('block_id','content','evidence','sources','shared_facts','measurements')
    return [{key: deepcopy(b.get(key)) for key in fields if key in b} for b in blocks]


def validate_character_integrity(canonical: list[dict], adapted: list[dict]) -> None:
    if academic_projection(canonical) != academic_projection(adapted):
        raise ValueError('Character personalization altered canonical academic content')
