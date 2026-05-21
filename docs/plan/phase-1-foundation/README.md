# Phase 1 — Foundation (Infra as Code)

**Goal:** Reproducible GCP + GKE platform; skeleton services deployable via Helm. No RAG business logic yet.

| Step | Doc | Status (repo) |
| ---- | --- | ------------- |
| 1.1 | [1.1-gcp-bootstrap.md](1.1-gcp-bootstrap.md) | Done |
| 1.2 | [1.2-terraform-layout.md](1.2-terraform-layout.md) | Done |
| 1.2b | [1.2b-network-foundation.md](1.2b-network-foundation.md) | Done (dev) |
| 1.3 | [1.3-gke-cluster.md](1.3-gke-cluster.md) | Done (dev) |
| 1.4 | [1.4-artifact-registry.md](1.4-artifact-registry.md) | Done (dev) |
| 1.5 | [1.5-cloudsql.md](1.5-cloudsql.md) | Done (dev) |
| 1.6 | [1.6-secret-manager.md](1.6-secret-manager.md) | Done (dev) |
| 1.7 | [1.7-service-skeletons.md](1.7-service-skeletons.md) | Not started |
| 1.8 | [1.8-helm-charts.md](1.8-helm-charts.md) | Not started |
| 1.9 | [1.9-qdrant.md](1.9-qdrant.md) | Not started |
| 1.10 | [1.10-workload-identity.md](1.10-workload-identity.md) | Not started |

**Phase done when:** All acceptance criteria in 1.1–1.10 pass in **dev**; prod tfvars documented but apply optional until Phase 5 CI.
