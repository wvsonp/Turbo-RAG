# Install Guide — Full first-time bring-up

Complete clean install of the dev platform from an empty project to a working
hybrid-RAG stack. For destroy → restore on existing Terraform state, use
[`quick-dev-reset.md`](quick-dev-reset.md) instead.

Principles: APIs enabled before Terraform; **one full `terraform apply`** (no
targeted applies); build each image **once**; no collection drops or
query-skeleton step. Smoke checks use create → wait `Completed` → `logs` →
delete (never `kubectl run --rm -i`). Run from WSL with `gcloud`, `terraform`,
`kubectl`, `helm`, `docker` (+ GKE auth plugin) installed.

## 1. Authenticate

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project turbo-rag
gcloud config set compute/region us-central1
```

## 2. Enable APIs (before Terraform — PSA fails otherwise)

```bash
gcloud services enable \
  container.googleapis.com compute.googleapis.com servicenetworking.googleapis.com \
  sqladmin.googleapis.com pubsub.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com storage.googleapis.com aiplatform.googleapis.com \
  --project=turbo-rag
```

## 3. Verify (or create) the Terraform state bucket

```bash
gcloud storage buckets describe gs://rag-platform-tf-state --project=turbo-rag \
  || gcloud storage buckets create gs://rag-platform-tf-state \
       --project=turbo-rag --location=us-central1 --uniform-bucket-level-access
```

## 4. Apply infrastructure (single full apply)

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform init
terraform validate
terraform apply -var-file=environments/dev.tfvars
```

Expected outputs: `artifact_registry_url`, `cloudsql_connection_name`,
`cloudsql_private_ip` (from `10.16.0.0/16`), `gke_cluster_name=rag-platform-dev`,
`secret_accessor_gcp_sa_email`, `ingestion_bucket_name=rag-ingestion-dev`,
`ingestion_topic_name=ingestion-uploads`, `ingestion_subscription_name=ingestion-uploads-sub`.

## 5. Get GKE credentials + shared env

```bash
gcloud container clusters get-credentials rag-platform-dev --region us-central1 --project turbo-rag
kubectl wait --for=condition=ready node --all --timeout=600s
kubectl get nodes -L cloud.google.com/gke-nodepool   # system + application Ready; worker may be 0

cd /home/wvsonp/Turbo-RAG
export SHA=$(git rev-parse --short HEAD)
export REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"
export PREFECT_API_URL="http://prefect-server.prefect.svc.cluster.local:4200/api"
echo "SHA=${SHA}"
```

## 6. Validate Artifact Registry (optional)

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
gcloud artifacts repositories describe rag-platform --location=us-central1 --project=turbo-rag
```

## 7. Validate Cloud SQL (optional)

```bash
gcloud sql databases list --instance=rag-platform-dev --project=turbo-rag   # rag_metadata, langfuse, mlflow, prefect
CLOUDSQL_PRIVATE_IP="$(cd infra && terraform output -raw cloudsql_private_ip)"
kubectl run cloudsql-smoke --restart=Never --env="CLOUDSQL_PRIVATE_IP=${CLOUDSQL_PRIVATE_IP}" \
  --image=postgres:15-alpine --command -- sh -c 'nc -zv "$CLOUDSQL_PRIVATE_IP" 5432'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/cloudsql-smoke --timeout=60s
kubectl logs cloudsql-smoke; kubectl delete pod cloudsql-smoke --ignore-not-found
```

## 8. Secret value + CSI drivers

Terraform created the secret container; add the value (never commit), then
install the cluster-scoped CSI drivers via kubectl:

```bash
echo -n 'your-dev-openai-key' | gcloud secrets versions add openai-api-key --project=turbo-rag --data-file=-

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

## 9. Validate GCS → Pub/Sub (optional)

```bash
echo "test-$(date +%s)" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag
sleep 5
gcloud pubsub subscriptions pull ingestion-uploads-test-sub --auto-ack --limit=1 --project=turbo-rag
gcloud pubsub subscriptions describe ingestion-uploads-sub \
  --project=turbo-rag --format="yaml(deadLetterPolicy,ackDeadlineSeconds)"
# Expect: deadLetterTopic ingestion-uploads-dlq, maxDeliveryAttempts 5, ackDeadlineSeconds 600
```

## 10. Build + push all service images (once)

Build context is `services/`; Dockerfiles referenced from repo root.

