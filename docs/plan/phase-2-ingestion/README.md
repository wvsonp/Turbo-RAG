# Phase 2 — Ingestion pipeline

**Goal:** Upload a document → automatic parse, chunk, embed, upsert to Qdrant, metadata in PostgreSQL.

**Blocked until:** Phase 1 complete (GKE, Qdrant, WI, skeleton services deployed).

**Suggested order:** 2.1 → 2.2 → 2.3 → 2.4 → 2.5 (DLQ topology in 2.5; idempotency keys seeded in 2.3).

## Before you start

Complete this checklist **once per project** before the first `terraform apply` in Phase 2. Phase 1 hit the same class of failures when APIs or local tools were missing ([`docs/FAILURES.md`](../../FAILURES.md), [`docs/history/lessons.md`](../../history/lessons.md)).

### APIs (enable before targeted apply)

```bash
gcloud services enable pubsub.googleapis.com aiplatform.googleapis.com \
  --project=turbo-rag
gcloud services list --enabled --project=turbo-rag | grep -E 'pubsub|aiplatform'
```

If apply fails with `API has not been used in project ... or it is disabled`, enable the API and re-run apply (same pattern as PSA / `servicenetworking.googleapis.com` in Phase 1).

### Local tools

| Tool | Used in |
| ---- | ------- |
| `gcloud` | APIs, uploads, Pub/Sub pull, credentials |
| `terraform` | `infra/modules/pubsub`, IAM extension, Cloud SQL DB |
| `kubectl` | Pod proofs, Prefect, flows |
| `gke-gcloud-auth-plugin` | GKE auth (required for `kubectl`) |
| `helm` | Prefect install — or kubectl-only fallback per [`docs/history/secret_manager.md`](../../history/secret_manager.md) |

### GKE reminders (worker pool)

- Regional cluster: `min_node_count` / `max_node_count` on node pools are **per zone** ([`docs/history/lessons.md`](../../history/lessons.md)).
- Prefect flow jobs target the **Spot `worker` pool** — ensure the pool has at least one Ready node before flow validation.
- Any new PVC mounts: set storage paths explicitly (Qdrant snapshot lesson in `lessons.md`).

### Phase 1 lessons to avoid repeating

| Lesson | Phase 2 mitigation |
| ------ | ------------------- |
| API disabled before apply | Prep checklist above |
| `kubectl` / gke auth plugin missing | Tool table above |
| WI roles deferred from 1.10 | Explicit scope in [2.1](2.1-gcs-pubsub.md) |
| Helm missing | Prefect [2.2](2.2-prefect-on-gke.md) documents kubectl fallback |

## Steps

| Step | Doc | Focus |
| ---- | --- | ----- |
| 2.1 | [2.1-gcs-pubsub.md](2.1-gcs-pubsub.md) | GCS + Pub/Sub + WI extension (ingestion/workers) |
| 2.2 | [2.2-prefect-on-gke.md](2.2-prefect-on-gke.md) | Prefect on GKE + `prefect` Cloud SQL DB |
| 2.3 | [2.3-ingestion-flow.md](2.3-ingestion-flow.md) | E2E flow + deterministic chunk IDs |
| 2.4 | [2.4-chunking-mlflow.md](2.4-chunking-mlflow.md) | Chunking experiments + MLflow local file backend |
| 2.5 | [2.5-dlq-idempotency.md](2.5-dlq-idempotency.md) | DLQ topology + idempotency validation |

**Phase done when:** All acceptance criteria in 2.1–2.5 pass in **dev**.
