"""Reciprocal Rank Fusion for merging ranked retrieval lists."""

from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Merge ranked ID lists with RRF. Higher score is better."""
    scores: dict[str, float] = {}
    for ranking in ranked_lists:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
