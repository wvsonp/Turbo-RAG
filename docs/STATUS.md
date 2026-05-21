# Project status

**Last updated:** 2026-05-21  
**Current phase:** 1 — Foundation (Infra as Code)  
**Roadmap:** [`docs/project-roadmap.md`](project-roadmap.md)  
**Step plans:** [`docs/plan/`](plan/README.md) (acceptance criteria per sub-step)

## Completed

- **Roadmap refinement** — Split execution plans into `docs/plan/phase-*`; streamlined [`project-roadmap.md`](project-roadmap.md) with links, security, and environment guidance
- **1.1 GCP bootstrap** — Project `turbo-rag`, APIs enabled, state bucket `gs://rag-platform-tf-state`, bootstrap SA, local `gcloud` + Terraform
- **1.2 Terraform layout** — `infra/` scaffold, `terraform init`, validate + plan (dev)
- **1.2b Network** — `infra/modules/network/` applied in dev: VPC `rag-platform-dev`, VPC-native subnet, PSA `10.16.0.0/16`, Cloud NAT, firewalls; GKE wired to custom VPC ([plan](plan/phase-1-foundation/1.2b-network-foundation.md), [`docs/history/IaC.md`](history/IaC.md))
- **1.3 GKE** — Standard dev cluster applied on custom VPC with VPC-native networking, private nodes, Workload Identity, and three node pools (see `docs/history/gke.md`)

## In progress

- **1.4 Artifact Registry** — Wire repository module in root `main.tf`, apply in dev, configure Docker auth, and validate an image push ([plan](plan/phase-1-foundation/1.4-artifact-registry.md))
- **1.5+** — Cloud SQL, Secret Manager, service skeletons, Helm, Qdrant, and Workload Identity bindings ([phase-1 README](plan/phase-1-foundation/README.md))

## Blocked

_(none)_

## Notes for agents

- Use **`docs/plan/<phase>/`** for acceptance criteria when implementing a step; update this file when a step’s criteria are met.
- **`README.md`** — Public progress tables; update when a sub-phase step completes (e.g. 1.3, 1.4).
- **`docs/history/`** — Learning journal after meaningful sub-tasks.
- **`docs/FAILURES.md`** — Log breaks before fixing.
