# Project status

**Last updated:** 2026-06-04 (first-time install guide)  
**Current phase:** 3 — Query & retrieval  
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
- **1.10 Workload Identity bindings** — `infra/modules/iam/` with per-service GCP SAs (`api-sa-dev`, etc.), WI bindings to Helm KSAs, `secretAccessor` on `openai-api-key` (api/query), `cloudsql.client` + IAM DB users for all four; Helm SA annotations in values-dev/prod; validated metadata + Secret Manager from `api` pod ([plan](plan/phase-1-foundation/1.10-workload-identity.md), [`docs/history/iam.md`](history/iam.md))
- **Phase 2 plan robustness** — Revised 2.1–2.5 + README: dispatcher-based Pub/Sub ack, GCS generation document identity, metadata/Qdrant contracts, Prefect IAM split, batching, DLQ replay, durable MLflow ([`docs/plan/phase-2-ingestion/`](plan/phase-2-ingestion/), [`docs/history/ingestion.md`](history/ingestion.md))
- **2.1 GCS bucket + Pub/Sub** — `rag-ingestion-dev` bucket, topic `ingestion-uploads`, subs `ingestion-uploads-sub` (600s ack) + test sub, GCS notification, scoped IAM for ingestion/workers; upload→message and WI bucket list validated ([plan](plan/phase-2-ingestion/2.1-gcs-pubsub.md), [`docs/history/pubsub.md`](history/pubsub.md), [`docs/history/iam.md`](history/iam.md))
- **Architecture map** — Added root [`ARCHITECTURE.md`](../ARCHITECTURE.md) with an implementation-derived master Mermaid diagram, current-vs-planned boundaries, runtime flow notes, and operational insights ([`docs/history/architecture.md`](history/architecture.md))
- **Quick dev reset — GKE cost control** — Documented targeted `terraform destroy -target=module.gke` and keep-list (network, Cloud SQL, secrets, AR, Pub/Sub, IAM) in [`quick-dev-reset.md`](../quick-dev-reset.md); full bring-back command sequence (Terraform, CSI, Helm, Qdrant, WI validation)
- **Quick dev reset — smoke pod pattern** — Replaced flaky `kubectl run --rm -i` curl/nc checks in [`quick-dev-reset.md`](../quick-dev-reset.md) with wait-for-Completed + logs; gotcha in [`docs/history/lessons.md`](history/lessons.md)
- **2.2 Prefect on GKE** — `prefect` DB; `prefect-server-sa-{env}` + WI; workers WI in `prefect` namespace; official Prefect Helm charts; Cloud SQL Auth Proxy IAM auth; server on system pool, flow jobs on worker pool; `hello-flow` validated ([plan](plan/phase-2-ingestion/2.2-prefect-on-gke.md), [`docs/history/prefect.md`](history/prefect.md))
- **2.3 Ingestion flow** — Shared `services/shared/rag_platform/` contracts; `rag_metadata` SQL migrations; Prefect `ingest-document` flow (parse/chunk/Vertex embed/Qdrant upsert/stale cleanup); Pub/Sub dispatcher in `ingestion` service (ack after Prefect success); Helm env + Prefect job template; deploy script ([plan](plan/phase-2-ingestion/2.3-ingestion-flow.md), [`docs/history/ingestion.md`](history/ingestion.md))
- **2.4 Chunking + MLflow** — Three chunkers (`fixed`, `recursive`, `semantic`) with registry + `CHUNKER` config; Prefect `chunking-experiment` flow logs params/metrics/artifacts to durable `mlruns-pvc` at `/mlruns`; deploy/upload scripts; production default remains `fixed` pending experiment comparison ([plan](plan/phase-2-ingestion/2.4-chunking-mlflow.md), [`docs/history/ingestion.md`](history/ingestion.md))
- **2.5 DLQ + idempotency** — DLQ topic/sub + `dead_letter_policy` (5 attempts) on main sub; Pub/Sub SA IAM; orphan Qdrant cleanup on document shrink; dispatcher nack-on-create-failure, failure logging, Prometheus counters, DLQ depth poll; replay runbook in history ([plan](plan/phase-2-ingestion/2.5-dlq-idempotency.md), [`docs/history/pubsub.md`](history/pubsub.md), [`docs/history/ingestion.md`](history/ingestion.md))
- **3.1 Query API skeleton** — `POST /query` with Pydantic request/response models and async stub handler; OpenAPI at `/docs`; query Helm on `application` node pool ([plan](plan/phase-3-query-retrieval/3.1-query-api-skeleton.md), [`docs/history/query.md`](history/query.md))
- **3.2 Hybrid search + RRF** — Qdrant dense+sparse collection schema; BM25 sparse encoder in `rag_platform`; ingestion upserts both vectors + full chunk text; query service runs dense/sparse search with app-side RRF, per-step latency logs, `/ready` checks hybrid schema; unit tests for RRF ([plan](plan/phase-3-query-retrieval/3.2-hybrid-search-rrf.md), [`docs/history/query.md`](history/query.md))
- **3.2 Sparse encoder FastEmbed migration** — Replaced the custom BM25-style hash encoder with `fastembed` `Qdrant/bm25`; the ingestion flow uses document sparse embeddings and query uses query sparse embeddings; added sparse adapter tests and service dependencies ([`docs/history/query.md`](history/query.md))
- **Quick dev reset — GKE-only cost path cleanup** — Clarified the targeted `module.gke` destroy/restore path, Qdrant scale-down before PVC disk cleanup, stale image rebuild command, and Phase 3 resume checkpoints in [`quick-dev-reset.md`](../quick-dev-reset.md); added GKE/history lesson notes
- **Quick dev reset — full cost teardown** — Added **Cost control — destroy all GCP except GCS buckets** to [`quick-dev-reset.md`](../quick-dev-reset.md): `terraform state rm` / `import` for `rag-ingestion-dev`, `state rm` for Cloud SQL IAM users before destroy, full destroy/restore commands, post-destroy checks, and Phase 3 resume path
- **README public overview refresh** — Reworked [`README.md`](../README.md) for a public GitHub branch with a clearer introduction, current implementation state, technology stack, platform flow, design decisions, repository map, and detailed progress tables
- **First-time install guide** — Added root [`install_guide.md`](../install_guide.md): clean linear bring-up for §12 onward (Qdrant → Prefect → ingestion → optional chunking → hybrid query). Removes recovery-runbook cruft (build images once, single full `terraform apply`, no targeted re-applies, no collection drop, no query skeleton step); bakes in `FAILURES.md` gotchas (Qdrant snapshot path, ingestion dispatcher rollout after Prefect, repo-root Dockerfile path) and replaces the hardcoded bootstrap password / `sleep` hacks with a prompted secret and `prefect deployment run --watch`

