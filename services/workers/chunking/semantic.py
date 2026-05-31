"""Semantic chunker — sentence boundaries with optional embedding breakpoints."""

from __future__ import annotations

import math
from collections.abc import Callable

from chunking.base import pack_units, split_sentences


class SemanticChunker:
    name = "semantic"

    def __init__(
        self,
        embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
        *,
        breakpoint_percentile: float = 25.0,
    ) -> None:
        self._embed_fn = embed_fn
        self._breakpoint_percentile = breakpoint_percentile

    def chunk(
        self, text: str, *, chunk_size: int, chunk_overlap: int
    ) -> list[str]:
        sentences = split_sentences(text)
        if not sentences:
            return []
        if self._embed_fn is None or len(sentences) == 1:
            return pack_units(
                sentences,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

        groups = self._group_by_embedding_breakpoints(sentences)
        return pack_units(
            groups,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def _group_by_embedding_breakpoints(self, sentences: list[str]) -> list[str]:
        vectors = self._embed_fn(sentences)
        if len(vectors) != len(sentences):
            raise ValueError("embed_fn returned unexpected vector count")

        distances: list[float] = []
        for left, right in zip(vectors, vectors[1:], strict=True):
            distances.append(_cosine_distance(left, right))

        if not distances:
            return sentences

        threshold = _percentile(distances, self._breakpoint_percentile)
        groups: list[str] = []
        current = sentences[0]
        for sentence, distance in zip(sentences[1:], distances, strict=True):
            if distance >= threshold:
                groups.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current.strip():
            groups.append(current.strip())
        return groups


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 1.0
    similarity = dot / (left_norm * right_norm)
    return 1.0 - similarity


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (percentile / 100.0) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight
