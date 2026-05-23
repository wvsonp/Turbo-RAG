"""Chunking utilities — backward-compatible exports."""

from __future__ import annotations

from chunking.fixed import FixedSizeChunker
from chunking.registry import ALL_CHUNKER_NAMES, DEFAULT_CHUNKER, get_chunker

_fixed = FixedSizeChunker()


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Fixed-size chunking (legacy helper used by 2.3)."""
    return _fixed.chunk(
        text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )


__all__ = [
    "ALL_CHUNKER_NAMES",
    "DEFAULT_CHUNKER",
    "chunk_text",
    "get_chunker",
]
