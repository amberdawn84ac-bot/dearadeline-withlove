"""
Reinforcement Learning Optimizer — Q-learning for component sequencing.

Autonomously improves component recommendations over time by rewarding
choices that increase mastery, maintain engagement, and reduce frustration.

State space:  (zpd_zone, mastery_band, cognitive_load_level, learner_profile_type)
Action space: component_id strings from COMPONENT_REGISTRY
Q-table:      dict keyed by serialized (state, action) pairs

Pure computation — no DB/Redis calls. Caller loads and persists the Q-table.
"""
from __future__ import annotations

import json
import random
from typing import Optional

# ── Hyperparameters ────────────────────────────────────────────────────────────

ALPHA   = 0.10   # Learning rate
GAMMA   = 0.90   # Discount factor (long-term rewards matter)
EPSILON = 0.15   # Exploration rate (15% random — keeps discovering new combos)

# Reward weights
W_MASTERY     = 10.0
W_ENGAGEMENT  =  5.0
W_FRUSTRATION = -8.0   # Negative: frustration increase is penalized
W_COMPLETION  =  2.0
W_STRUGGLE    = -3.0


# ── State encoding ─────────────────────────────────────────────────────────────

def _mastery_band(mastery: float) -> str:
    if mastery < 0.30:
        return "LOW"
    if mastery < 0.70:
        return "MID"
    return "HIGH"


def encode_state(
    zpd_zone: str,
    mastery_score: float,
    cognitive_load_level: str,
    learner_profile_type: str,
) -> tuple[str, str, str, str]:
    """Encode learner state as a 4-tuple key for the Q-table."""
    return (zpd_zone, _mastery_band(mastery_score), cognitive_load_level, learner_profile_type)


# ── Q-table serialization (for Redis storage) ──────────────────────────────────

def _key(state: tuple, action: str) -> str:
    """Serialize (state, action) pair to a JSON-safe string key."""
    return json.dumps([list(state), action], separators=(",", ":"))


def serialize_q_table(q_table: dict) -> dict[str, float]:
    """Convert internal Q-table (tuple keys) to JSON-serializable dict."""
    return {_key(state, action): q_val for (state, action), q_val in q_table.items()}


def deserialize_q_table(raw: dict[str, float]) -> dict:
    """Restore Q-table from JSON-serializable dict."""
    result = {}
    for key_str, q_val in raw.items():
        parts = json.loads(key_str)
        state = tuple(parts[0])
        action = parts[1]
        result[(state, action)] = q_val
    return result


# ── Core Q-learning functions ──────────────────────────────────────────────────

def select_action(
    q_table: dict,
    state: tuple,
    available_actions: list[str],
    epsilon: float = EPSILON,
    seed: Optional[int] = None,
) -> str:
    """
    Epsilon-greedy action selection.
      - Probability ε  → explore: pick a random component
      - Probability 1-ε → exploit: pick the highest Q-value component
    """
    if not available_actions:
        raise ValueError("select_action requires at least one available action")

    rng = random.Random(seed)
    if rng.random() < epsilon:
        return rng.choice(available_actions)

    best_action = available_actions[0]
    best_q = q_table.get((state, best_action), 0.0)

    for action in available_actions[1:]:
        q = q_table.get((state, action), 0.0)
        if q > best_q:
            best_q = q
            best_action = action

    return best_action


def compute_reward(
    mastery_delta: float,
    engagement_delta: float,
    frustration_delta: float,
    lesson_completed: bool = True,
    struggled: bool = False,
) -> float:
    """
    Compute scalar reward from post-lesson outcome signals.

    mastery_delta:     change in mastery probability after lesson (-1 to +1)
    engagement_delta:  change in engagement level after lesson (-1 to +1)
    frustration_delta: change in frustration score after lesson (-1 to +1)
                       positive = more frustrated → penalized by W_FRUSTRATION
    """
    reward = (
        W_MASTERY     * mastery_delta
        + W_ENGAGEMENT  * engagement_delta
        + W_FRUSTRATION * frustration_delta
    )
    if lesson_completed:
        reward += W_COMPLETION
    if struggled:
        reward += W_STRUGGLE

    return round(reward, 4)


def q_update(
    q_table: dict,
    state: tuple,
    action: str,
    reward: float,
    next_state: tuple,
    available_next_actions: list[str],
    alpha: float = ALPHA,
    gamma: float = GAMMA,
) -> dict:
    """
    Bellman update:  Q(s,a) ← Q(s,a) + α · [r + γ · max_a' Q(s',a') − Q(s,a)]

    Returns a *new* Q-table dict; does not mutate the input.
    Caller is responsible for persisting the returned table to Redis.
    """
    current_q = q_table.get((state, action), 0.0)

    max_next_q = (
        max(q_table.get((next_state, a), 0.0) for a in available_next_actions)
        if available_next_actions
        else 0.0
    )

    new_q = current_q + alpha * (reward + gamma * max_next_q - current_q)
    updated = dict(q_table)
    updated[(state, action)] = round(new_q, 6)
    return updated


def get_q_values(
    q_table: dict,
    state: tuple,
    available_actions: list[str],
) -> dict[str, float]:
    """Return Q-values for all available actions in a state (for monitoring/debug)."""
    return {action: round(q_table.get((state, action), 0.0), 4) for action in available_actions}
