# Quick Dev Reset

Use this when the dev GCP platform was destroyed and you want to recreate the
current project state so work can continue at **Phase 3 Query & retrieval**.

Current target state:

- Project: `turbo-rag`
- Region: `us-central1`
- Terraform env: `infra/environments/dev.tfvars`
- Recreated stack: network, GKE, Artifact Registry, Cloud SQL, Secret Manager (containers + accessor SA), GCS ingestion bucket + Pub/Sub (`module.pubsub`), per-service Workload Identity with ingestion IAM (`module.iam`)
- Cluster addons: Secret Store CSI driver + GCP provider (kubectl manifests)
- Helm: api, ingestion (dispatcher), query, workers, qdrant; Prefect server + worker
- Ingestion: dispatcher → Prefect `ingest-document` flow → Qdrant + `rag_metadata`; DLQ on `ingestion-uploads-dlq`; chunking experiments on `mlruns-pvc`
- Query: hybrid dense+sparse retrieval with RRF on application node pool (`POST /query`)
- Next task after reset: `docs/plan/phase-3-query-retrieval/3.3-reranker.md`

## Smoke pods

Avoid `kubectl run --rm -i` for fast one-shot checks (curl, `nc`, short `gcloud`).
kubectl often fails to attach before the container exits, reporting
`terminated (Error)` even when the check succeeded. Pattern used below:
create pod → wait for `Completed` → `kubectl logs` → delete.

## Cost control — destroy GKE only

Use this to stop the main dev spend (GKE node VMs and disks) while keeping
everything that is cheap to run or painful to recreate.

**Destroy (expensive):**

| Resource | Why |
| -------- | --- |
| GKE cluster + node pools (`module.gke`) | Largest ongoing cost: fixed system nodes + application pool |

**Keep running (do not destroy):**

| Resource | Why keep |
| -------- | -------- |
| Network / VPC / PSA / NAT (`module.network`) | Peering and CIDR layout are tedious to rebuild |
| Cloud SQL (`module.cloudsql`) | Data, backups, IAM DB users |
| Secret Manager (`module.secret_manager`) | Secret **values** are manual; containers + IAM are in Terraform |
| Artifact Registry (`module.artifact_registry`) | Pushed service images |
| GCS + Pub/Sub (`module.pubsub`) | Bucket objects and notification wiring |
| Workload Identity (`module.iam`) | GCP SAs, WI bindings, Cloud SQL IAM users |
| State bucket `gs://rag-platform-tf-state` | Bootstrap; always outside teardown |

Cloud SQL (`db-f1-micro`) still incurs a small monthly charge. Destroy it
separately only if you also accept losing DB data and re-running secret value
setup — not covered here.

**What you lose when GKE goes away:** all cluster workloads, Helm releases,
CSI driver pods, and PVC data (including Qdrant vectors). GCP-side IAM, secrets,
SQL, bucket, and registry are unchanged.

No `helm uninstall` required; deleting the cluster removes in-cluster resources.

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform destroy -var-file=environments/dev.tfvars -target=module.gke
```

GKE `deletion_protection` is `false` in dev by default. Confirm with
`terraform plan -destroy -var-file=environments/dev.tfvars -target=module.gke`
before typing `yes`.

### Bring GKE back

Prerequisites: network, Cloud SQL, Secret Manager, Artifact Registry, Pub/Sub,
and IAM modules were **not** destroyed (see keep-list above). Secret values
(e.g. `openai-api-key`) must still exist in Secret Manager — no re-entry needed
if you only destroyed GKE.

**1. Authenticate (if the session expired)**

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project turbo-rag
gcloud config set compute/region us-central1
```

**2. Recreate the cluster**

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform init
terraform apply -var-file=environments/dev.tfvars -target=module.gke
```

**3. Restore kubectl access and wait for nodes**

```bash
gcloud container clusters get-credentials rag-platform-dev \
  --region us-central1 \
  --project turbo-rag

