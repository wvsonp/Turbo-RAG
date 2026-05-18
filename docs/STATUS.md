# Project status

**Last updated:** 2026-05-19  
**Current phase:** 1 — Foundation (Infra as Code)  
**Roadmap:** [`docs/project-roadmap.md`](project-roadmap.md)  
**Step plans:** [`docs/plan/`](plan/README.md) (acceptance criteria per sub-step)

## Completed

- **Roadmap refinement** — Split execution plans into `docs/plan/phase-*`; streamlined [`project-roadmap.md`](project-roadmap.md) with links, security, and environment guidance
- **1.1 GCP bootstrap** — Project `turbo-rag`, APIs enabled, state bucket `gs://rag-platform-tf-state`, bootstrap SA, local `gcloud` + Terraform
- **1.2 Terraform layout** — `infra/` scaffold, `terraform init`, validate + plan (dev); no full root apply beyond GKE module yet
- **1.3 GKE module (code)** — Standard cluster + node pools in Terraform; dev apply in progress (see `docs/history/gke.md`)

## In progress

- **1.3 GKE** — `terraform apply` for dev after successful plan ([plan](plan/phase-1-foundation/1.3-gke-cluster.md))
- **1.2b Network** — VPC / PSA / NAT not started; recommended before private Cloud SQL ([plan](plan/phase-1-foundation/1.2b-network-foundation.md))
- **1.4+** — Artifact Registry module scaffold; wire in root `main.tf`, then Cloud SQL, Secret Manager ([phase-1 README](plan/phase-1-foundation/README.md))

## Blocked

_(none)_

## Notes for agents

- Use **`docs/plan/<phase>/`** for acceptance criteria when implementing a step; update this file when a step’s criteria are met.
- **`README.md`** — Public progress tables; update when a sub-phase step completes (e.g. 1.3, 1.4).
- **`docs/history/`** — Learning journal after meaningful sub-tasks.
- **`docs/FAILURES.md`** — Log breaks before fixing.
