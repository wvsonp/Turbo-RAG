## History

What we did so far, in order (logic over detail):

1. **Phase 2 plan robustness (2026-05-23)** — Updated `docs/plan/phase-2-ingestion/` README and steps 2.1–2.5 before implementation.

## 2026-05-23 — Phase 2 plan robustness

**What:** Revised Phase 2 ingestion plans with explicit architecture decisions: dispatcher service for Pub/Sub (ack only after Prefect success), GCS `bucket/object#generation` document version identity, PostgreSQL metadata schema, Qdrant point ID formula, Prefect server/worker IAM split, batching/concurrency defaults, DLQ replay runbook, and durable MLflow storage (PVC or GCS copy).

**Why:** Avoid hard-to-change mistakes in ack semantics, idempotency, stale vectors, Cloud SQL auth, and ephemeral experiment artifacts before coding 2.1.

**Key references:**

- [`docs/plan/phase-2-ingestion/README.md`](../plan/phase-2-ingestion/README.md) — invariants and data contracts
- [`docs/plan/phase-2-ingestion/2.1-gcs-pubsub.md`](../plan/phase-2-ingestion/2.1-gcs-pubsub.md) — dispatcher contract, 600s ack deadline
- [`docs/plan/phase-2-ingestion/2.2-prefect-on-gke.md`](../plan/phase-2-ingestion/2.2-prefect-on-gke.md) — `prefect-server-sa`, Cloud SQL IAM auth
- [`docs/plan/phase-2-ingestion/2.3-ingestion-flow.md`](../plan/phase-2-ingestion/2.3-ingestion-flow.md) — metadata schema, stale cleanup, batching