kubectl get nodes -L cloud.google.com/gke-nodepool
kubectl wait --for=condition=ready node --all --timeout=600s
```

Expected: Ready nodes in the `system` and `application` pools. The `worker`
pool may show zero nodes (autoscale min is 0).

**4. Reinstall Secret Store CSI drivers (cluster-scoped; lost with the cluster)**

```bash
CSI_TAG=v1.4.7
BASE="https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/${CSI_TAG}/deploy"
kubectl apply -f "${BASE}/rbac-secretproviderclass.yaml"
kubectl apply -f "${BASE}/csidriver.yaml"
kubectl apply -f "${BASE}/secrets-store.csi.x-k8s.io_secretproviderclasses.yaml"
kubectl apply -f "${BASE}/secrets-store.csi.x-k8s.io_secretproviderclasspodstatuses.yaml"
kubectl apply -f "${BASE}/secrets-store-csi-driver.yaml"
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/secrets-store-csi-driver-provider-gcp/main/deploy/provider-gcp-plugin.yaml
kubectl wait --for=condition=ready pod -l app=csi-secrets-store -n kube-system --timeout=300s
```

**5. Confirm service images in Artifact Registry**

Images should still be present if you only destroyed GKE. List tags:

```bash
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/turbo-rag/rag-platform \
  --include-tags
