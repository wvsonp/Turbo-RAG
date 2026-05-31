"""Fixed-size character chunker."""

from __future__ import annotations


class FixedSizeChunker:
    name = "fixed"

    def chunk(
        self, text: str, *, chunk_size: int, chunk_overlap: int
    ) -> list[str]:
        if not text.strip():
            return []
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        chunks: list[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + chunk_size, length)
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= length:
                break
            start = end - chunk_overlap
        return chunks
