"""Initial rag_metadata schema for ingestion pipeline."""

revision = "001_initial"
down_revision = None

SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    logical_uri TEXT NOT NULL UNIQUE,
    latest_version_id UUID,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id),
    document_version_id TEXT NOT NULL UNIQUE,
    bucket TEXT NOT NULL,
    object_name TEXT NOT NULL,
    generation BIGINT NOT NULL,
    content_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (bucket, object_name, generation)
);

ALTER TABLE documents
    DROP CONSTRAINT IF EXISTS documents_latest_version_id_fkey;

ALTER TABLE documents
    ADD CONSTRAINT documents_latest_version_id_fkey
    FOREIGN KEY (latest_version_id) REFERENCES document_versions(id);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY,
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    text_hash TEXT,
    qdrant_point_id TEXT NOT NULL,
    UNIQUE (document_version_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY,
    document_version_id UUID NOT NULL REFERENCES document_versions(id),
    prefect_flow_run_id TEXT NOT NULL UNIQUE,
    pubsub_message_id TEXT,
    status TEXT NOT NULL DEFAULT 'processing',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_document_versions_logical
    ON document_versions (bucket, object_name);

CREATE INDEX IF NOT EXISTS idx_document_versions_status
    ON document_versions (status);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_document_version
    ON ingestion_runs (document_version_id);
"""
