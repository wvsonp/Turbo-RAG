"""Document identity and Qdrant point ID conventions."""

from __future__ import annotations

import uuid

# Fixed namespace for deterministic Qdrant point IDs across runs.
NAMESPACE_DOCUMENT = uuid.UUID("a3f2c8e1-4b5d-4e6f-9a0b-1c2d3e4f5a6b")


def logical_uri(bucket: str, object_name: str) -> str:
    return f"gs://{bucket}/{object_name}"


def document_version_id(bucket: str, object_name: str, generation: str | int) -> str:
    return f"{bucket}/{object_name}#{generation}"


def chunk_point_id(
    bucket: str, object_name: str, generation: str | int, chunk_index: int
) -> str:
    key = f"{document_version_id(bucket, object_name, generation)}:{chunk_index}"
    return str(uuid.uuid5(NAMESPACE_DOCUMENT, key))
