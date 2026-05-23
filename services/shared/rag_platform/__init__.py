"""Shared contracts and configuration for RAG platform services."""

from rag_platform.contracts import (
    NAMESPACE_DOCUMENT,
    chunk_point_id,
    document_version_id,
    logical_uri,
)
from rag_platform.config import IngestionConfig

__all__ = [
    "NAMESPACE_DOCUMENT",
    "IngestionConfig",
    "chunk_point_id",
    "document_version_id",
    "logical_uri",
]
