# Qdrant on GKE (1.9)

## 2026-05-22 — StatefulSet chart + dev deploy

**What:** Added `helm/qdrant/` with StatefulSet, `volumeClaimTemplates` (`qdrant-storage`, `standard-rwo`, 10Gi), ClusterIP service on 6333/6334, and env vars to keep storage/snapshots on the PVC. Deployed release `qdrant` to namespace `platform`.

**Why:** Vector store must persist across pod restarts before Phase 2 ingestion writes embeddings to Qdrant.

**PVC name (Phase 6.3 DR):** `qdrant-storage-qdrant-0`

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG

helm lint helm/qdrant -f helm/qdrant/values-dev.yaml
helm upgrade --install qdrant helm/qdrant \
  -f helm/qdrant/values.yaml \
  -f helm/qdrant/values-dev.yaml \
  --namespace platform --create-namespace

kubectl get pods,pvc,svc -n platform -l app.kubernetes.io/name=qdrant

# Health (in-cluster)
kubectl run curl-qdrant --rm -i --restart=Never -n platform \
  --image=curlimages/curl:latest -- curl -sf http://qdrant:6333/healthz

# Persistence smoke: create collection, restart pod, verify collection remains
kubectl run qdrant-setup --rm -i --restart=Never -n platform \
  --image=curlimages/curl:latest -- \
  curl -sf -X PUT 'http://qdrant:6333/collections/persist-test' \
  -H 'Content-Type: application/json' \
  -d '{"vectors":{"size":4,"distance":"Cosine"}}'

kubectl delete pod qdrant-0 -n platform
kubectl wait --for=condition=ready pod/qdrant-0 -n platform --timeout=120s

kubectl run qdrant-check --rm -i --restart=Never -n platform \
  --image=curlimages/curl:latest -- \
  curl -sf 'http://qdrant:6333/collections/persist-test'
```

**Note:** Qdrant image is `qdrant/qdrant:v1.13.4` from Docker Hub (not Artifact Registry). Set `QDRANT__STORAGE__SNAPSHOTS_PATH` under the PVC mount or the container crashes trying to write `./snapshots/tmp` under root-owned `/qdrant`.
