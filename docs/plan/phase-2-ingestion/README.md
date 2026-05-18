# Phase 2 — Ingestion pipeline

**Goal:** Upload a document → automatic parse, chunk, embed, upsert to Qdrant, metadata in PostgreSQL.

**Blocked until:** Phase 1 complete (GKE, Qdrant, WI, Pub/Sub module wired).

| Step | Doc |
| ---- | --- |
| 2.1 | [2.1-gcs-pubsub.md](2.1-gcs-pubsub.md) |
| 2.2 | [2.2-prefect-on-gke.md](2.2-prefect-on-gke.md) |
| 2.3 | [2.3-ingestion-flow.md](2.3-ingestion-flow.md) |
| 2.4 | [2.4-chunking-mlflow.md](2.4-chunking-mlflow.md) |
| 2.5 | [2.5-dlq-idempotency.md](2.5-dlq-idempotency.md) |
