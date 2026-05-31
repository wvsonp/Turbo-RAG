"""Chunker registry — config-driven selection for ingestion and experiments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chunking.fixed import FixedSizeChunker
from chunking.recursive import RecursiveChunker
from chunking.semantic import SemanticChunker

if TYPE_CHECKING:
    from rag_platform.config import IngestionConfig

ALL_CHUNKER_NAMES: tuple[str, ...] = ("fixed", "recursive", "semantic")

# Production default: fixed (matches 2.3 behavior). Run chunking-experiment-flow
# and compare MLflow metrics before switching to recursive or semantic.
DEFAULT_CHUNKER = "fixed"

_FIXED = FixedSizeChunker()
_RECURSIVE = RecursiveChunker()


def get_chunker(name: str, *, config: IngestionConfig | None = None) -> FixedSizeChunker | RecursiveChunker | SemanticChunker:
    normalized = (name or DEFAULT_CHUNKER).strip().lower()
    if normalized == "fixed":
        return _FIXED
    if normalized == "recursive":
        return _RECURSIVE
    if normalized == "semantic":
        embed_fn = None
        if config is not None:
            from embedding.vertex import VertexEmbedder

            embed_fn = VertexEmbedder(config).embed_batches
        return SemanticChunker(embed_fn=embed_fn)
    raise ValueError(
        f"Unknown chunker {name!r}; expected one of {', '.join(ALL_CHUNKER_NAMES)}"
    )
