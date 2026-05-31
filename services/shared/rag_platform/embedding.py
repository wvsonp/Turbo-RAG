"""Vertex AI text embeddings."""

from __future__ import annotations

import logging
from typing import Protocol

import vertexai
from vertexai.language_models import TextEmbeddingModel

from rag_platform.retry import with_retry_sync

logger = logging.getLogger(__name__)


class EmbeddingSettings(Protocol):
    project_id: str
    vertex_region: str
    vertex_embedding_model: str
    embedding_batch_size: int
    retry_attempts: int
    retry_base_delay_seconds: float


class VertexEmbedder:
    def __init__(self, config: EmbeddingSettings) -> None:
        self._config = config
        vertexai.init(project=config.project_id, location=config.vertex_region)
        self._model = TextEmbeddingModel.from_pretrained(
            config.vertex_embedding_model
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        batch_size = self._config.embedding_batch_size
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]

            def _call(batch: list[str] = batch) -> list[list[float]]:
                result = self._model.get_embeddings(batch)
                return [item.values for item in result]

            batch_vectors = with_retry_sync(
                _call,
                attempts=self._config.retry_attempts,
                base_delay=self._config.retry_base_delay_seconds,
                label="vertex_embed",
            )
            vectors.extend(batch_vectors)
        return vectors

    def embed_batches(self, texts: list[str]) -> list[list[float]]:
        """Alias kept for ingestion flow compatibility."""
        return self.embed_texts(texts)

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
