## History

What we did so far, in order (logic over detail):

1. **GCP project `turbo-rag`** — created in the Console (org, billing). Needed a billable, isolated project before any automation.
2. **Enable APIs** — `gcloud services enable` for GKE, Cloud SQL, Pub/Sub, Artifact Registry, Secret Manager, Storage, Vertex AI. Provider and later resources need APIs on first.
3. **Terraform state bucket** — `gs://rag-platform-tf-state` during bootstrap (Console or gcloud). Remote state for `terraform init` and future CI.
4. **Terraform bootstrap service account** — Editor + IAM Admin (and Storage Admin) for first applies; narrow permissions in prod later (see `lessons.md`).
5. **Local tooling** — installed `gcloud` and Terraform on the workstation to manage infra from the repo.
6. **Repo layout** — `infra/` with `backend.tf`, provider, `environments/dev|prod.tfvars`, and empty module folders (`gke`, `cloudsql`, `artifact_registry`, `pubsub`, `secret_manager`, `iam`). Phase 1.2 scaffold before wiring real resources.
7. `**terraform init`** — connected to the GCS backend (`terraform/state` prefix).
8. `**terraform validate` and `plan**` — against `dev.tfvars`; scaffold only, no `terraform apply` yet.
9. **Phase 1.2b network (dev)** — `infra/modules/network/` applied: custom VPC, VPC-native subnet, PSA, Cloud NAT, baseline firewalls. GKE module wired to use this VPC (apply GKE separately in 1.3).

## CIDR plan (per environment VPC)

| Range | CIDR | Use |
| ----- | ---- | --- |
| Nodes (primary subnet) | `10.0.0.0/20` | GKE node IPs |
| Pods (secondary) | `10.4.0.0/14` | VPC-native pod alias IPs |
| Services (secondary) | `10.8.0.0/20` | ClusterIP services |
| PSA (global peering) | `10.16.0.0/16` | Cloud SQL private IP |
| Master (GKE) | `172.16.0.0/28` | Private cluster control plane CIDR |

See also [`infra/modules/network/README.md`](../../infra/modules/network/README.md).

## Network apply (dev)

**Why:** Private Cloud SQL and VPC-native GKE require PSA and a dedicated VPC before data-plane services.

Enable APIs if PSA apply fails (see `docs/FAILURES.md`):

```bash
gcloud services enable servicenetworking.googleapis.com compute.googleapis.com --project=turbo-rag
```

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars -target=module.network
terraform apply -var-file=environments/dev.tfvars -target=module.network
```

Verify:

```bash
gcloud compute networks list --project=turbo-rag
gcloud compute addresses list --global --filter="purpose=VPC_PEERING" --project=turbo-rag
```

**Destroy order:** GKE → Cloud SQL → PSA connection → NAT → router → firewalls → subnet → PSA address → VPC.

## Create new project in GCP

activate the apis

```bash
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  sqladmin.googleapis.com \
  pubsub.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  --project=turbo-rag
```

in the local repo install terraform and gcloud

```bash
cd /home/wvsonp/Turbo-RAG

mkdir -p infra/modules/{gke,cloudsql,artifact_registry,pubsub,secret_manager,iam}
mkdir -p infra/environments

gcloud storage ls gs://rag-platform-tf-state/
```

Commands after saving files

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform init
terraform validate
terraform plan -var-file=environments/dev.tfvars
```

## 2026-05-22 — Quick dev reset runbook

**What:** Added root `quick-dev-reset.md` with ordered commands to recreate the current dev platform baseline after Terraform destroy: APIs, remote state bootstrap check, Terraform init, network, GKE, Artifact Registry, Cloud SQL, and validation.

**Why:** A compact reset path makes the dev-to-current-state migration repeatable, so future work can resume at the active Phase 1.6 Secret Manager step after teardown or cost-control cleanup.

**Commands:**
```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform init
terraform validate
terraform apply -var-file=environments/dev.tfvars -target=module.network
terraform apply -var-file=environments/dev.tfvars -target=module.gke
terraform apply -var-file=environments/dev.tfvars -target=module.artifact_registry
terraform apply -var-file=environments/dev.tfvars -target=module.cloudsql
terraform plan -var-file=environments/dev.tfvars
```

## 2026-05-23 — GKE-only cost control teardown

**What:** Added a **Cost control — destroy GKE only** section to `quick-dev-reset.md`: targeted destroy of `module.gke`, keep-list for network, Cloud SQL, Secret Manager, Artifact Registry, Pub/Sub, and IAM, plus ordered steps to bring the cluster back.

**Why:** GKE node pools dominate dev spend; other modules are cheap or require manual re-entry (secret values, image rebuilds, PSA peering).

**Commands:**
```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -destroy -var-file=environments/dev.tfvars -target=module.gke
terraform destroy -var-file=environments/dev.tfvars -target=module.gke
```

**Bring back:** full copy-paste sequence in **Bring GKE back** under Cost control in `quick-dev-reset.md`.
