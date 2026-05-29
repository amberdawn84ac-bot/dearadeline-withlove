"""
Collaborative Filter — recommends components based on what succeeded
for learners with similar mastery profiles.

Uses cosine similarity on 10-track mastery vectors to find k-nearest peers,
then computes a weighted average of their component success rates.

Pure computation — no DB calls. Caller fetches peer data from DB.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Canonical track order — must match adeline-core/src/types.ts Track enum
TRACKS = [
    "CREATION_SCIENCE",
    "HEALTH_NATUROPATHY",
    "HOMESTEADING",
    "GOVERNMENT_ECONOMICS",
    "JUSTICE_CHANGEMAKING",
    "DISCIPLESHIP",
    "TRUTH_HISTORY",
    "ENGLISH_LITERATURE",
    "APPLIED_MATHEMATICS",
    "CREATIVE_ECONOMY",
]


@dataclass
class PeerProfile:
    """A peer learner's anonymized mastery snapshot and their component success rates."""
    student_id: str
    mastery_vector: list[float]                # 10 floats, ordered by TRACKS above
    component_success_rates: dict[str, float]  # {component_id: 0.0 – 1.0}
    total_interactions: int = 0


@dataclass
class CollaborativeRecommendation:
    component_id: str
    score: float             # Similarity-weighted success rate across peers
    contributing_peers: int  # Number of similar peers that inform this score


def build_mastery_vector(mastery_map: dict[str, float]) -> list[float]:
    """Convert a {track: mastery} dict into a canonical 10-dim vector."""
    return [mastery_map.get(track, 0.0) for track in TRACKS]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    arr_a = np.array(a, dtype=float)
    arr_b = np.array(b, dtype=float)
    norm_a = float(np.linalg.norm(arr_a))
    norm_b = float(np.linalg.norm(arr_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))


def find_similar_peers(
    student_vector: list[float],
    peers: list[PeerProfile],
    top_k: int = 10,
    min_interactions: int = 5,
    min_similarity: float = 0.10,
) -> list[tuple[PeerProfile, float]]:
    """Return top-k peers sorted by cosine similarity, filtered by quality."""
    candidates: list[tuple[PeerProfile, float]] = []
    for peer in peers:
        if peer.total_interactions < min_interactions:
            continue
        sim = _cosine_similarity(student_vector, peer.mastery_vector)
        if sim >= min_similarity:
            candidates.append((peer, sim))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:top_k]


def recommend_from_peers(
    student_mastery_vector: list[float],
    peers: list[PeerProfile],
    top_k_peers: int = 10,
    top_n_components: int = 5,
) -> list[CollaborativeRecommendation]:
    """
    Weighted item–user collaborative filtering.

    For each component, the score is the similarity-weighted mean of peer
    success rates among the top-k nearest neighbors.
    """
    similar = find_similar_peers(student_mastery_vector, peers, top_k=top_k_peers)
    if not similar:
        return []

    weighted_sums: dict[str, float] = {}
    weight_totals: dict[str, float] = {}
    peer_counts:   dict[str, int]   = {}

    for peer, similarity in similar:
        for comp_id, success_rate in peer.component_success_rates.items():
            weighted_sums[comp_id]  = weighted_sums.get(comp_id, 0.0)  + similarity * success_rate
            weight_totals[comp_id]  = weight_totals.get(comp_id, 0.0)  + similarity
            peer_counts[comp_id]    = peer_counts.get(comp_id, 0)      + 1

    recommendations: list[CollaborativeRecommendation] = [
        CollaborativeRecommendation(
            component_id=comp_id,
            score=round(weighted_sums[comp_id] / weight_totals[comp_id], 3),
            contributing_peers=peer_counts[comp_id],
        )
        for comp_id, total_w in weight_totals.items()
        if total_w > 0
    ]

    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations[:top_n_components]
