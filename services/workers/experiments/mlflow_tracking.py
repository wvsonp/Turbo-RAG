"""MLflow helpers for chunking experiments."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import mlflow

from rag_platform.config import ExperimentConfig, IngestionConfig


def configure_tracking(exp_config: ExperimentConfig) -> None:
    mlflow.set_tracking_uri(exp_config.mlflow_tracking_uri)
    mlflow.set_experiment(exp_config.mlflow_experiment_name)


def log_chunking_run(
    *,
    chunker_name: str,
    chunks: list[str],
    chunk_size: int,
    chunk_overlap: int,
    document_version_id: str,
    flow_duration_seconds: float,
    embedding_batch_size: int,
    exp_config: ExperimentConfig,
    ingest_config: IngestionConfig,
) -> str:
    chunk_count = len(chunks)
    avg_length = (
        sum(len(chunk) for chunk in chunks) / chunk_count if chunk_count else 0.0
    )
    embedding_batch_count = (
        math.ceil(chunk_count / embedding_batch_size) if chunk_count else 0
    )

    with mlflow.start_run(run_name=f"chunker-{chunker_name}") as run:
        mlflow.set_tags(
            {
                "phase": "2.4",
                "environment": exp_config.environment,
                "chunker": chunker_name,
            }
        )
        mlflow.log_params(
            {
                "chunker": chunker_name,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "document_version_id": document_version_id,
                "vertex_embedding_model": ingest_config.vertex_embedding_model,
            }
        )
        mlflow.log_metrics(
            {
                "chunk_count": float(chunk_count),
                "avg_chunk_length": avg_length,
                "flow_duration_seconds": flow_duration_seconds,
                "embedding_batch_count": float(embedding_batch_count),
            }
        )
        _log_sample_chunks(chunks, exp_config.sample_chunk_count)
        return run.info.run_id


def _log_sample_chunks(chunks: list[str], sample_count: int) -> None:
    sample = [
        {"index": index, "length": len(text), "text": text}
        for index, text in enumerate(chunks[:sample_count])
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample_chunks.json"
        path.write_text(json.dumps(sample, indent=2), encoding="utf-8")
        mlflow.log_artifact(str(path), artifact_path="chunks")
