"""Document parsing for text and PDF uploads."""

from __future__ import annotations

import io
import logging

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def parse_bytes(
    data: bytes,
    *,
    object_name: str,
    max_bytes: int,
    max_pdf_pages: int,
) -> str:
    if len(data) > max_bytes:
        raise ValueError(
            f"Object exceeds max size ({len(data)} > {max_bytes} bytes)"
        )

    lower = object_name.lower()
    if lower.endswith(".pdf"):
        return _parse_pdf(data, max_pdf_pages)
    return data.decode("utf-8", errors="replace").strip()


def _parse_pdf(data: bytes, max_pdf_pages: int) -> str:
    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) > max_pdf_pages:
        raise ValueError(
            f"PDF exceeds max pages ({len(reader.pages)} > {max_pdf_pages})"
        )
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)
