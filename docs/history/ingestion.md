## History

What we did so far, in order (logic over detail):

1. **Phase 2 plan robustness (2026-05-23)** — Updated `docs/plan/phase-2-ingestion/` README and steps 2.1–2.5 before implementation.
2. **2.3 Ingestion flow (2026-05-23)** — E2E dispatcher + Prefect flow with metadata schema, Vertex embeddings, Qdrant upsert, stale cleanup.

## 2026-05-23 — Phase 2 plan robustness

**What:** Revised Phase 2 ingestion plans with explicit architecture decisions: dispatcher service for Pub/Sub (ack only after Prefect success), GCS `bucket/object#generation` document version identity, PostgreSQL metadata schema, Qdrant point ID formula, Prefect server/worker IAM split, batching/concurrency defaults, DLQ replay runbook, and durable MLflow storage (PVC or GCS copy).

**Why:** Avoid hard-to-change mistakes in ack semantics, idempotency, stale vectors, Cloud SQL auth, and ephemeral experiment artifacts before coding 2.1.

**Key references:**

- [`docs/plan/phase-2-ingestion/README.md`](../plan/phase-2-ingestion/README.md) — invariants and data contracts
- [`docs/plan/phase-2-ingestion/2.1-gcs-pubsub.md`](../plan/phase-2-ingestion/2.1-gcs-pubsub.md) — dispatcher contract, 600s ack deadline
- [`docs/plan/phase-2-ingestion/2.2-prefect-on-gke.md`](../plan/phase-2-ingestion/2.2-prefect-on-gke.md) — `prefect-server-sa`, Cloud SQL IAM auth
- [`docs/plan/phase-2-ingestion/2.3-ingestion-flow.md`](../plan/phase-2-ingestion/2.3-ingestion-flow.md) — metadata schema, stale cleanup, batching

## 2026-05-23 — 2.3 Ingestion flow

**What:** Implemented end-to-end ingestion: shared contracts in `services/shared/rag_platform/`; SQL migrations for `documents`, `document_versions`, `chunks`, `ingestion_runs`; Prefect `ingest-document` flow in `services/workers/flows/` (GCS download → parse → chunk → Vertex `text-embedding-004` → metadata commit → Qdrant upsert → superseded cleanup); Pub/Sub dispatcher in `services/ingestion/dispatcher.py` (pull without early ack, start Prefect run, extend deadline, ack on `Completed`); Helm env for dispatcher and workers; updated Prefect base job template (Cloud SQL proxy sidecar, workers image); `scripts/register-ingest-deployment.sh`.

**Why:** Phase 2 requires automatic document indexing with idempotent version identity, PostgreSQL as source of truth, and clear Pub/Sub retry boundaries before DLQ (2.5) and chunking experiments (2.4).

**Commands:**

```bash
# Build (context is services/ for shared package)
cd /home/wvsonp/Turbo-RAG/services
SHA=$(git -C .. rev-parse --short HEAD)
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"
for svc in ingestion workers; do
  docker build -f "${svc}/Dockerfile" -t "${svc}:local" .
  docker tag "${svc}:local" "${REGISTRY}/${svc}:${SHA}"
  docker push "${REGISTRY}/${svc}:${SHA}"
done

# Register Prefect deployment + redeploy dispatcher
WORKERS_IMAGE="${REGISTRY}/workers:${SHA}" bash ../scripts/register-ingest-deployment.sh
helm upgrade --install ingestion ../helm/ingestion \
  -f ../helm/ingestion/values.yaml -f ../helm/ingestion/values-dev.yaml \
  --set "image.tag=${SHA}" --namespace platform

# E2E trigger (never --auto-ack on ingestion-uploads-sub)
echo "test-$(date +%s)" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag
kubectl logs -n platform deploy/ingestion -f --tail=50
```

**Layout:**

| Component | Path |
| --------- | ---- |
| Contracts / config | `services/shared/rag_platform/` |
| Dispatcher | `services/ingestion/dispatcher.py` |
| Prefect flow | `services/workers/flows/ingest_document.py` |
| DB migrations | `services/workers/migrations/` |
| Deploy script | `scripts/register-ingest-deployment.sh` |

**Not in 2.3:** DLQ Terraform ([2.5](../plan/phase-2-ingestion/2.5-dlq-idempotency.md)); chunking MLflow comparison ([2.4](../plan/phase-2-ingestion/2.4-chunking-mlflow.md)).