```bash
cd /home/wvsonp/Turbo-RAG
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
for svc in api ingestion query workers; do
  docker build -f "services/${svc}/Dockerfile" -t "${svc}:local" services/
  docker tag "${svc}:local" "${REGISTRY}/${svc}:${SHA}"
  docker push "${REGISTRY}/${svc}:${SHA}"
done
```

## 11. Deploy service charts

```bash
for svc in api ingestion query workers; do
  helm upgrade --install "$svc" "helm/${svc}" \
    -f "helm/${svc}/values.yaml" -f "helm/${svc}/values-dev.yaml" \
    --set "image.tag=${SHA}" --namespace platform --create-namespace
done
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=api -n platform --timeout=120s
kubectl run curl-smoke --restart=Never -n platform --image=curlimages/curl:latest \
  -- curl -sf http://api:8080/health
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/curl-smoke -n platform --timeout=60s
kubectl logs curl-smoke -n platform; kubectl delete pod curl-smoke -n platform --ignore-not-found
```

`query` and `ingestion` may stay NotReady until §12 (Qdrant) and §14–§15
(Prefect) — expected.

## 12. Qdrant

```bash
helm upgrade --install qdrant helm/qdrant \
  -f helm/qdrant/values.yaml -f helm/qdrant/values-dev.yaml \
  --namespace platform --create-namespace
kubectl wait --for=condition=ready pod/qdrant-0 -n platform --timeout=120s

kubectl run curl-qdrant --restart=Never -n platform --image=curlimages/curl:latest \
  -- curl -sf http://qdrant:6333/healthz
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/curl-qdrant -n platform --timeout=60s
kubectl logs curl-qdrant -n platform; kubectl delete pod curl-qdrant -n platform --ignore-not-found
```

## 13. WI check (optional)

```bash
kubectl run wi-secret-test --restart=Never -n platform --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"api"}}' \
  --command -- sh -c 'gcloud secrets versions access latest --secret=openai-api-key --project=turbo-rag >/dev/null && echo SECRET_ACCESS_OK'
kubectl wait --for=condition=ready pod/wi-secret-test -n platform --timeout=90s
kubectl logs wi-secret-test -n platform; kubectl delete pod wi-secret-test -n platform
```

## 14. Prefect (server + worker)

```bash
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
  -f helm/prefect/values-server.yaml -f helm/prefect/values-server-dev.yaml \
  --namespace prefect --create-namespace
helm upgrade --install prefect-worker prefect/prefect-worker \
  -f helm/prefect/values-worker.yaml -f helm/prefect/values-worker-dev.yaml \
  --namespace prefect
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prefect-server -n prefect --timeout=180s
```

**Prefect UI (optional):** `values-server.yaml` sets `prefectUiApiUrl: /api` so the dashboard works over port-forward. If the page is blank or shows a cluster DNS API error, redeploy the server chart (above) and restart the server pod, then:

```bash
kubectl port-forward -n prefect svc/prefect-server 4200:4200
```

Open http://localhost:4200 (hard refresh). API health: `curl -sf http://localhost:4200/api/health`.

One-time DB grants (dev bootstrap; prompted password, not committed):

```bash
read -rs -p "Temp dev postgres password: " PG_BOOTSTRAP_PW; echo
gcloud sql users set-password postgres --instance=rag-platform-dev \
  --password="${PG_BOOTSTRAP_PW}" --project=turbo-rag
CLOUDSQL_IP="$(cd infra && terraform output -raw cloudsql_private_ip)"
kubectl run db-grant-prefect --restart=Never -n prefect --image=postgres:15-alpine \
  --env="PGPASSWORD=${PG_BOOTSTRAP_PW}" --command -- sh -c "
psql -h ${CLOUDSQL_IP} -U postgres -d prefect -c \"GRANT ALL ON SCHEMA public TO \\\"prefect-server-sa-dev@turbo-rag.iam\\\";\"
psql -h ${CLOUDSQL_IP} -U postgres -d prefect -c \"GRANT cloudsqlsuperuser TO \\\"prefect-server-sa-dev@turbo-rag.iam\\\";\"
psql -h ${CLOUDSQL_IP} -U postgres -d rag_metadata -c \"GRANT cloudsqlsuperuser TO \\\"workers-sa-dev@turbo-rag.iam\\\";\"
echo GRANTS_OK"
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/db-grant-prefect -n prefect --timeout=90s
kubectl logs db-grant-prefect -n prefect; kubectl delete pod db-grant-prefect -n prefect --ignore-not-found
kubectl delete pod -n prefect -l app.kubernetes.io/name=prefect-server
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prefect-server -n prefect --timeout=120s
unset PG_BOOTSTRAP_PW
```

