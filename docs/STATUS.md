# Project status

**Last updated:** 2026-05-22 (1.9 done)  
**Current phase:** 1 — Foundation (Infra as Code)  
**Roadmap:** [`docs/project-roadmap.md`](project-roadmap.md)  
**Step plans:** [`docs/plan/`](plan/README.md) (acceptance criteria per sub-step)

## Completed

- **Roadmap refinement** — Split execution plans into `docs/plan/phase-*`; streamlined [`project-roadmap.md`](project-roadmap.md) with links, security, and environment guidance
- **1.1 GCP bootstrap** — Project `turbo-rag`, APIs enabled, state bucket `gs://rag-platform-tf-state`, bootstrap SA, local `gcloud` + Terraform
- **1.2 Terraform layout** — `infra/` scaffold, `terraform init`, validate + plan (dev)
- **1.2b Network** — `infra/modules/network/` applied in dev: VPC `rag-platform-dev`, VPC-native subnet, PSA `10.16.0.0/16`, Cloud NAT, firewalls; GKE wired to custom VPC ([plan](plan/phase-1-foundation/1.2b-network-foundation.md), [`docs/history/IaC.md`](history/IaC.md))
- **1.3 GKE** — Standard dev cluster applied and validated on custom VPC with VPC-native networking, private nodes, Workload Identity, and Ready system/application nodes (see `docs/history/gke.md`)
- **1.4 Artifact Registry** — `rag-platform` Docker repo in Terraform; dev apply clean; `smoke-test` image present; outputs `artifact_registry_url` for Helm/CI ([plan](plan/phase-1-foundation/1.4-artifact-registry.md), [`docs/history/artifact_registry.md`](history/artifact_registry.md))
- **1.5 Cloud SQL** — PostgreSQL 15 `rag-platform-dev` with private IP only, IAM auth flag, backups, databases `rag_metadata` / `langfuse` / `mlflow`; GKE pod reachability smoke test ([plan](plan/phase-1-foundation/1.5-cloudsql.md), [`docs/history/cloudsql.md`](history/cloudsql.md))
- **1.6 Secret Manager** — Secret container `openai-api-key`, GCP SA `secret-accessor-dev`, WI + `secretAccessor` IAM; CSI drivers (kubectl); smoke pod mounts `/var/secrets/openai-api-key` via `platform-secrets` ([plan](plan/phase-1-foundation/1.6-secret-manager.md), [`docs/history/secret_manager.md`](history/secret_manager.md))
- **Quick dev reset runbook** — Added root [`quick-dev-reset.md`](../quick-dev-reset.md) with ordered commands to recreate the current dev platform state after Terraform destroy
- **Rule update for reset docs** — Updated lifecycle/documentation rules so `quick-dev-reset.md` stays current when infra reset requirements change
- **Project status command** — Added `.cursor/commands/project-status.md` to summarize completed work, next task, and goal from this status file
- **1.7 Service skeletons** — Minimal FastAPI skeleton (health/ready/metrics) in `services/{api,ingestion,query,workers}/`; multi-stage Dockerfiles with non-root user; images pushed to `us-central1-docker.pkg.dev/turbo-rag/rag-platform` with `:{git-sha}` tag ([plan](plan/phase-1-foundation/1.7-service-skeletons.md), [`docs/history/service_skeletons.md`](history/service_skeletons.md))
- **1.8 Helm charts** — Charts for `api`, `ingestion`, `query`, `workers` with Artifact Registry images, port 8080, `/health`/`/ready` probes, `values-dev.yaml`/`values-prod.yaml`; deployed to `platform` namespace on dev GKE ([plan](plan/phase-1-foundation/1.8-helm-charts.md), [`docs/history/helm.md`](history/helm.md))
- **1.9 Qdrant on GKE** — `helm/qdrant/` StatefulSet with `qdrant-storage` PVC (`standard-rwo`, 10Gi), ClusterIP service, storage/snapshot paths on PVC; deployed to `platform` on dev GKE ([plan](plan/phase-1-foundation/1.9-qdrant.md), [`docs/history/qdrant.md`](history/qdrant.md))

## In progress

- **1.10 Workload Identity bindings** — per-service GCP SAs and Helm SA annotations ([plan](plan/phase-1-foundation/1.10-workload-identity.md))

## Blocked

_(none)_

## Notes for agents

- Use **`docs/plan/<phase>/`** for acceptance criteria when implementing a step; update this file when a step’s criteria are met.
- **`README.md`** — Public progress tables; update when a sub-phase step completes (e.g. 1.3, 1.4).
- **`docs/history/`** — Learning journal after meaningful sub-tasks.
- **`docs/FAILURES.md`** — Log breaks before fixing.
