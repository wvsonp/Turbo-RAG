"""Unit tests for reciprocal rank fusion."""

from rag_platform.rrf import reciprocal_rank_fusion


def test_rrf_prefers_items_in_both_lists():
    dense = ["a", "b", "c"]
    sparse = ["b", "a", "d"]
    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    scores = dict(fused)
    assert scores["a"] > scores["c"]
    assert scores["b"] > scores["c"]
    assert scores["a"] == scores["b"]


def test_rrf_respects_rank_order():
    fused = reciprocal_rank_fusion([["x", "y", "z"], []], k=60)
    assert [item for item, _ in fused] == ["x", "y", "z"]


def test_rrf_fixed_scores_with_k_60():
    fused = reciprocal_rank_fusion([["only"]], k=60)
    assert fused == [("only", 1.0 / 61)]
