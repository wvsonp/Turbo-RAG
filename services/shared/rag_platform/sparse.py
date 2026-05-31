"""FastEmbed sparse vectors for Qdrant hybrid search."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from threading import Lock
from typing import Any

from qdrant_client.http import models as qmodels


@dataclass(frozen=True)
class SparseEncoderConfig:
    model_name: str = "Qdrant/bm25"


class FastEmbedSparseEncoder:
    """Encode text into Qdrant sparse vectors with FastEmbed.

    ``Qdrant/bm25`` expects Qdrant's sparse vector index to use
    ``Modifier.IDF`` so inverse document frequency is computed in Qdrant.
    """

    def __init__(
        self,
        config: SparseEncoderConfig | None = None,
        *,
        model: Any | None = None,
    ) -> None:
        self._config = config or SparseEncoderConfig()
        self._model = model or self._load_model(self._config.model_name)
        self._lock = Lock()

    def encode_document(self, text: str) -> qmodels.SparseVector:
        return self._encode(text, self._model.embed)

    def encode_query(self, text: str) -> qmodels.SparseVector:
        embed = getattr(self._model, "query_embed", self._model.embed)
        return self._encode(text, embed)

    def _encode(
        self,
        text: str,
        embed: Callable[[list[str]], Iterable[Any]],
    ) -> qmodels.SparseVector:
        if not text.strip():
            return qmodels.SparseVector(indices=[], values=[])
        with self._lock:
            embedding = next(iter(embed([text])), None)
        if embedding is None:
            return qmodels.SparseVector(indices=[], values=[])
        return _to_qdrant_sparse_vector(embedding)

    @staticmethod
    def _load_model(model_name: str) -> Any:
        try:
            from fastembed import SparseTextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "fastembed is required for sparse retrieval; install the "
                "query/workers requirements or rebuild their service images."
            ) from exc
        return SparseTextEmbedding(model_name=model_name)


def _to_qdrant_sparse_vector(embedding: Any) -> qmodels.SparseVector:
    return qmodels.SparseVector(
        indices=[int(index) for index in _as_list(embedding.indices)],
        values=[float(value) for value in _as_list(embedding.values)],
    )


def _as_list(values: Any) -> list[Any]:
    if hasattr(values, "tolist"):
        return values.tolist()
    return list(values)
