## History

What we did so far, in order (logic over detail):

1. **Module scaffold** — `infra/modules/cloudsql/` with placeholder `main.tf` (Phase 1.5). Folder and `variables.tf` only; not wired in root `main.tf`; no Cloud SQL resources or apply yet.
2. **Phase 1.5 dev apply** — PostgreSQL 15 instance `rag-platform-dev` on PSA private IP `10.16.0.3`; IAM auth flag; automated backups (7 retained); databases `rag_metadata`, `langfuse`, `mlflow`. Prod tfvars set `REGIONAL` HA, deletion protection, and PITR.

## Runbook

Plan and apply (dev):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars -target=module.cloudsql
terraform apply -var-file=environments/dev.tfvars -target=module.cloudsql
```

Verify instance and databases:

```bash
gcloud sql instances describe rag-platform-dev --project=turbo-rag
gcloud sql databases list --instance=rag-platform-dev --project=turbo-rag
terraform output cloudsql_connection_name cloudsql_private_ip
```

Connect from workstation via Cloud SQL Auth Proxy (install: `gcloud components install cloud-sql-proxy`):

```bash
cloud-sql-proxy turbo-rag:us-central1:rag-platform-dev --private-ip
# In another terminal:
psql "host=127.0.0.1 port=5432 user=postgres dbname=rag_metadata sslmode=disable"
```

Private IP reachability from GKE (no DB auth; TCP smoke test only):

```bash
gcloud container clusters get-credentials rag-platform-dev --region us-central1 --project turbo-rag
kubectl run cloudsql-smoke --rm -i --restart=Never --image=postgres:15-alpine -- \
  sh -c 'nc -zv 10.16.0.3 5432'
```

## 2026-05-23 — 2.2 `prefect` database

**What:** Added `prefect` to `local.databases` in `infra/modules/cloudsql/main.tf`; applied dev. One-time postgres grants for IAM users on `prefect` and `rag_metadata` schemas (see `docs/history/prefect.md`).

**Why:** Prefect server metadata store must live on Cloud SQL with IAM auth before Phase 2 orchestration.

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.cloudsql
terraform output cloudsql_database_names | grep prefect
```

**Destroy order:** GKE workloads → `terraform destroy -target=module.cloudsql` → network PSA (see `docs/history/IaC.md`).

## 2026-05-21 — 1.5 Cloud SQL dev apply

**What:** Implemented `infra/modules/cloudsql/` and applied dev instance with private IP only, IAM authentication enabled, backups, and three platform databases. Root outputs expose `cloudsql_connection_name` and `cloudsql_private_ip` for Helm.

**Why:** Managed PostgreSQL on the PSA range is required for ingestion metadata, Langfuse, and MLflow before application skeletons and in-cluster services can persist state.

**Commands:**
```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.cloudsql -auto-approve
gcloud sql instances describe rag-platform-dev --project=turbo-rag
gcloud sql databases list --instance=rag-platform-dev --project=turbo-rag
gcloud container clusters get-credentials rag-platform-dev --region us-central1 --project turbo-rag
kubectl run cloudsql-smoke --rm -i --restart=Never --image=postgres:15-alpine -- sh -c 'nc -zv 10.16.0.3 5432'
```
