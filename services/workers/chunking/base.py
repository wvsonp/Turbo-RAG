"""Shared chunker interface and helpers."""

from __future__ import annotations

import re
from typing import Protocol

SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


class Chunker(Protocol):
    name: str

    def chunk(
        self, text: str, *, chunk_size: int, chunk_overlap: int
    ) -> list[str]:
        ...


def split_sentences(text: str) -> list[str]:
    parts = SENTENCE_PATTERN.split(text.strip())
    return [part.strip() for part in parts if part.strip()]


def pack_units(
    units: list[str],
    *,
    chunk_size: int,
    chunk_overlap: int,
    separator: str = " ",
) -> list[str]:
    """Merge small units into chunks respecting size and overlap."""
    if not units:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        piece = separator.join(current).strip()
        if piece:
            chunks.append(piece)
        if chunk_overlap <= 0:
            current = []
            current_len = 0
            return
        overlap_units: list[str] = []
        overlap_len = 0
        for unit in reversed(current):
            unit_len = len(unit) + (len(separator) if overlap_units else 0)
            if overlap_len + unit_len > chunk_overlap and overlap_units:
                break
            overlap_units.insert(0, unit)
            overlap_len += unit_len
        current = overlap_units
        current_len = sum(len(unit) for unit in current) + max(
            0, len(current) - 1
        ) * len(separator)

    for unit in units:
        unit_len = len(unit) + (len(separator) if current else 0)
        if current and current_len + unit_len > chunk_size:
            flush()
            unit_len = len(unit)
        current.append(unit)
        current_len += unit_len

    flush()
    return chunks
