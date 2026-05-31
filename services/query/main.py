import logging
import os

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from models import QueryRequest, QueryResponse

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
    version="0.1.0",
    description="RAG query API — retrieval stub until hybrid search (3.2).",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
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
    return QueryResponse(query=body.query)


@app.on_event("startup")
async def startup():
    logger.info("started")
