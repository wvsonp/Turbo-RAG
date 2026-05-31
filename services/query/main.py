import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from models import QueryRequest, QueryResponse
from rag_platform.config import QueryConfig
from retrieval import HybridRetriever

SERVICE_NAME = os.getenv("SERVICE_NAME", "query")

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","service":"'
    + SERVICE_NAME
    + '","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Turbo-RAG Query Service",
    version="0.2.0",
    description="RAG query API with hybrid dense+sparse retrieval and RRF.",
)

_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    if _retriever is None:
        raise RuntimeError("Retriever not initialized")
    return _retriever


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        get_retriever().check_ready()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return "# HELP up Service up\n# TYPE up gauge\nup 1\n"


@app.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest) -> QueryResponse:
    logger.info(
        "query request query_len=%s top_k=%s filtered=%s",
        len(body.query),
        body.top_k,
        body.filters is not None,
    )
    chunks = await asyncio.to_thread(
        get_retriever().retrieve,
        body.query,
        top_k=body.top_k,
        filters=body.filters,
    )
    return QueryResponse(query=body.query, chunks=chunks, stub=False)


@app.on_event("startup")
async def startup():
    global _retriever
    config = QueryConfig.from_env()
    _retriever = HybridRetriever(config)
    logger.info(
        "started collection=%s prefetch_limit=%d",
        config.qdrant_collection,
        config.hybrid_prefetch_limit,
    )
