# Turbo-RAG

Enterprise-ready RAG platform on GCP: Terraform, GKE, Qdrant, Prefect, Langfuse, MLflow.

**Roadmap:** [`docs/project-roadmap.md`](docs/project-roadmap.md) · **Plans:** [`docs/plan/`](docs/plan/README.md) · **Status:** [`docs/STATUS.md`](docs/STATUS.md)

## Project status

Last updated: **2026-05-19**. Phase 1 in progress (1.1–1.2b done; 1.3 GKE apply next).

### Phase summary

| Phase | Focus | Status |
| ----- | ----- | ------ |
| 1 | Foundation — Infra as Code | **In progress** |
| 2 | Ingestion pipeline | Blocked (Phase 1) |
| 3 | Query & retrieval service | Blocked (Phase 1) |
| 4 | Observability stack | Blocked (Phase 1) |
| 5 | CI/CD + MLflow registry | Blocked (Phase 1) |
| 6 | Scaling & hardening | Blocked (Phase 1) |

### Phase 1 — Foundation (detail)

| Step | Task | Status | Plan |
| ---- | ---- | ------ | ---- |
| 1.1 | GCP project bootstrap | **Done** | [1.1](docs/plan/phase-1-foundation/1.1-gcp-bootstrap.md) |
| 1.2 | Terraform project structure | **Done** | [1.2](docs/plan/phase-1-foundation/1.2-terraform-layout.md) |
| 1.2b | Network (VPC, PSA, NAT) | **Done** | [1.2b](docs/plan/phase-1-foundation/1.2b-network-foundation.md) |
| 1.3 | GKE cluster | **In progress** | [1.3](docs/plan/phase-1-foundation/1.3-gke-cluster.md) |
| 1.4 | Artifact Registry | Scaffold | [1.4](docs/plan/phase-1-foundation/1.4-artifact-registry.md) |
| 1.5 | CloudSQL (PostgreSQL) | Not started | [1.5](docs/plan/phase-1-foundation/1.5-cloudsql.md) |
| 1.6 | Secret Manager | Not started | [1.6](docs/plan/phase-1-foundation/1.6-secret-manager.md) |
| 1.7 | Dockerize services (skeleton) | Not started | [1.7](docs/plan/phase-1-foundation/1.7-service-skeletons.md) |
| 1.8 | Helm charts | Not started | [1.8](docs/plan/phase-1-foundation/1.8-helm-charts.md) |
| 1.9 | Deploy Qdrant on GKE | Not started | [1.9](docs/plan/phase-1-foundation/1.9-qdrant.md) |
| 1.10 | Workload Identity bindings | Not started | [1.10](docs/plan/phase-1-foundation/1.10-workload-identity.md) |

### Phases 2–6

See [`docs/plan/`](docs/plan/README.md) for step-by-step acceptance criteria per phase.

### Suggested next steps

1. **`terraform apply`** for GKE (dev) on custom VPC — [1.3 plan](docs/plan/phase-1-foundation/1.3-gke-cluster.md)
2. Wire **Artifact Registry** (1.4), then Cloud SQL + Secret Manager (1.5–1.6; PSA ready)
