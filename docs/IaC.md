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

## Create new project in GCP

activate the apis

```bash
gcloud services enable \
  container.googleapis.com \
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

