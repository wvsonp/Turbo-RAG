"""Recursive separator chunker (paragraph → line → sentence → word → char)."""

from __future__ import annotations

from chunking.base import pack_units

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class RecursiveChunker:
    name = "recursive"

    def __init__(self, separators: list[str] | None = None) -> None:
        self._separators = separators or DEFAULT_SEPARATORS

    def chunk(
        self, text: str, *, chunk_size: int, chunk_overlap: int
    ) -> list[str]:
        if not text.strip():
            return []
        units = self._split_recursive(text, self._separators)
        return pack_units(
            units,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=" ",
        )

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        if not separators:
            return [text]
        separator = separators[0]
        rest = separators[1:]
        if separator == "":
            return list(text)
        if separator not in text:
            return self._split_recursive(text, rest)
        parts = text.split(separator)
        units: list[str] = []
        for index, part in enumerate(parts):
            if not part:
                continue
            suffix = separator if index < len(parts) - 1 else ""
            candidate = f"{part}{suffix}"
            if len(candidate) <= 0:
                continue
            if len(candidate) > max(len(separator), 1) and rest:
                units.extend(self._split_recursive(candidate, rest))
            else:
                units.append(candidate.strip())
        return [unit for unit in units if unit.strip()]
