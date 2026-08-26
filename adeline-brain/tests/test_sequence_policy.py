from dataclasses import dataclass

from app.algorithms.sequence_policy import (
    SequencePolicy,
    SequenceState,
    build_sequence_contract,
    suggestion_is_assignable,
)


@dataclass
class PlannedMission:
    sequence_policy: str
    sequence_state: str
    concept_id: str | None = None
    sequence_target_id: str | None = None


def test_hard_concept_is_locked_below_prerequisite_threshold():
    contract = build_sequence_contract(
        source="zpd", concept_id="fractions", prerequisite_readiness=0.69
    )
    assert contract.policy is SequencePolicy.HARD
    assert contract.state is SequenceState.LOCKED
    assert contract.assignable is False


def test_hard_concept_is_ready_at_threshold():
    contract = build_sequence_contract(
        source="zpd", concept_id="fractions", prerequisite_readiness=0.70
    )
    assert contract.state is SequenceState.READY
    assert contract.assignable is True


def test_interest_and_standard_work_require_a_bridge_instead_of_claiming_readiness():
    for source in ("interest", "standard", "explore"):
        contract = build_sequence_contract(source=source)
        assert contract.policy is SequencePolicy.SUPPORTED
        assert contract.state is SequenceState.BRIDGE_REQUIRED
        assert contract.assignable is True
        assert contract.bridge_required is True


def test_family_history_and_science_topics_do_not_receive_a_generic_bridge():
    contract = build_sequence_contract(source="family")

    assert contract.policy is SequencePolicy.OPEN
    assert contract.state is SequenceState.OPEN
    assert contract.bridge_required is False


def test_final_gate_fails_closed_for_locked_or_unidentified_hard_work():
    assert suggestion_is_assignable(PlannedMission("HARD", "LOCKED", "fractions")) is False
    assert suggestion_is_assignable(PlannedMission("HARD", "READY", None)) is False
    assert suggestion_is_assignable(PlannedMission("HARD", "READY", "fractions")) is True


def test_supported_curiosity_remains_assignable():
    assert suggestion_is_assignable(PlannedMission("SUPPORTED", "BRIDGE_REQUIRED")) is True


def test_verified_standard_can_use_a_non_concept_sequence_target():
    mission = PlannedMission("HARD", "READY", sequence_target_id="OAS.MATH.4.1")
    assert suggestion_is_assignable(mission) is True