## 15. Ingestion flow (register + reconnect dispatcher)

`ingestion` from §11 started before Prefect, so its dispatcher crashed — roll it out again.

```bash
kubectl create configmap prefect-worker-base-job-template \
  --from-file=baseJobTemplate.json=helm/prefect/base-job-template-dev.json \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -
# Applies kubernetes work-pool base job template (Cloud SQL proxy sidecar + mlruns PVC).
WORKERS_IMAGE="${REGISTRY}/workers:${SHA}" PREFECT_API_URL="${PREFECT_API_URL}" \
  bash scripts/register-ingest-deployment.sh
kubectl rollout restart deployment/ingestion -n platform
kubectl rollout status deployment/ingestion -n platform --timeout=120s
```

Validate (no `--auto-ack` on the main sub):

```bash
echo "ingest-test-$(date +%s)" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag
sleep 30; kubectl get jobs -n prefect
kubectl run qdrant-count --restart=Never -n platform --image=curlimages/curl:latest \
  -- curl -sf -X POST http://qdrant:6333/collections/rag_chunks_dev/points/count \
  -H 'Content-Type: application/json' -d '{"exact":true}'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/qdrant-count -n platform --timeout=60s
kubectl logs qdrant-count -n platform; kubectl delete pod qdrant-count -n platform --ignore-not-found
```

## 16. Chunking experiments (optional)

```bash
kubectl apply -f helm/prefect/mlruns-pvc.yaml
bash scripts/upload-chunking-sample.sh
WORKERS_IMAGE="${REGISTRY}/workers:${SHA}" PREFECT_API_URL="${PREFECT_API_URL}" \
  bash scripts/register-chunking-experiment-deployment.sh
kubectl run prefect-run-chunking --restart=Never -n prefect --image="${REGISTRY}/workers:${SHA}" \
  --overrides="{\"spec\":{\"serviceAccountName\":\"workers\",\"containers\":[{\"name\":\"c\",\"image\":\"${REGISTRY}/workers:${SHA}\",\"env\":[{\"name\":\"PREFECT_API_URL\",\"value\":\"${PREFECT_API_URL}\"},{\"name\":\"MLFLOW_TRACKING_URI\",\"value\":\"file:/mlruns\"}],\"command\":[\"prefect\",\"deployment\",\"run\",\"chunking-experiment/chunking-experiment\",\"--watch\"]}]}}"
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/prefect-run-chunking -n prefect --timeout=300s
kubectl logs prefect-run-chunking -n prefect; kubectl delete pod prefect-run-chunking -n prefect --ignore-not-found
```

If Prefect rejects `--watch`, drop it and poll `kubectl get jobs -n prefect -w`.
Prod default stays `CHUNKER=fixed`; compare MLflow runs before changing.

## 17. Hybrid query (validate — already deployed in §11)

```bash
kubectl rollout status deployment/query -n platform --timeout=120s
kubectl run query-hybrid-smoke --restart=Never -n platform --image=curlimages/curl:8.5.0 \
  --command -- sh -c 'curl -sf http://query.platform.svc.cluster.local:8080/ready \
  && curl -sf -X POST http://query.platform.svc.cluster.local:8080/query \
  -H "Content-Type: application/json" -d "{\"query\":\"What is retrieval-augmented generation?\",\"top_k\":5}"'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/query-hybrid-smoke -n platform --timeout=120s
kubectl logs query-hybrid-smoke -n platform; kubectl delete pod query-hybrid-smoke -n platform --ignore-not-found
# Expect: stub=false, non-empty chunks with RRF scores. If 503/empty, ingest a doc (§15) first.
```

Next: [`docs/plan/phase-3-query-retrieval/3.3-reranker.md`](docs/plan/phase-3-query-retrieval/3.3-reranker.md).

## Rebuild one service (only if code changed)

```bash
export SHA=$(git rev-parse --short HEAD)
docker build -f "services/${SVC}/Dockerfile" -t "${SVC}:local" services/
docker tag "${SVC}:local" "${REGISTRY}/${SVC}:${SHA}"; docker push "${REGISTRY}/${SVC}:${SHA}"
helm upgrade --install "${SVC}" "helm/${SVC}" \
  -f "helm/${SVC}/values.yaml" -f "helm/${SVC}/values-dev.yaml" \
  --set "image.tag=${SHA}" --namespace platform
```
