## History

What we did so far, in order (logic over detail):

1. **Module scaffold** — `infra/modules/iam/` with placeholder `main.tf` (Phase 1.1+). Folder and `variables.tf` only; not wired in root `main.tf`; no IAM resources in Terraform yet (bootstrap SA notes live in `lessons.md` / `IaC.md`).
2. **Phase 1.10 implementation** — Four per-service GCP SAs with env suffix, Workload Identity bindings to Helm KSAs in `platform`, least-privilege IAM on existing resources; Helm `serviceAccount.annotations` in values-dev/prod.

## Runbook

Terraform (dev):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars -target=module.iam
terraform apply -var-file=environments/dev.tfvars -target=module.iam
terraform output iam_service_account_emails iam_k8s_service_account_annotations
```

Helm redeploy (values-dev.yaml includes WI annotations; apply **after** `module.iam`):

```bash
gcloud container clusters get-credentials rag-platform-dev --region us-central1 --project turbo-rag
cd /home/wvsonp/Turbo-RAG
for svc in api ingestion query workers; do
  helm upgrade --install "$svc" "helm/$svc" \
    -f "helm/$svc/values.yaml" \
    -f "helm/$svc/values-dev.yaml" \
    --namespace platform
done
kubectl get sa -n platform api ingestion query workers \
  -o custom-columns=NAME:.metadata.name,GSA:.metadata.annotations.'iam\.gke\.io/gcp-service-account'
```

Workload Identity validation (kubectl 1.34+ uses `--overrides` instead of `--serviceaccount`):

```bash
for sa in api ingestion query workers; do
  kubectl run "wi-check-$sa" --rm -i --restart=Never -n platform \
    --image=curlimages/curl:latest \
    --overrides="{\"spec\":{\"serviceAccountName\":\"$sa\"}}" \
    -- curl -sf -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
done
```

Secret Manager proof (api SA):

```bash
kubectl run wi-secret-test --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"api"}}' \
  --command -- sh -c 'gcloud secrets versions access latest --secret=openai-api-key --project=turbo-rag >/dev/null && echo SECRET_ACCESS_OK'
kubectl wait --for=condition=ready pod/wi-secret-test -n platform --timeout=90s
kubectl logs wi-secret-test -n platform
kubectl delete pod wi-secret-test -n platform
```

**Destroy order:** remove Helm releases using WI SAs → `terraform destroy -target=module.iam` before deleting Cloud SQL instance (IAM DB users depend on instance).

## 2026-05-22 — 1.10 Workload Identity dev apply

**What:** Implemented `infra/modules/iam/` (18 resources): GCP SAs `api-sa-dev`, `ingestion-sa-dev`, `query-sa-dev`, `workers-sa-dev`; WI bindings to `platform/{api,ingestion,query,workers}`; `secretAccessor` on `openai-api-key` for api/query; `cloudsql.client` + Cloud SQL IAM users for all four. Updated Helm values-dev/prod with `iam.gke.io/gcp-service-account` annotations; redeployed charts; validated metadata email and Secret Manager access from api pod.

**Why:** Pods must call GCP APIs without JSON keys before Phase 2 ingestion and later secret/DB access from application code.

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.iam -auto-approve
# helm upgrade loop and WI checks — see Runbook above
```

**Deferred to 2.1:** GCS, Pub/Sub, and Vertex IAM roles for ingestion/workers (no buckets/topics yet).

## 2026-05-23 — 2.1 Ingestion IAM (scoped GCS / Pub/Sub / Vertex)

**What:** Added `infra/modules/iam/ingestion.tf` with scoped bindings: `ingestion-sa-{env}` → `storage.objectViewer` on `rag-ingestion-{env}` + `pubsub.subscriber` on `ingestion-uploads-sub` (dispatcher-only; workers do not subscribe); `workers-sa-{env}` → `storage.objectViewer` on bucket + `aiplatform.user` at project level.

**Why:** Phase 2 ingestion needs least-privilege access to the upload bucket and Pub/Sub main subscription without JSON keys; workers need GCS read and Vertex embeddings access for flow jobs (2.3).

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.pubsub -target=module.iam

kubectl run wi-gcs-ingestion --rm -i --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"ingestion"}}' \
  -- gcloud storage ls gs://rag-ingestion-dev/incoming/ --project=turbo-rag
```
