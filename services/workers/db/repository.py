"""PostgreSQL metadata repository for ingestion."""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg

from rag_platform.contracts import chunk_point_id, document_version_id, logical_uri

logger = logging.getLogger(__name__)


@dataclass
class ChunkRecord:
    chunk_index: int
    text: str
    text_hash: str
    qdrant_point_id: str


class MetadataRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def upsert_ingestion_metadata(
        self,
        *,
        bucket: str,
        object_name: str,
        generation: int,
        content_hash: str,
        chunks: list[ChunkRecord],
        prefect_flow_run_id: str,
        pubsub_message_id: str | None,
    ) -> tuple[uuid.UUID, uuid.UUID]:
        uri = logical_uri(bucket, object_name)
        version_key = document_version_id(bucket, object_name, generation)
        now = datetime.now(timezone.utc)

        async with self._conn.transaction():
            doc_row = await self._conn.fetchrow(
                """
                INSERT INTO documents (id, logical_uri, status, created_at, updated_at)
                VALUES ($1, $2, 'processing', $3, $3)
                ON CONFLICT (logical_uri) DO UPDATE
                SET status = 'processing', updated_at = EXCLUDED.updated_at
                RETURNING id
                """,
                uuid.uuid4(),
                uri,
                now,
            )
            document_id = doc_row["id"]

            version_row = await self._conn.fetchrow(
                """
                INSERT INTO document_versions (
                    id, document_id, document_version_id, bucket, object_name,
                    generation, content_hash, status, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'processing', $8, $8)
                ON CONFLICT (bucket, object_name, generation) DO UPDATE
                SET content_hash = EXCLUDED.content_hash,
                    status = 'processing',
                    updated_at = EXCLUDED.updated_at
                RETURNING id
                """,
                uuid.uuid4(),
                document_id,
                version_key,
                bucket,
                object_name,
                generation,
                content_hash,
                now,
            )
            version_uuid = version_row["id"]

            await self._conn.execute(
                """
                INSERT INTO ingestion_runs (
                    id, document_version_id, prefect_flow_run_id,
                    pubsub_message_id, status, started_at
                )
                VALUES ($1, $2, $3, $4, 'processing', $5)
                ON CONFLICT (prefect_flow_run_id) DO UPDATE
                SET status = 'processing', started_at = EXCLUDED.started_at
                """,
                uuid.uuid4(),
                version_uuid,
                prefect_flow_run_id,
                pubsub_message_id,
                now,
            )

            for chunk in chunks:
                await self._conn.execute(
                    """
                    INSERT INTO chunks (
                        id, document_version_id, chunk_index, text_hash, qdrant_point_id
                    )
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (document_version_id, chunk_index) DO UPDATE
                    SET text_hash = EXCLUDED.text_hash,
                        qdrant_point_id = EXCLUDED.qdrant_point_id
                    """,
                    uuid.uuid4(),
                    version_uuid,
                    chunk.chunk_index,
                    chunk.text_hash,
                    chunk.qdrant_point_id,
                )

            await self._conn.execute(
                """
                DELETE FROM chunks
                WHERE document_version_id = $1 AND chunk_index >= $2
                """,
                version_uuid,
                len(chunks),
            )

        return document_id, version_uuid

    async def mark_completed(
        self, version_uuid: uuid.UUID, prefect_flow_run_id: str
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._conn.transaction():
            await self._conn.execute(
                """
                UPDATE document_versions SET status = 'completed', updated_at = $2
                WHERE id = $1
                """,
                version_uuid,
                now,
            )
            await self._conn.execute(
                """
                UPDATE documents d SET
                    latest_version_id = $1,
                    status = 'completed',
                    updated_at = $2
                FROM document_versions dv
                WHERE dv.id = $1 AND d.id = dv.document_id
                """,
                version_uuid,
                now,
            )
            await self._conn.execute(
                """
                UPDATE ingestion_runs
                SET status = 'completed', finished_at = $2
                WHERE prefect_flow_run_id = $1
                """,
                prefect_flow_run_id,
                now,
            )

    async def mark_failed(
        self, version_uuid: uuid.UUID, prefect_flow_run_id: str
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._conn.transaction():
            await self._conn.execute(
                """
                UPDATE document_versions SET status = 'failed', updated_at = $2
                WHERE id = $1
                """,
                version_uuid,
                now,
            )
            await self._conn.execute(
                """
                UPDATE ingestion_runs
                SET status = 'failed', finished_at = $2
                WHERE prefect_flow_run_id = $1
                """,
                prefect_flow_run_id,
                now,
            )

    async def supersede_stale_versions(
        self, bucket: str, object_name: str, current_generation: int
    ) -> list[str]:
        """Mark older generations superseded; return their document_version_id strings."""
        rows = await self._conn.fetch(
            """
            UPDATE document_versions
            SET status = 'superseded', updated_at = NOW()
            WHERE bucket = $1 AND object_name = $2 AND generation < $3
              AND status NOT IN ('superseded')
            RETURNING document_version_id, id
            """,
            bucket,
            object_name,
            current_generation,
        )
        return [row["document_version_id"] for row in rows]

    async def get_superseded_point_ids(
        self, document_version_keys: list[str]
    ) -> list[str]:
        if not document_version_keys:
            return []
        rows = await self._conn.fetch(
            """
            SELECT c.qdrant_point_id
            FROM chunks c
            JOIN document_versions dv ON dv.id = c.document_version_id
            WHERE dv.document_version_id = ANY($1::text[])
            """,
            document_version_keys,
        )
        return [row["qdrant_point_id"] for row in rows]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_chunk_records(
    bucket: str,
    object_name: str,
    generation: int,
    texts: list[str],
) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for index, text in enumerate(texts):
        records.append(
            ChunkRecord(
                chunk_index=index,
                text=text,
                text_hash=text_hash(text),
                qdrant_point_id=chunk_point_id(
                    bucket, object_name, generation, index
                ),
            )
        )
    return records