## In progress

- **Phase 3 — Query & retrieval** — CrossEncoder reranker (3.3) ([plan](plan/phase-3-query-retrieval/3.3-reranker.md))

## Blocked

_(none)_

## Notes for agents

- Phase 2 plan revised 2026-05-23 for robustness: dedicated dispatcher (ack after Prefect success), `bucket/object#generation` identity, metadata schema + stale cleanup, `prefect-server-sa` + `workers` WI for Cloud SQL, 600s ack deadline, no `--auto-ack` on main sub, durable MLflow PVC/GCS. See [`docs/plan/phase-2-ingestion/README.md`](plan/phase-2-ingestion/README.md).
- Docker build context for `ingestion`, `workers`, and `query` is `services/` (not `services/<svc>/`) because of shared `rag_platform` package.
- **3.2 migration:** Existing dense-only or pre-FastEmbed `rag_chunks_dev` data must be dropped before re-ingest — see `scripts/recreate-qdrant-hybrid-collection.sh` and `quick-dev-reset.md` section 18. Section 18 assumes Prefect section 14 is already complete.
- Use **`docs/plan/<phase>/`** for acceptance criteria when implementing a step; update this file when a step’s criteria are met.
- **`README.md`** — Public progress tables; update when a sub-phase step completes (e.g. 1.3, 1.4).
- **`docs/history/`** — Learning journal after meaningful sub-tasks.
- **`docs/FAILURES.md`** — Log breaks before fixing.
