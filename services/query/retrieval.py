"""Hybrid dense + sparse retrieval with RRF merge."""

from __future__ import annotations

import logging
import time
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from models import QueryFilters, RetrievedChunk
from rag_platform.config import QueryConfig
from rag_platform.embedding import VertexEmbedder
from rag_platform.retry import with_retry_sync
from rag_platform.rrf import reciprocal_rank_fusion
from rag_platform.sparse import FastEmbedSparseEncoder, SparseEncoderConfig

logger = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(self, config: QueryConfig) -> None:
        self._config = config
        self._client = QdrantClient(url=config.qdrant_url)
        self._embedder = VertexEmbedder(config)
        self._sparse_encoder = FastEmbedSparseEncoder(
            SparseEncoderConfig(model_name=config.sparse_model_name)
        )

    def check_ready(self) -> None:
        name = self._config.qdrant_collection
        if not self._client.collection_exists(name):
            raise RuntimeError(f"Qdrant collection {name} does not exist")
        info = self._client.get_collection(name)
        dense_name = self._config.dense_vector_name
        sparse_name = self._config.sparse_vector_name
        vectors = info.config.params.vectors
        sparse = info.config.params.sparse_vectors
        if not isinstance(vectors, dict) or dense_name not in vectors:
            raise RuntimeError(
                f"Collection {name} missing dense vector '{dense_name}'"
            )
        if not sparse or sparse_name not in sparse:
            raise RuntimeError(
                f"Collection {name} missing sparse vector '{sparse_name}'"
            )

    def retrieve(
        self,
        query: str,
        *,
        top_k: int,
        filters: QueryFilters | None = None,
    ) -> list[RetrievedChunk]:
        t0 = time.perf_counter()
        dense_vector = self._embedder.embed_query(query)
        t_embed = time.perf_counter()
        sparse_vector = self._sparse_encoder.encode_query(query)
        t_sparse = time.perf_counter()

        query_filter = self._build_filter(filters)
        prefetch_limit = self._config.hybrid_prefetch_limit

        dense_hits = self._search_dense(
            dense_vector, limit=prefetch_limit, query_filter=query_filter
        )
        t_dense = time.perf_counter()

        sparse_hits = self._search_sparse(
            sparse_vector, limit=prefetch_limit, query_filter=query_filter
        )
        t_sparse_search = time.perf_counter()

        fused = self._fuse_results(dense_hits, sparse_hits)
        t_rrf = time.perf_counter()

        chunks = [
            self._to_chunk(score, payload)
            for _point_id, score, payload in fused[:top_k]
        ]

        logger.info(
            "retrieval step=embed_query duration_ms=%.2f",
            (t_embed - t0) * 1000,
        )
        logger.info(
            "retrieval step=sparse_encode duration_ms=%.2f",
            (t_sparse - t_embed) * 1000,
        )
        logger.info(
            "retrieval step=dense_search duration_ms=%.2f hits=%d",
            (t_dense - t_sparse) * 1000,
            len(dense_hits),
        )
        logger.info(
            "retrieval step=sparse_search duration_ms=%.2f hits=%d",
            (t_sparse_search - t_dense) * 1000,
            len(sparse_hits),
        )
        logger.info(
            "retrieval step=rrf_merge duration_ms=%.2f fused=%d returned=%d",
            (t_rrf - t_sparse_search) * 1000,
            len(fused),
            len(chunks),
        )
        return chunks

    def _build_filter(
        self, filters: QueryFilters | None
    ) -> qmodels.Filter | None:
        if filters is None or filters.logical_uri is None:
            return None
        return qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="logical_uri",
                    match=qmodels.MatchValue(value=filters.logical_uri),
                )
            ]
        )

    def _search_dense(
        self,
        vector: list[float],
        *,
        limit: int,
        query_filter: qmodels.Filter | None,
    ) -> list[qmodels.ScoredPoint]:
        def _query() -> list[qmodels.ScoredPoint]:
            response = self._client.query_points(
                collection_name=self._config.qdrant_collection,
                query=vector,
                using=self._config.dense_vector_name,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            return list(response.points)

        return with_retry_sync(
            _query,
            attempts=self._config.retry_attempts,
            base_delay=self._config.retry_base_delay_seconds,
            label="qdrant_dense_search",
        )

    def _search_sparse(
        self,
        vector: qmodels.SparseVector,
        *,
        limit: int,
        query_filter: qmodels.Filter | None,
    ) -> list[qmodels.ScoredPoint]:
        def _query() -> list[qmodels.ScoredPoint]:
            response = self._client.query_points(
                collection_name=self._config.qdrant_collection,
                query=vector,
                using=self._config.sparse_vector_name,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            return list(response.points)

        return with_retry_sync(
            _query,
            attempts=self._config.retry_attempts,
            base_delay=self._config.retry_base_delay_seconds,
            label="qdrant_sparse_search",
        )

    def _fuse_results(
        self,
        dense_hits: list[qmodels.ScoredPoint],
        sparse_hits: list[qmodels.ScoredPoint],
    ) -> list[tuple[str, float, dict[str, Any]]]:
        dense_ids = [str(point.id) for point in dense_hits]
        sparse_ids = [str(point.id) for point in sparse_hits]
        fused_scores = reciprocal_rank_fusion(
            [dense_ids, sparse_ids],
            k=self._config.rrf_k,
        )

        payload_by_id: dict[str, dict[str, Any]] = {}
        for point in dense_hits + sparse_hits:
            point_id = str(point.id)
            if point_id not in payload_by_id and point.payload:
                payload_by_id[point_id] = dict(point.payload)

        return [
            (point_id, score, payload_by_id[point_id])
            for point_id, score in fused_scores
            if point_id in payload_by_id
        ]

    @staticmethod
    def _to_chunk(score: float, payload: dict[str, Any]) -> RetrievedChunk:
        text = payload.get("text") or payload.get("text_preview") or ""
        return RetrievedChunk(
            chunk_index=int(payload.get("chunk_index", 0)),
            text=str(text),
            score=score,
            logical_uri=payload.get("logical_uri"),
            document_version_id=payload.get("document_version_id"),
            source_uri=payload.get("source_uri"),
        )
