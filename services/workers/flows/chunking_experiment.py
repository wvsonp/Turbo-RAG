"""Prefect flow: compare chunking strategies and log MLflow runs."""

from __future__ import annotations

import logging
import time

from prefect import flow, get_run_logger, task

from rag_platform.config import ExperimentConfig, IngestionConfig
from rag_platform.contracts import document_version_id
from rag_platform.logging_utils import configure_logging

from chunking.registry import ALL_CHUNKER_NAMES, get_chunker
from experiments.mlflow_tracking import configure_tracking, log_chunking_run
from gcs.experiment import download_uri
from parsing.parser import parse_bytes

configure_logging("workers-chunking-experiment")
logger = logging.getLogger(__name__)


@task
def load_test_document(
    exp_config: ExperimentConfig, ingest_config: IngestionConfig
) -> tuple[str, str, int, str, str]:
    bucket, object_name, generation, data, content_hash = download_uri(
        exp_config.test_gcs_uri
    )
    text = parse_bytes(
        data,
        object_name=object_name,
        max_bytes=ingest_config.max_object_bytes,
        max_pdf_pages=ingest_config.max_pdf_pages,
    )
    version_key = document_version_id(bucket, object_name, generation)
    return bucket, object_name, generation, version_key, text


@task
def run_chunker_experiment(
    chunker_name: str,
    text: str,
    document_version_key: str,
    ingest_config: IngestionConfig,
    exp_config: ExperimentConfig,
) -> str:
    chunker = get_chunker(chunker_name, config=ingest_config)
    started = time.perf_counter()
    chunks = chunker.chunk(
        text,
        chunk_size=ingest_config.chunk_size,
        chunk_overlap=ingest_config.chunk_overlap,
    )
    duration = time.perf_counter() - started
    return log_chunking_run(
        chunker_name=chunker_name,
        chunks=chunks,
        chunk_size=ingest_config.chunk_size,
        chunk_overlap=ingest_config.chunk_overlap,
        document_version_id=document_version_key,
        flow_duration_seconds=duration,
        embedding_batch_size=ingest_config.embedding_batch_size,
        exp_config=exp_config,
        ingest_config=ingest_config,
    )


@flow(name="chunking-experiment", log_prints=True)
def chunking_experiment() -> dict[str, str]:
    run_logger = get_run_logger()
    ingest_config = IngestionConfig.from_env()
    exp_config = ExperimentConfig.from_env()
    configure_tracking(exp_config)

    _, _, _, version_key, text = load_test_document(exp_config, ingest_config)
    run_logger.info(
        "Starting chunking experiment document_version_id=%s chunkers=%s tracking_uri=%s",
        version_key,
        ",".join(ALL_CHUNKER_NAMES),
        exp_config.mlflow_tracking_uri,
    )

    run_ids: dict[str, str] = {}
    for chunker_name in ALL_CHUNKER_NAMES:
        run_id = run_chunker_experiment(
            chunker_name,
            text,
            version_key,
            ingest_config,
            exp_config,
        )
        run_ids[chunker_name] = run_id
        run_logger.info("Logged MLflow run chunker=%s run_id=%s", chunker_name, run_id)

    run_logger.info("Completed chunking experiment runs=%s", run_ids)
    return run_ids


if __name__ == "__main__":
    chunking_experiment()
