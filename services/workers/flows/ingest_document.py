"""Prefect ingestion flow: GCS → parse → chunk → embed → metadata → Qdrant."""

from __future__ import annotations

import logging
import os
import uuid

import asyncpg
from prefect import flow, get_run_logger, task
from prefect.runtime import flow_run

from rag_platform.config import IngestionConfig
from rag_platform.contracts import document_version_id
from rag_platform.logging_utils import configure_logging

from chunking.registry import get_chunker
from db.migrate import ensure_schema
from db.repository import MetadataRepository, build_chunk_records
from embedding.vertex import VertexEmbedder
from gcs.client import download_object
from parsing.parser import parse_bytes
from qdrant.store import QdrantStore

configure_logging("workers-ingest-flow")
logger = logging.getLogger(__name__)


def _flow_run_id() -> str:
    try:
        return str(flow_run.id)
    except Exception:
        return str(uuid.uuid4())


@task
def download_and_parse(
    bucket: str,
    object_name: str,
    generation: int,
    config: IngestionConfig,
) -> tuple[str, list[str]]:
    data, content_hash, _ = download_object(bucket, object_name, generation)
    text = parse_bytes(
        data,
        object_name=object_name,
        max_bytes=config.max_object_bytes,
        max_pdf_pages=config.max_pdf_pages,
    )
    chunks = get_chunker(config.chunker_name, config=config).chunk(
        text, chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap
    )
    return content_hash, chunks


@task
def embed_chunks(chunks: list[str], config: IngestionConfig) -> list[list[float]]:
    embedder = VertexEmbedder(config)
    return embedder.embed_batches(chunks)


@task
def upsert_qdrant(
    *,
    bucket: str,
    object_name: str,
    generation: int,
    content_hash: str,
    chunk_records: list,
    vectors: list[list[float]],
    config: IngestionConfig,
) -> None:
    store = QdrantStore(config)
    store.ensure_collection()
    tuples = [
        (rec.qdrant_point_id, rec.text, vec)
        for rec, vec in zip(chunk_records, vectors, strict=True)
    ]
    store.upsert_points(
        bucket=bucket,
        object_name=object_name,
        generation=generation,
        content_hash=content_hash,
        chunks=tuples,
    )


@task
async def persist_metadata(
    *,
    bucket: str,
    object_name: str,
    generation: int,
    content_hash: str,
    chunk_texts: list[str],
    prefect_flow_run_id: str,
    pubsub_message_id: str | None,
    config: IngestionConfig,
) -> uuid.UUID:
    conn = await asyncpg.connect(
        user=config.db_user,
        database=config.db_name,
        host=config.db_host,
        port=config.db_port,
        ssl=None,
    )
    try:
        await ensure_schema(conn)
        repo = MetadataRepository(conn)
        chunk_records = build_chunk_records(
            bucket, object_name, generation, chunk_texts
        )
        _, version_uuid = await repo.upsert_ingestion_metadata(
            bucket=bucket,
            object_name=object_name,
            generation=generation,
            content_hash=content_hash,
            chunks=chunk_records,
            prefect_flow_run_id=prefect_flow_run_id,
            pubsub_message_id=pubsub_message_id,
        )
        return version_uuid
    finally:
        await conn.close()


@task
async def cleanup_superseded(
    *,
    bucket: str,
    object_name: str,
    generation: int,
    config: IngestionConfig,
) -> None:
    conn = await asyncpg.connect(
        user=config.db_user,
        database=config.db_name,
        host=config.db_host,
        port=config.db_port,
        ssl=None,
    )
    try:
        repo = MetadataRepository(conn)
        superseded_keys = await repo.supersede_stale_versions(
            bucket, object_name, generation
        )
        point_ids = await repo.get_superseded_point_ids(superseded_keys)
        if point_ids:
            store = QdrantStore(config)
            store.delete_points(point_ids)
    finally:
        await conn.close()


@task
async def mark_run_completed(
    version_uuid: uuid.UUID,
    prefect_flow_run_id: str,
    config: IngestionConfig,
) -> None:
    conn = await asyncpg.connect(
        user=config.db_user,
        database=config.db_name,
        host=config.db_host,
        port=config.db_port,
        ssl=None,
    )
    try:
        repo = MetadataRepository(conn)
        await repo.mark_completed(version_uuid, prefect_flow_run_id)
    finally:
        await conn.close()


@task
async def mark_run_failed(
    bucket: str,
    object_name: str,
    generation: int,
    prefect_flow_run_id: str,
    config: IngestionConfig,
) -> None:
    conn = await asyncpg.connect(
        user=config.db_user,
        database=config.db_name,
        host=config.db_host,
        port=config.db_port,
        ssl=None,
    )
    try:
        version_key = document_version_id(bucket, object_name, generation)
        row = await conn.fetchrow(
            "SELECT id FROM document_versions WHERE document_version_id = $1",
            version_key,
        )
        if row:
            repo = MetadataRepository(conn)
            await repo.mark_failed(row["id"], prefect_flow_run_id)
    finally:
        await conn.close()


@flow(name="ingest-document", log_prints=True)
async def ingest_document(
    bucket: str,
    object_name: str,
    generation: str,
    pubsub_message_id: str | None = None,
) -> None:
    run_logger = get_run_logger()
    config = IngestionConfig.from_env()
    gen_int = int(generation)
    version_key = document_version_id(bucket, object_name, generation)
    flow_id = _flow_run_id()

    run_logger.info(
        "Starting ingestion document_version_id=%s prefect_flow_run_id=%s pubsub_message_id=%s",
        version_key,
        flow_id,
        pubsub_message_id or "",
    )

    try:
        content_hash, chunk_texts = download_and_parse(
            bucket, object_name, gen_int, config
        )
        if not chunk_texts:
            run_logger.warning("No chunks produced for %s", version_key)
            chunk_texts = [""]

        vectors = embed_chunks(chunk_texts, config)
        chunk_records = build_chunk_records(
            bucket, object_name, gen_int, chunk_texts
        )

        version_uuid = await persist_metadata(
            bucket=bucket,
            object_name=object_name,
            generation=gen_int,
            content_hash=content_hash,
            chunk_texts=chunk_texts,
            prefect_flow_run_id=flow_id,
            pubsub_message_id=pubsub_message_id,
            config=config,
        )

        upsert_qdrant(
            bucket=bucket,
            object_name=object_name,
            generation=gen_int,
            content_hash=content_hash,
            chunk_records=chunk_records,
            vectors=vectors,
            config=config,
        )

        await cleanup_superseded(
            bucket=bucket,
            object_name=object_name,
            generation=gen_int,
            config=config,
        )

        await mark_run_completed(version_uuid, flow_id, config)
        run_logger.info(
            "Completed ingestion document_version_id=%s prefect_flow_run_id=%s",
            version_key,
            flow_id,
        )
    except Exception:
        await mark_run_failed(
            bucket, object_name, gen_int, flow_id, config
        )
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        ingest_document(
            bucket=os.environ["BUCKET"],
            object_name=os.environ["OBJECT_NAME"],
            generation=os.environ["GENERATION"],
            pubsub_message_id=os.environ.get("PUBSUB_MESSAGE_ID"),
        )
    )
