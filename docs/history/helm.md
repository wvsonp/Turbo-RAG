# Helm charts (1.8)

## 2026-05-22 — Service charts on dev GKE

**What:** Customized `helm/{api,ingestion,query,workers}` from `helm create` defaults: Artifact Registry image repos, port 8080, `/health` and `/ready` probes, required `image.tag` in templates, `values-dev.yaml` / `values-prod.yaml`. Deployed all four releases to namespace `platform`.

**Why:** Completes Phase 1.8 so skeleton services run on GKE with environment-specific values before Qdrant (1.9) and Workload Identity annotations (1.10).

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG
SHA=$(git rev-parse --short HEAD)

# Lint
for svc in api ingestion query workers; do
  helm lint "helm/${svc}" -f "helm/${svc}/values-dev.yaml"
done

# Push images (tag must exist in registry before deploy)
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"
for svc in api ingestion query workers; do
  docker build -t "${svc}:local" "services/${svc}"
  docker tag "${svc}:local" "${REGISTRY}/${svc}:${SHA}"
  docker push "${REGISTRY}/${svc}:${SHA}"
done

# Install
for svc in api ingestion query workers; do
  helm upgrade --install "$svc" "helm/${svc}" -f "helm/${svc}/values-dev.yaml" \
    --namespace platform --create-namespace
done

kubectl get pods -n platform
kubectl run curl-smoke --rm -i --restart=Never -n platform \
  --image=curlimages/curl:latest -- curl -sf http://api:8080/health
```

**Note:** `values-dev.yaml` may pin a SHA; after new commits, bump `image.tag` or use `--set image.tag=$SHA` on upgrade. ImagePullBackOff means the tag is missing in Artifact Registry.
