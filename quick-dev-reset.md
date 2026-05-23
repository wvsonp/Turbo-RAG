# Quick Dev Reset

Use this when the dev GCP platform was destroyed and you want to recreate the
current project state so work can continue at **Phase 2.2 Prefect on GKE**.

Current target state:

- Project: `turbo-rag`
- Region: `us-central1`
- Terraform env: `infra/environments/dev.tfvars`
- Recreated stack: network, GKE, Artifact Registry, Cloud SQL, Secret Manager (containers + accessor SA), GCS ingestion bucket + Pub/Sub (`module.pubsub`), per-service Workload Identity with ingestion IAM (`module.iam`)
- Cluster addons: Secret Store CSI driver + GCP provider (kubectl manifests)
- Helm: api, ingestion, query, workers (WI annotations), qdrant
- Next task after reset: `docs/plan/phase-2-ingestion/2.2-prefect-on-gke.md`

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

kubectl run cloudsql-smoke --rm -i --restart=Never \
  --env="CLOUDSQL_PRIVATE_IP=${CLOUDSQL_PRIVATE_IP}" \
  --image=postgres:15-alpine \
  --command -- sh -c 'nc -zv "$CLOUDSQL_PRIVATE_IP" 5432'
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
  --project=turbo-rag --format="value(ackDeadlineSeconds)"
# Expected: 600
```

WI proof (ingestion KSA lists bucket):

```bash
kubectl run wi-gcs-ingestion --rm -i --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"ingestion"}}' \
  -- gcloud storage ls gs://rag-ingestion-dev/incoming/ --project=turbo-rag
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
  docker build -t "${svc}:local" "services/${svc}"
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
kubectl run curl-smoke --rm -i --restart=Never -n platform \
  --image=curlimages/curl:latest -- curl -sf http://api:8080/health
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
kubectl run curl-qdrant --rm -i --restart=Never -n platform \
  --image=curlimages/curl:latest -- curl -sf http://qdrant:6333/healthz
```

## 13. Validate Workload Identity

Run after section 11 (Helm charts must include WI annotations from `values-dev.yaml`):

```bash
for sa in api ingestion query workers; do
  kubectl run "wi-check-$sa" --rm -i --restart=Never -n platform \
    --image=curlimages/curl:latest \
    --overrides="{\"spec\":{\"serviceAccountName\":\"$sa\"}}" \
    -- curl -sf -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
done
kubectl run wi-secret-test --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"api"}}' \
  --command -- sh -c 'gcloud secrets versions access latest --secret=openai-api-key --project=turbo-rag >/dev/null && echo SECRET_ACCESS_OK'
kubectl wait --for=condition=ready pod/wi-secret-test -n platform --timeout=90s
kubectl logs wi-secret-test -n platform
kubectl delete pod wi-secret-test -n platform
```

Then continue with:

[`docs/plan/phase-2-ingestion/2.2-prefect-on-gke.md`](docs/plan/phase-2-ingestion/2.2-prefect-on-gke.md)

Useful status docs:

- `docs/STATUS.md`
- `README.md`
- `docs/history/IaC.md`
- `docs/history/gke.md`
- `docs/history/artifact_registry.md`
- `docs/history/cloudsql.md`
- `docs/history/secret_manager.md`
- `docs/history/helm.md`
- `docs/history/qdrant.md`
- `docs/history/iam.md`
- `docs/history/pubsub.md`
