"""Qdrant collection management and point upserts."""

from __future__ import annotations

import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from rag_platform.config import IngestionConfig
from rag_platform.contracts import document_version_id, logical_uri
from rag_platform.retry import with_retry_sync
from rag_platform.sparse import FastEmbedSparseEncoder, SparseEncoderConfig

logger = logging.getLogger(__name__)


class QdrantStore:
    def __init__(self, config: IngestionConfig) -> None:
        self._config = config
        self._client = QdrantClient(url=config.qdrant_url)
        self._sparse_encoder = FastEmbedSparseEncoder(
            SparseEncoderConfig(model_name=config.sparse_model_name)
        )

    def ensure_collection(self) -> None:
        name = self._config.qdrant_collection
        if self._client.collection_exists(name):
            self._validate_hybrid_schema(name)
            return

        dense_name = self._config.dense_vector_name
        sparse_name = self._config.sparse_vector_name

        def _create() -> None:
            self._client.create_collection(
                collection_name=name,
                vectors_config={
                    dense_name: qmodels.VectorParams(
                        size=self._config.vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                },
                sparse_vectors_config={
                    sparse_name: qmodels.SparseVectorParams(
                        modifier=qmodels.Modifier.IDF,
                    ),
                },
            )

        with_retry_sync(
            _create,
            attempts=self._config.retry_attempts,
            base_delay=self._config.retry_base_delay_seconds,
            label="qdrant_create_collection",
        )
        logger.info(
            "Created hybrid Qdrant collection %s (dense=%s sparse=%s)",
            name,
            dense_name,
            sparse_name,
        )

    def _validate_hybrid_schema(self, name: str) -> None:
        info = self._client.get_collection(name)
        dense_name = self._config.dense_vector_name
        sparse_name = self._config.sparse_vector_name
        params = info.config.params
        vectors = params.vectors
        sparse = params.sparse_vectors

        if not isinstance(vectors, dict) or dense_name not in vectors:
            raise RuntimeError(
                f"Collection {name} is not hybrid (missing dense vector '{dense_name}'). "
                "Drop the collection and re-ingest — see scripts/recreate-qdrant-hybrid-collection.sh"
            )
        if not sparse or sparse_name not in sparse:
            raise RuntimeError(
                f"Collection {name} is not hybrid (missing sparse vector '{sparse_name}'). "
                "Drop the collection and re-ingest — see scripts/recreate-qdrant-hybrid-collection.sh"
            )

    def upsert_points(
        self,
        *,
        bucket: str,
        object_name: str,
        generation: int,
        content_hash: str,
        chunks: list[tuple[str, str, list[float]]],
    ) -> None:
        """Upsert (point_id, text, dense_vector) tuples with sparse vectors."""
        if not chunks:
            return
        version_key = document_version_id(bucket, object_name, generation)
        uri = logical_uri(bucket, object_name)
        batch_size = self._config.qdrant_upsert_batch_size
        collection = self._config.qdrant_collection
        dense_name = self._config.dense_vector_name
        sparse_name = self._config.sparse_vector_name

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            points = [
                qmodels.PointStruct(
                    id=uuid.UUID(point_id),
                    vector={
                        dense_name: vector,
                        sparse_name: self._sparse_encoder.encode_document(text),
                    },
                    payload={
                        "logical_uri": uri,
                        "document_version_id": version_key,
                        "chunk_index": start + offset,
                        "generation": generation,
                        "content_hash": content_hash,
                        "source_uri": uri,
                        "text": text,
                        "text_preview": text[: self._config.text_preview_chars],
                    },
                )
                for offset, (point_id, text, vector) in enumerate(batch)
            ]

            def _upsert(points: list[qmodels.PointStruct] = points) -> None:
                self._client.upsert(collection_name=collection, points=points)

            with_retry_sync(
                _upsert,
                attempts=self._config.retry_attempts,
                base_delay=self._config.retry_base_delay_seconds,
                label="qdrant_upsert",
            )

    def delete_points(self, point_ids: list[str]) -> None:
        if not point_ids:
            return
        collection = self._config.qdrant_collection
        uuids = [uuid.UUID(pid) for pid in point_ids]
        batch_size = self._config.qdrant_upsert_batch_size

        for start in range(0, len(uuids), batch_size):
            batch = uuids[start : start + batch_size]

            def _delete(batch: list[uuid.UUID] = batch) -> None:
                self._client.delete(
                    collection_name=collection,
                    points_selector=qmodels.PointIdsList(points=batch),
                )

            with_retry_sync(
                _delete,
                attempts=self._config.retry_attempts,
                base_delay=self._config.retry_base_delay_seconds,
                label="qdrant_delete",
            )