```

If `api`, `ingestion`, `query`, and `workers` images exist, deploy with the
tags in `helm/*/values-dev.yaml` (skip to step 6). Otherwise rebuild and push:

```bash
cd /home/wvsonp/Turbo-RAG
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"
SHA=$(git rev-parse --short HEAD)
for svc in api ingestion query workers; do
  docker build -t "${svc}:local" "services/${svc}"
  docker tag "${svc}:local" "${REGISTRY}/${svc}:${SHA}"
  docker push "${REGISTRY}/${svc}:${SHA}"
done
```

**6. Deploy platform Helm charts**

Using tags from `values-dev.yaml` (no rebuild):

```bash
cd /home/wvsonp/Turbo-RAG
for svc in api ingestion query workers; do
  helm lint "helm/${svc}" -f "helm/${svc}/values-dev.yaml"
  helm upgrade --install "$svc" "helm/${svc}" \
    -f "helm/${svc}/values.yaml" \
    -f "helm/${svc}/values-dev.yaml" \
    --namespace platform --create-namespace
done
kubectl get pods -n platform
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=api -n platform --timeout=120s
kubectl run curl-smoke --restart=Never -n platform \
  --image=curlimages/curl:latest -- curl -sf http://api:8080/health
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/curl-smoke -n platform --timeout=60s
kubectl logs curl-smoke -n platform
kubectl delete pod curl-smoke -n platform --ignore-not-found
```

If you rebuilt images in step 5, add `--set "image.tag=${SHA}"` to each
`helm upgrade --install` instead of relying on `values-dev.yaml` tags.

**7. Deploy Qdrant (fresh PVC — vector data from before teardown is gone)**

```bash
cd /home/wvsonp/Turbo-RAG
helm lint helm/qdrant -f helm/qdrant/values-dev.yaml
helm upgrade --install qdrant helm/qdrant \
  -f helm/qdrant/values.yaml \
  -f helm/qdrant/values-dev.yaml \
  --namespace platform --create-namespace
kubectl wait --for=condition=ready pod/qdrant-0 -n platform --timeout=120s
kubectl get pvc -n platform -l app.kubernetes.io/name=qdrant
kubectl run curl-qdrant --restart=Never -n platform \
  --image=curlimages/curl:latest -- curl -sf http://qdrant:6333/healthz
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/curl-qdrant -n platform --timeout=60s
kubectl logs curl-qdrant -n platform
kubectl delete pod curl-qdrant -n platform --ignore-not-found
```

**8. Validate Workload Identity and Secret Manager access**

GCP-side WI bindings were kept; Helm charts must recreate KSAs with annotations
from `values-dev.yaml` (step 6):

```bash
for sa in api ingestion query workers; do
  kubectl run "wi-check-$sa" --restart=Never -n platform \
    --image=curlimages/curl:latest \
    --overrides="{\"spec\":{\"serviceAccountName\":\"$sa\"}}" \
    -- curl -sf -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
  kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
    "pod/wi-check-$sa" -n platform --timeout=60s
  kubectl logs "wi-check-$sa" -n platform
  kubectl delete pod "wi-check-$sa" -n platform --ignore-not-found
done
kubectl run wi-secret-test --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"api"}}' \
  --command -- sh -c 'gcloud secrets versions access latest --secret=openai-api-key --project=turbo-rag >/dev/null && echo SECRET_ACCESS_OK'
kubectl wait --for=condition=ready pod/wi-secret-test -n platform --timeout=90s
kubectl logs wi-secret-test -n platform
kubectl delete pod wi-secret-test -n platform
```

**9. Optional smoke tests (GCP resources unchanged; confirms pod reachability)**

Cloud SQL from a pod:

```bash
cd /home/wvsonp/Turbo-RAG/infra
CLOUDSQL_PRIVATE_IP="$(terraform output -raw cloudsql_private_ip)"
kubectl run cloudsql-smoke --restart=Never \
  --env="CLOUDSQL_PRIVATE_IP=${CLOUDSQL_PRIVATE_IP}" \
  --image=postgres:15-alpine \
  --command -- sh -c 'nc -zv "$CLOUDSQL_PRIVATE_IP" 5432'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/cloudsql-smoke --timeout=60s
kubectl logs cloudsql-smoke
kubectl delete pod cloudsql-smoke --ignore-not-found
```

GCS list via ingestion WI:

```bash
kubectl run wi-gcs-ingestion --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"ingestion"}}' \
  -- gcloud storage ls gs://rag-ingestion-dev/incoming/ --project=turbo-rag
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/wi-gcs-ingestion -n platform --timeout=120s
kubectl logs wi-gcs-ingestion -n platform
kubectl delete pod wi-gcs-ingestion -n platform --ignore-not-found
```

Then continue with section 14 (Prefect on GKE), then section 15 (Ingestion flow).

For a full platform teardown (all modules), see destroy order notes in
`docs/history/IaC.md`, `docs/history/iam.md`, and `docs/history/cloudsql.md`.

## 0. Assumptions

Run commands from WSL with `gcloud`, Terraform, `kubectl`, and Docker available.
Helm is optional (CSI drivers can be installed with `kubectl` only; see section 9).
The Terraform state bucket is bootstrap infrastructure and should usually exist
outside normal platform teardown.

If the platform was deleted manually in the GCP Console instead of with
Terraform, first inspect state carefully before applying. The commands below
assume a normal Terraform destroy or a clean state.

## 1. Authenticate and Select the Project

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project turbo-rag
gcloud config set compute/region us-central1
```

## 2. Ensure Required APIs Are Enabled

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

## 3. Verify Remote State Bootstrap

```bash
gcloud storage buckets describe gs://rag-platform-tf-state --project=turbo-rag
```

If the bucket is missing, recreate it before `terraform init`:

```bash
gcloud storage buckets create gs://rag-platform-tf-state \
  --project=turbo-rag \
  --location=us-central1 \
  --uniform-bucket-level-access
```

## 4. Initialize Terraform

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform init
terraform validate
```

## 5. Recreate Dev Infrastructure in Dependency Order

Network comes first because both GKE and Cloud SQL depend on the VPC, subnet,
NAT, and Private Service Access peering.

```bash
terraform apply -var-file=environments/dev.tfvars -target=module.network
```

Then recreate GKE:

```bash
terraform apply -var-file=environments/dev.tfvars -target=module.gke
```

Then recreate Artifact Registry:

```bash
terraform apply -var-file=environments/dev.tfvars -target=module.artifact_registry
```

Then recreate Cloud SQL:

```bash
terraform apply -var-file=environments/dev.tfvars -target=module.cloudsql
```

Finally run a full plan to confirm no remaining drift:

```bash
terraform plan -var-file=environments/dev.tfvars
```

Expected key outputs after reset:

- `artifact_registry_url = "us-central1-docker.pkg.dev/turbo-rag/rag-platform"`
- `cloudsql_connection_name = "turbo-rag:us-central1:rag-platform-dev"`
- `cloudsql_private_ip` allocated from `10.16.0.0/16`
- `gke_cluster_name = "rag-platform-dev"`
- `secret_accessor_gcp_sa_email` (e.g. `secret-accessor-dev@turbo-rag.iam.gserviceaccount.com`)
- `ingestion_bucket_name = "rag-ingestion-dev"`
- `ingestion_topic_name = "ingestion-uploads"`
- `ingestion_subscription_name = "ingestion-uploads-sub"`

## 6. Restore Local GKE Access

```bash
gcloud container clusters get-credentials rag-platform-dev \
  --region us-central1 \
  --project turbo-rag

kubectl get nodes -L cloud.google.com/gke-nodepool
```

Expected: Ready nodes in the `system` and `application` pools. The `worker`
pool can be scaled to zero in dev.

## 7. Validate Artifact Registry

```bash
gcloud artifacts repositories describe rag-platform \
  --location=us-central1 \
  --project=turbo-rag

gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

docker pull hello-world:latest
docker tag hello-world:latest \
  us-central1-docker.pkg.dev/turbo-rag/rag-platform/smoke-test:latest
docker push us-central1-docker.pkg.dev/turbo-rag/rag-platform/smoke-test:latest

gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/turbo-rag/rag-platform \
  --include-tags
```

## 8. Validate Cloud SQL

```bash
gcloud sql instances describe rag-platform-dev --project=turbo-rag
gcloud sql databases list --instance=rag-platform-dev --project=turbo-rag
```

Expected databases:

- `rag_metadata`
- `langfuse`
- `mlflow`

Validate private network reachability from GKE:

```bash
CLOUDSQL_PRIVATE_IP="$(terraform output -raw cloudsql_private_ip)"

kubectl run cloudsql-smoke --restart=Never \
  --env="CLOUDSQL_PRIVATE_IP=${CLOUDSQL_PRIVATE_IP}" \
  --image=postgres:15-alpine \
  --command -- sh -c 'nc -zv "$CLOUDSQL_PRIVATE_IP" 5432'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/cloudsql-smoke --timeout=60s
kubectl logs cloudsql-smoke
kubectl delete pod cloudsql-smoke --ignore-not-found
```

## 9. Secret Manager + CSI (Terraform + cluster)

Apply secret containers and accessor SA:

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.secret_manager
```

Add secret values manually (never commit; repeat per secret as needed):

```bash
echo -n 'your-dev-value' | gcloud secrets versions add openai-api-key \
  --project=turbo-rag --data-file=-
```

Install CSI drivers (kubectl; no Helm required):

```bash
CSI_TAG=v1.4.7
BASE="https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/${CSI_TAG}/deploy"
kubectl apply -f "${BASE}/rbac-secretproviderclass.yaml"
kubectl apply -f "${BASE}/csidriver.yaml"
kubectl apply -f "${BASE}/secrets-store.csi.x-k8s.io_secretproviderclasses.yaml"
kubectl apply -f "${BASE}/secrets-store.csi.x-k8s.io_secretproviderclasspodstatuses.yaml"
kubectl apply -f "${BASE}/secrets-store-csi-driver.yaml"
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/secrets-store-csi-driver-provider-gcp/main/deploy/provider-gcp-plugin.yaml
kubectl wait --for=condition=ready pod -l app=csi-secrets-store -n kube-system --timeout=300s
```

Optional smoke test (see `k8s/secret-manager-csi/` and `docs/history/secret_manager.md`).

## 9b. GCS ingestion bucket + Pub/Sub + Workload Identity

Apply Pub/Sub resources first, then IAM ingestion bindings (root passes bucket/sub names from `module.pubsub`):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.pubsub -target=module.iam
terraform output ingestion_bucket_name ingestion_subscription_name iam_service_account_emails
```

Validate upload → Pub/Sub (use test sub for `--auto-ack`; never on main sub once dispatcher is deployed):

```bash
echo "test-$(date +%s)" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag
sleep 5
gcloud pubsub subscriptions pull ingestion-uploads-test-sub --auto-ack --limit=1 --project=turbo-rag

gcloud pubsub subscriptions describe ingestion-uploads-sub \
  --project=turbo-rag --format="yaml(deadLetterPolicy)"
# Expected: deadLetterTopic → ingestion-uploads-dlq, maxDeliveryAttempts: 5

gcloud pubsub topics get-iam-policy ingestion-uploads-dlq --project=turbo-rag
# Expected: service-{project_number}@gcp-sa-pubsub.iam.gserviceaccount.com → roles/pubsub.publisher

gcloud pubsub subscriptions describe ingestion-uploads-sub \
  --project=turbo-rag --format="value(ackDeadlineSeconds)"
# Expected: 600
```

WI proof (ingestion KSA lists bucket):

```bash
kubectl run wi-gcs-ingestion --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"ingestion"}}' \
  -- gcloud storage ls gs://rag-ingestion-dev/incoming/ --project=turbo-rag
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/wi-gcs-ingestion -n platform --timeout=120s
kubectl logs wi-gcs-ingestion -n platform
kubectl delete pod wi-gcs-ingestion -n platform --ignore-not-found
```

## 9c. Workload Identity (base bindings)

If you applied section 9b, base WI + ingestion IAM are already in place. To apply only the original 1.10 bindings without Pub/Sub (not recommended after Phase 2.1):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.iam
terraform output iam_service_account_emails
```

## 10. Continue Development

After the reset, rebuild service images and push to Artifact Registry:

```bash
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"
SHA=$(git rev-parse --short HEAD)
for svc in api ingestion query workers; do
  docker build -f "services/${svc}/Dockerfile" -t "${svc}:local" services/
  docker tag "${svc}:local" "${REGISTRY}/${svc}:${SHA}"
  docker push "${REGISTRY}/${svc}:${SHA}"
done
```

## 11. Deploy service Helm charts

Update `image.tag` in each `helm/<svc>/values-dev.yaml` to match `SHA`, then:

```bash
cd /home/wvsonp/Turbo-RAG
SHA=$(git rev-parse --short HEAD)
for svc in api ingestion query workers; do
  helm lint "helm/${svc}" -f "helm/${svc}/values-dev.yaml"
  helm upgrade --install "$svc" "helm/${svc}" \
    -f "helm/${svc}/values.yaml" \
    -f "helm/${svc}/values-dev.yaml" \
    --set "image.tag=${SHA}" \
    --namespace platform --create-namespace
done
kubectl get pods -n platform
kubectl run curl-smoke --restart=Never -n platform \
  --image=curlimages/curl:latest -- curl -sf http://api:8080/health
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/curl-smoke -n platform --timeout=60s
kubectl logs curl-smoke -n platform
kubectl delete pod curl-smoke -n platform --ignore-not-found
```

## 12. Deploy Qdrant

```bash
cd /home/wvsonp/Turbo-RAG
helm lint helm/qdrant -f helm/qdrant/values-dev.yaml
helm upgrade --install qdrant helm/qdrant \
  -f helm/qdrant/values.yaml \
  -f helm/qdrant/values-dev.yaml \
  --namespace platform --create-namespace
kubectl wait --for=condition=ready pod/qdrant-0 -n platform --timeout=120s
kubectl get pvc -n platform -l app.kubernetes.io/name=qdrant
kubectl run curl-qdrant --restart=Never -n platform \
  --image=curlimages/curl:latest -- curl -sf http://qdrant:6333/healthz
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/curl-qdrant -n platform --timeout=60s
kubectl logs curl-qdrant -n platform
kubectl delete pod curl-qdrant -n platform --ignore-not-found
```

## 13. Validate Workload Identity

Run after section 11 (Helm charts must include WI annotations from `values-dev.yaml`):

```bash
for sa in api ingestion query workers; do
  kubectl run "wi-check-$sa" --restart=Never -n platform \
    --image=curlimages/curl:latest \
    --overrides="{\"spec\":{\"serviceAccountName\":\"$sa\"}}" \
    -- curl -sf -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
  kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
    "pod/wi-check-$sa" -n platform --timeout=60s
  kubectl logs "wi-check-$sa" -n platform
  kubectl delete pod "wi-check-$sa" -n platform --ignore-not-found
done
kubectl run wi-secret-test --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"api"}}' \
  --command -- sh -c 'gcloud secrets versions access latest --secret=openai-api-key --project=turbo-rag >/dev/null && echo SECRET_ACCESS_OK'
kubectl wait --for=condition=ready pod/wi-secret-test -n platform --timeout=90s
kubectl logs wi-secret-test -n platform
kubectl delete pod wi-secret-test -n platform
```

Then continue with section 14 (Prefect on GKE).

## 14. Deploy Prefect on GKE (2.2)

Requires Helm (`helm repo add prefect https://prefecthq.github.io/prefect-helm`). After Terraform
`module.cloudsql` + `module.iam` include the `prefect` database and `prefect-server-sa-{env}`.

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.cloudsql -target=module.iam

cd /home/wvsonp/Turbo-RAG
helm repo add prefect https://prefecthq.github.io/prefect-helm 2>/dev/null || true
helm repo update prefect

kubectl create namespace prefect --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic prefect-server-postgresql-connection \
  --from-literal=connection-string='postgresql+asyncpg://prefect-server-sa-dev%40turbo-rag.iam@127.0.0.1:5432/prefect' \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap prefect-worker-base-job-template \
  --from-file=baseJobTemplate.json=helm/prefect/base-job-template-dev.json \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f helm/prefect/mlruns-pvc.yaml

helm upgrade --install prefect-server prefect/prefect-server \
  -f helm/prefect/values-server.yaml \
  -f helm/prefect/values-server-dev.yaml \
  --namespace prefect --create-namespace

helm upgrade --install prefect-worker prefect/prefect-worker \
  -f helm/prefect/values-worker.yaml \
  -f helm/prefect/values-worker-dev.yaml \
  --namespace prefect

kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prefect-server -n prefect --timeout=180s
kubectl get pods -n prefect -o wide
```

One-time Cloud SQL grants for new `prefect` database (dev bootstrap — see `docs/history/prefect.md`):

```bash
gcloud sql users set-password postgres --instance=rag-platform-dev \
  --password='Bootstrap-Dev-Only-2026!' --project=turbo-rag
CLOUDSQL_IP="$(cd infra && terraform output -raw cloudsql_private_ip)"
kubectl run db-grant-prefect --restart=Never -n prefect \
  --image=postgres:15-alpine \
  --env="PGPASSWORD=Bootstrap-Dev-Only-2026!" \
  --command -- sh -c "
psql -h ${CLOUDSQL_IP} -U postgres -d prefect -c \"GRANT ALL ON SCHEMA public TO \\\"prefect-server-sa-dev@turbo-rag.iam\\\";\"
psql -h ${CLOUDSQL_IP} -U postgres -d prefect -c \"GRANT cloudsqlsuperuser TO \\\"prefect-server-sa-dev@turbo-rag.iam\\\";\"
psql -h ${CLOUDSQL_IP} -U postgres -d rag_metadata -c \"GRANT cloudsqlsuperuser TO \\\"workers-sa-dev@turbo-rag.iam\\\";\"
echo GRANTS_OK"
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/db-grant-prefect -n prefect --timeout=90s
kubectl logs db-grant-prefect -n prefect
kubectl delete pod db-grant-prefect -n prefect --ignore-not-found
kubectl delete pod -n prefect -l app.kubernetes.io/name=prefect-server
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prefect-server -n prefect --timeout=120s
```

Then continue with section 15 (Ingestion flow).

## 15. Deploy ingestion flow (2.3)

Build context is `services/` (shared `rag_platform` package). After section 10
push and section 14 Prefect:

```bash
cd /home/wvsonp/Turbo-RAG
set -euo pipefail
SHA=$(git rev-parse --short HEAD)
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"

# Refresh base job template (Cloud SQL proxy sidecar for flow jobs)
kubectl create configmap prefect-worker-base-job-template \
  --from-file=baseJobTemplate.json=helm/prefect/base-job-template-dev.json \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -

# Register Prefect deployment (uses workers image with flow code baked in)
WORKERS_IMAGE="${REGISTRY}/workers:${SHA}" \
  PREFECT_API_URL=http://prefect-server.prefect.svc.cluster.local:4200/api \
  bash scripts/register-ingest-deployment.sh

# Redeploy ingestion (dispatcher) + workers with new image tag
for svc in ingestion workers; do
  helm upgrade --install "$svc" "helm/${svc}" \
    -f "helm/${svc}/values.yaml" \
    -f "helm/${svc}/values-dev.yaml" \
    --set "image.tag=${SHA}" \
    --namespace platform --create-namespace
done
kubectl rollout status deployment/ingestion -n platform --timeout=120s
kubectl logs -n platform deploy/ingestion --tail=30
```

End-to-end validation (do **not** use `--auto-ack` on `ingestion-uploads-sub`):

```bash
echo "ingest-test-$(date +%s)" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag

kubectl logs -n platform deploy/ingestion -f --tail=50
kubectl get jobs -n prefect
kubectl get pods -n prefect -l prefect.io/flow-run-id

kubectl run qdrant-count --restart=Never -n platform \
  --image=curlimages/curl:latest \
  -- curl -sf -X POST http://qdrant:6333/collections/rag_chunks_dev/points/count \
  -H 'Content-Type: application/json' -d '{"exact":true}'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/qdrant-count -n platform --timeout=60s
kubectl logs qdrant-count -n platform
kubectl delete pod qdrant-count -n platform --ignore-not-found
```

Then continue with section 16 (Chunking experiments).

## 16. Chunking experiments + MLflow (2.4)

After section 15 (ingestion flow deployed), upload the fixed test document,
register the experiment deployment, and run it:

```bash
cd /home/wvsonp/Turbo-RAG
set -euo pipefail
SHA=$(git rev-parse --short HEAD)
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"

kubectl apply -f helm/prefect/mlruns-pvc.yaml

kubectl create configmap prefect-worker-base-job-template \
  --from-file=baseJobTemplate.json=helm/prefect/base-job-template-dev.json \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -

bash scripts/upload-chunking-sample.sh

WORKERS_IMAGE="${REGISTRY}/workers:${SHA}" \
  PREFECT_API_URL=http://prefect-server.prefect.svc.cluster.local:4200/api \
  bash scripts/register-chunking-experiment-deployment.sh

# Trigger experiment (no Pub/Sub)
kubectl run prefect-run-chunking-experiment --restart=Never -n prefect \
  --image="${REGISTRY}/workers:${SHA}" \
  --overrides="$(cat <<EOF
{
  "spec": {
    "serviceAccountName": "workers",
    "containers": [{
      "name": "c",
      "image": "${REGISTRY}/workers:${SHA}",
      "env": [
        {"name": "PREFECT_API_URL", "value": "http://prefect-server.prefect.svc.cluster.local:4200/api"},
        {"name": "MLFLOW_TRACKING_URI", "value": "file:/mlruns"}
      ],
      "command": ["sh", "-c", "prefect deployment run chunking-experiment/chunking-experiment && sleep 120"]
    }]
  }
}
EOF
)"
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/prefect-run-chunking-experiment -n prefect --timeout=180s || true
kubectl logs prefect-run-chunking-experiment -n prefect
kubectl delete pod prefect-run-chunking-experiment -n prefect --ignore-not-found

kubectl get jobs -n prefect
kubectl get pods -n prefect -l prefect.io/flow-run-id

# Prove durable mlruns on PVC (survives job pod exit)
kubectl run mlruns-ls --restart=Never -n prefect \
  --image=busybox:1.36 \
  --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.36","command":["sh","-c","ls -la /mlruns && find /mlruns -maxdepth 4 -type f | head -20 && echo MLRUNS_OK"],"volumeMounts":[{"name":"mlruns","mountPath":"/mlruns"}]}],"volumes":[{"name":"mlruns","persistentVolumeClaim":{"claimName":"mlruns-pvc"}}]}}'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/mlruns-ls -n prefect --timeout=60s
kubectl logs mlruns-ls -n prefect
kubectl delete pod mlruns-ls -n prefect --ignore-not-found
```

Local UI (copy mlruns from cluster first if needed):

```bash
mlflow ui --backend-store-uri file:./mlruns --port 5000
```

Production chunker default is `CHUNKER=fixed` (see `helm/workers/values-*.yaml`).
Compare the three MLflow runs before switching to `recursive` or `semantic`.

### 2.5 DLQ + idempotency (deploy + validate)

Rebuild and deploy ingestion + workers (see [`docs/history/ingestion.md`](docs/history/ingestion.md) § 2.5), then:

```bash
gcloud pubsub subscriptions describe ingestion-uploads-sub \
  --project=turbo-rag --format="yaml(deadLetterPolicy)"

kubectl run metrics-curl --restart=Never -n platform --image=curlimages/curl:8.5.0 \
  --command -- curl -sf http://ingestion.platform.svc.cluster.local:8080/metrics
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/metrics-curl -n platform --timeout=60s
kubectl logs metrics-curl -n platform
kubectl delete pod metrics-curl -n platform --ignore-not-found
# Expected: ingestion_runs_total, ingestion_failures_total, dlq_undelivered_messages
```

Then continue with section 17 (Query API skeleton).

## 17. Query API skeleton (3.1)

Build, push, and deploy the query service with the retrieval stub:

```bash
cd /home/wvsonp/Turbo-RAG
SHA=$(git rev-parse --short HEAD)
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"

docker build -f services/query/Dockerfile -t query:local services/
docker tag query:local "${REGISTRY}/query:${SHA}"
docker push "${REGISTRY}/query:${SHA}"

helm upgrade --install query helm/query \
  -f helm/query/values.yaml \
  -f helm/query/values-dev.yaml \
  --set "image.tag=${SHA}" \
  --namespace platform --create-namespace

kubectl rollout status deployment/query -n platform --timeout=120s
kubectl get pod -n platform -l app.kubernetes.io/name=query \
  -o jsonpath='{.items[0].spec.nodeSelector}{"\n"}'
# Expected nodeSelector key: cloud.google.com/gke-nodepool=application
```

Validate `POST /query` and OpenAPI:

```bash
kubectl run query-smoke --restart=Never -n platform --image=curlimages/curl:8.5.0 \
  --command -- sh -c 'curl -sf http://query.platform.svc.cluster.local:8080/health \
  && curl -sf -X POST http://query.platform.svc.cluster.local:8080/query \
  -H "Content-Type: application/json" -d "{\"query\":\"What is RAG?\",\"top_k\":5}" \
  && curl -sf -o /dev/null -w "%{http_code}" http://query.platform.svc.cluster.local:8080/docs'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/query-smoke -n platform --timeout=60s
kubectl logs query-smoke -n platform
kubectl delete pod query-smoke -n platform --ignore-not-found
# Expected: health JSON, query response with stub=true and empty chunks, docs HTTP 200
```

Then continue with section 18 (Hybrid search + RRF).

## 18. Hybrid search + RRF (3.2)

After workers/query images include FastEmbed-backed sparse encoding (`SPARSE_MODEL_NAME`
defaults to `Qdrant/bm25`), recreate the dev collection. Dense-only data and
pre-FastEmbed custom sparse vectors are incompatible, so re-ingest documents
before validating query retrieval:

```bash
cd /home/wvsonp/Turbo-RAG
SHA=$(git rev-parse --short HEAD)
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"

# Rebuild workers + ingestion (workers owns FastEmbed sparse upserts)
for svc in ingestion workers; do
  docker build -f "services/${svc}/Dockerfile" -t "${svc}:local" services/
  docker tag "${svc}:local" "${REGISTRY}/${svc}:${SHA}"
  docker push "${REGISTRY}/${svc}:${SHA}"
  helm upgrade --install "$svc" "helm/${svc}" \
    -f "helm/${svc}/values.yaml" \
    -f "helm/${svc}/values-dev.yaml" \
    --set "image.tag=${SHA}" \
    --namespace platform
done
kubectl rollout status deployment/ingestion -n platform --timeout=120s

# Re-register Prefect ingest deployment (workers image changed)
# If this namespace is missing, run section 14 before continuing.
kubectl create configmap prefect-worker-base-job-template \
  --from-file=baseJobTemplate.json=helm/prefect/base-job-template-dev.json \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -
WORKERS_IMAGE="${REGISTRY}/workers:${SHA}" \
  PREFECT_API_URL=http://prefect-server.prefect.svc.cluster.local:4200/api \
  bash scripts/register-ingest-deployment.sh

# Drop old dense-only or pre-FastEmbed custom-sparse collection
kubectl run qdrant-drop-collection --restart=Never -n platform \
  --image=curlimages/curl:8.5.0 \
  --command -- curl -sf -X DELETE \
  "http://qdrant.platform.svc.cluster.local:6333/collections/rag_chunks_dev"
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/qdrant-drop-collection -n platform --timeout=60s
kubectl delete pod qdrant-drop-collection -n platform --ignore-not-found

# Re-ingest sample documents (creates hybrid collection on first upsert)
echo "hybrid-test-$(date +%s)" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag
kubectl logs -n platform deploy/ingestion -f --tail=50

bash scripts/upload-chunking-sample.sh
gcloud storage cp gs://rag-ingestion-dev/experiments/chunking-sample.txt \
  gs://rag-ingestion-dev/incoming/chunking-sample.txt --project=turbo-rag

kubectl run qdrant-count --restart=Never -n platform \
  --image=curlimages/curl:8.5.0 \
  --command -- curl -sf -X POST http://qdrant:6333/collections/rag_chunks_dev/points/count \
  -H 'Content-Type: application/json' -d '{"exact":true}'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/qdrant-count -n platform --timeout=60s
kubectl logs qdrant-count -n platform
kubectl delete pod qdrant-count -n platform --ignore-not-found

# Deploy query service with hybrid retrieval
docker build -f services/query/Dockerfile -t query:local services/
docker tag query:local "${REGISTRY}/query:${SHA}"
docker push "${REGISTRY}/query:${SHA}"

helm upgrade --install query helm/query \
  -f helm/query/values.yaml \
  -f helm/query/values-dev.yaml \
  --set "image.tag=${SHA}" \
  --namespace platform

kubectl rollout status deployment/query -n platform --timeout=120s
kubectl run query-hybrid-smoke --restart=Never -n platform --image=curlimages/curl:8.5.0 \
  --command -- sh -c 'curl -sf http://query.platform.svc.cluster.local:8080/ready \
  && curl -sf -X POST http://query.platform.svc.cluster.local:8080/query \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"What is retrieval-augmented generation?\",\"top_k\":5}"'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/query-hybrid-smoke -n platform --timeout=120s
kubectl logs query-hybrid-smoke -n platform
kubectl delete pod query-hybrid-smoke -n platform --ignore-not-found
# Expected: stub=false, non-empty chunks with text and RRF scores from FastEmbed sparse vectors
```

Run shared retrieval unit tests locally:

```bash
cd /home/wvsonp/Turbo-RAG
PYTHONPATH=services/shared python3 -m pytest \
  services/shared/tests/test_rrf.py \
  services/shared/tests/test_sparse.py \
  -v
# Or without pytest:
PYTHONPATH=services/shared python3 -c "from rag_platform.rrf import reciprocal_rank_fusion; assert reciprocal_rank_fusion([['a'],['b']], k=60)"
```

Then continue with
[`docs/plan/phase-3-query-retrieval/3.3-reranker.md`](docs/plan/phase-3-query-retrieval/3.3-reranker.md).
