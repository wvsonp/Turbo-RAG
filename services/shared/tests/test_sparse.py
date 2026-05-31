"""Unit tests for FastEmbed sparse-vector adaptation."""

from rag_platform.sparse import FastEmbedSparseEncoder


class _ArrayLike:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


class _Embedding:
    indices = _ArrayLike([10, 20])
    values = _ArrayLike([1.5, 2])


class _Model:
    def __init__(self):
        self.calls: list[str] = []

    def embed(self, texts):
        self.calls.append(f"document:{texts[0]}")
        return [_Embedding()]

    def query_embed(self, texts):
        self.calls.append(f"query:{texts[0]}")
        return [_Embedding()]


def test_encode_document_uses_document_embedding_path():
    model = _Model()
    encoder = FastEmbedSparseEncoder(model=model)

    vector = encoder.encode_document("hello world")

    assert model.calls == ["document:hello world"]
    assert vector.indices == [10, 20]
    assert vector.values == [1.5, 2.0]


def test_encode_query_uses_query_embedding_path():
    model = _Model()
    encoder = FastEmbedSparseEncoder(model=model)

    vector = encoder.encode_query("hello")

    assert model.calls == ["query:hello"]
    assert vector.indices == [10, 20]
    assert vector.values == [1.5, 2.0]


def test_blank_text_returns_empty_sparse_vector_without_model_call():
    model = _Model()
    encoder = FastEmbedSparseEncoder(model=model)

    vector = encoder.encode_query("  ")

    assert model.calls == []
    assert vector.indices == []
    assert vector.values == []
