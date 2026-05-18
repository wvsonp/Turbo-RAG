# Turbo-RAG

Enterprise-Ready RAG system on GCP, with Terraform, K8s, Qdrand, Langfuse, MLflow, 

## Project status

Last updated from repo state and component docs (`docs/`). **Phase 1.1 is complete.**

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

| Step | Task | Status | Notes |
| ---- | ---- | ------ | ----- |
| 1.1 | GCP project bootstrap | **Implemented** | Project `turbo-rag`, APIs enabled, remote state bucket `gs://rag-platform-tf-state`, bootstrap SA for Terraform CI |
| 1.2 | Terraform project structure | **Implemented** | `infra/` layout, GCS backend, `dev`/`prod` tfvars, `terraform init` / `validate` / `plan` |
| 1.3 | GKE cluster | **In progress** | Module wired with Workload Identity and three node pools; dev apply pending (quota fix for regional pools / disk size in module) |
| 1.4 | Artifact Registry | **In progress** | Module scaffold only; not wired in root `main.tf` yet |
| 1.5 | CloudSQL (PostgreSQL) | Not started | Placeholder module only |
| 1.6 | Secret Manager | Not started | Placeholder module only |
| 1.7 | Dockerize services (skeleton) | Not started | No `services/` directory yet |
| 1.8 | Helm charts | Not started | No `helm/` directory yet |
| 1.9 | Deploy Qdrant on GKE | Not started | Depends on GKE + Helm |
| 1.10 | Workload Identity bindings | Not started | IAM module scaffold; bindings after GKE and service accounts exist |

### Phases 2–6

| Phase | Status | Notes |
| ----- | ------ | ----- |
| 2 — Ingestion | Blocked | Pub/Sub module scaffold only; no Prefect flows or GCS pipeline |
| 3 — Query & retrieval | Blocked | No FastAPI query service |
| 4 — Observability | Blocked | No Langfuse, Prometheus, Grafana, or OTel |
| 5 — CI/CD + MLflow | Blocked | No `.github/workflows`, no MLflow |
| 6 — Scaling & hardening | Blocked | HPA, load tests, DR, ADRs not started |

### Suggested next steps

1. **`terraform apply`** for GKE (dev) after `terraform plan -var-file=environments/dev.tfvars`.
2. Implement and wire **Artifact Registry** (1.4), then **CloudSQL** and **Secret Manager** (1.5–1.6).
3. Add skeleton **`services/`** images and **`helm/`** charts (1.7–1.9), then Workload Identity bindings (1.10).
