"""Environment-driven configuration — single source for ingestion defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class IngestionConfig:
    project_id: str
    vertex_region: str
    vertex_embedding_model: str
    embedding_batch_size: int
    qdrant_url: str
    qdrant_collection: str
    qdrant_upsert_batch_size: int
    vector_size: int
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    max_object_bytes: int
    max_pdf_pages: int
    text_preview_chars: int
    chunk_size: int
    chunk_overlap: int
    chunker_name: str
    retry_attempts: int
    retry_base_delay_seconds: float

    @classmethod
    def from_env(cls) -> IngestionConfig:
        return cls(
            project_id=os.getenv("GCP_PROJECT", "turbo-rag"),
            vertex_region=os.getenv("VERTEX_REGION", "us-central1"),
            vertex_embedding_model=os.getenv(
                "VERTEX_EMBEDDING_MODEL", "text-embedding-004"
            ),
            embedding_batch_size=_int("EMBEDDING_BATCH_SIZE", 32),
            qdrant_url=os.getenv(
                "QDRANT_URL", "http://qdrant.platform.svc.cluster.local:6333"
            ),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "rag_chunks_dev"),
            qdrant_upsert_batch_size=_int("QDRANT_UPSERT_BATCH_SIZE", 100),
            vector_size=_int("VECTOR_SIZE", 768),
            db_host=os.getenv("DB_HOST", "127.0.0.1"),
            db_port=_int("DB_PORT", 5432),
            db_name=os.getenv("DB_NAME", "rag_metadata"),
            db_user=os.getenv("DB_USER", "workers-sa-dev@turbo-rag.iam"),
            max_object_bytes=_int("MAX_OBJECT_BYTES", 10 * 1024 * 1024),
            max_pdf_pages=_int("MAX_PDF_PAGES", 10),
            text_preview_chars=_int("TEXT_PREVIEW_CHARS", 200),
            chunk_size=_int("CHUNK_SIZE", 512),
            chunk_overlap=_int("CHUNK_OVERLAP", 64),
            chunker_name=os.getenv("CHUNKER", "fixed").strip().lower(),
            retry_attempts=_int("RETRY_ATTEMPTS", 3),
            retry_base_delay_seconds=_float("RETRY_BASE_DELAY_SECONDS", 1.0),
        )


@dataclass(frozen=True)
class DispatcherConfig:
    project_id: str
    subscription: str
    dlq_subscription: str
    prefect_api_url: str
    prefect_deployment_name: str
    max_concurrent_runs: int
    ack_extension_seconds: int
    poll_interval_seconds: float
    flow_timeout_seconds: int
    dlq_poll_interval_seconds: float

    @classmethod
    def from_env(cls) -> DispatcherConfig:
        return cls(
            project_id=os.getenv("GCP_PROJECT", "turbo-rag"),
            subscription=os.getenv(
                "PUBSUB_SUBSCRIPTION", "ingestion-uploads-sub"
            ),
            dlq_subscription=os.getenv(
                "PUBSUB_DLQ_SUBSCRIPTION", "ingestion-uploads-dlq-sub"
            ),
            prefect_api_url=os.getenv(
                "PREFECT_API_URL",
                "http://prefect-server.prefect.svc.cluster.local:4200/api",
            ),
            prefect_deployment_name=os.getenv(
                "PREFECT_DEPLOYMENT_NAME", "ingest-document/ingest-document"
            ),
            max_concurrent_runs=_int("DISPATCHER_MAX_CONCURRENT", 2),
            ack_extension_seconds=_int("ACK_EXTENSION_SECONDS", 60),
            poll_interval_seconds=_float("DISPATCHER_POLL_INTERVAL_SECONDS", 5.0),
            flow_timeout_seconds=_int("DISPATCHER_FLOW_TIMEOUT_SECONDS", 540),
            dlq_poll_interval_seconds=_float("DLQ_POLL_INTERVAL_SECONDS", 60.0),
        )


@dataclass(frozen=True)
class ExperimentConfig:
    mlflow_tracking_uri: str
    mlflow_experiment_name: str
    test_gcs_uri: str
    sample_chunk_count: int
    environment: str

    @classmethod
    def from_env(cls) -> ExperimentConfig:
        return cls(
            mlflow_tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "file:/mlruns"),
            mlflow_experiment_name=os.getenv(
                "MLFLOW_EXPERIMENT_NAME", "chunking-strategies"
            ),
            test_gcs_uri=os.getenv(
                "EXPERIMENT_TEST_GCS_URI",
                "gs://rag-ingestion-dev/experiments/chunking-sample.txt",
            ),
            sample_chunk_count=_int("EXPERIMENT_SAMPLE_CHUNK_COUNT", 5),
            environment=os.getenv("ENVIRONMENT", "dev"),
        )
