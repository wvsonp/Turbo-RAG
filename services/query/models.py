"""Request/response models for the query API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryFilters(BaseModel):
    """Optional retrieval filters — used by hybrid search in 3.2+."""

    logical_uri: str | None = Field(
        default=None,
        description="Restrict results to a single logical document (bucket/object_name).",
    )


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8192, description="User question.")
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of chunks to retrieve.",
    )
    filters: QueryFilters | None = None


class RetrievedChunk(BaseModel):
    chunk_index: int
    text: str
    score: float | None = None
    logical_uri: str | None = None
    document_version_id: str | None = None
    source_uri: str | None = None


class QueryResponse(BaseModel):
    query: str
    answer: str = Field(
        default="",
        description="Generated answer — empty until LLM streaming in 3.5.",
    )
    chunks: list[RetrievedChunk] = Field(
        default_factory=list,
        description="Ranked retrieval candidates — populated by hybrid search in 3.2.",
    )
    stub: bool = Field(
        default=True,
        description="True while the endpoint returns schema-valid placeholder results.",
    )
