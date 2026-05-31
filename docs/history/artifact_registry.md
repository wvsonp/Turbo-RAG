## History

What we did so far, in order (logic over detail):

1. **Module scaffold** — `infra/modules/artifact_registry/` with placeholder `main.tf` (Phase 1.4). Folder and `variables.tf` only; not wired in root `main.tf`; no Artifact Registry resources or apply yet.
2. **Phase 1.4 complete** — `google_artifact_registry_repository` `rag-platform` (DOCKER) wired in root `infra/main.tf`; dev apply matches config; outputs `artifact_registry_url` for Helm/CI. Smoke image `smoke-test:latest` present in repo.

## Runbook

Plan and apply (dev):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars -target=module.artifact_registry
terraform apply -var-file=environments/dev.tfvars -target=module.artifact_registry
```

Verify repository:

```bash
gcloud artifacts repositories describe rag-platform --location=us-central1 --project=turbo-rag
terraform output artifact_registry_url
```

Docker auth and test push (requires Docker in WSL or Docker Desktop integration):

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
docker pull hello-world
docker tag hello-world us-central1-docker.pkg.dev/turbo-rag/rag-platform/smoke-test:latest
docker push us-central1-docker.pkg.dev/turbo-rag/rag-platform/smoke-test:latest
gcloud artifacts docker images list us-central1-docker.pkg.dev/turbo-rag/rag-platform --include-tags
```

Image naming convention: `{REGION}-docker.pkg.dev/{PROJECT_ID}/rag-platform/{service}:{git-sha}`

## 2026-05-21 — 1.4 Artifact Registry validated

**What:** Confirmed Terraform-managed `rag-platform` Docker repository in dev; repository URL exposed as root output; existing `smoke-test` image listed in Artifact Registry.

**Why:** Gives all platform services a single, IAM-governed image registry before skeleton builds and Helm deploys in 1.7–1.8.

**Commands:**
```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars -target=module.artifact_registry
gcloud artifacts repositories describe rag-platform --location=us-central1 --project=turbo-rag
terraform output artifact_registry_url
gcloud artifacts docker images list us-central1-docker.pkg.dev/turbo-rag/rag-platform --include-tags
```

## 2026-05-21 — Docker push re-validated (WSL)

**What:** Re-ran local `docker pull` / `tag` / `push` after Docker Desktop WSL integration was enabled; push to `smoke-test:latest` succeeded (digest `sha256:d1a8d0a4...`).

**Commands:**
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
docker pull hello-world:latest
docker tag hello-world:latest us-central1-docker.pkg.dev/turbo-rag/rag-platform/smoke-test:latest
docker push us-central1-docker.pkg.dev/turbo-rag/rag-platform/smoke-test:latest
```
