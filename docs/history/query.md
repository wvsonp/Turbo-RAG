# Query service

## 2026-05-30 — 3.1 Query API skeleton

**What:** Added `POST /query` with Pydantic `QueryRequest` / `QueryResponse` models in `services/query/models.py`; async handler returns schema-valid stub (`stub=true`, empty `chunks` and `answer`); OpenAPI at `/docs`. Helm query chart pins pods to the `application` node pool and supports `env` in the deployment template.

**Why:** Locks the HTTP contract and deployment path before hybrid search (3.2), reranking, auth, and SSE streaming.

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG
SHA=$(git rev-parse --short HEAD)
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"

docker build -t query:local services/query
docker tag query:local "${REGISTRY}/query:${SHA}"
docker push "${REGISTRY}/query:${SHA}"

helm upgrade --install query helm/query \
  -f helm/query/values.yaml -f helm/query/values-dev.yaml \
  --set "image.tag=${SHA}" --namespace platform

# Local smoke (no cluster)
python3 -m pip install -r services/query/requirements.txt
python3 -c "
from fastapi.testclient import TestClient
import sys; sys.path.insert(0, 'services/query')
import main
c = TestClient(main.app)
assert c.post('/query', json={'query': 'test'}).json()['stub'] is True
print('OK')
"

# In-cluster
kubectl run query-smoke --restart=Never -n platform --image=curlimages/curl:8.5.0 \
  --command -- curl -sf -X POST http://query.platform.svc.cluster.local:8080/query \
  -H 'Content-Type: application/json' -d '{"query":"What is RAG?"}'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/query-smoke -n platform --timeout=60s
kubectl logs query-smoke -n platform
kubectl delete pod query-smoke -n platform --ignore-not-found
```

## 2026-05-31 — 3.2 hybrid retrieval architecture decision

**What:** Chose Qdrant dense + Qdrant sparse for 3.2 hybrid retrieval. BM25 sparse vectors will be generated in application code for both ingestion and query-time retrieval; full chunk text will be stored in Qdrant payloads; dev data must be re-ingested after the dense+sparse collection schema change.

**Why:** Keeps dense and sparse retrieval in one operational store, aligns with the roadmap's Qdrant hybrid-search direction, and avoids introducing a sidecar BM25 index before the platform needs that extra moving part.

**Commands:**
```bash
# Documentation-only decision; no runtime command required.
```

## 2026-05-31 — 3.2 Hybrid search + RRF implementation

**What:** Added shared `BM25SparseEncoder` and `reciprocal_rank_fusion` in `services/shared/rag_platform/`; updated `workers/qdrant/store.py` for dense+sparse collection schema with full chunk `text` in payloads; implemented `HybridRetriever` in `services/query/retrieval.py` (Vertex embed → dense search → sparse search → RRF → `RetrievedChunk` list with per-step latency logs); query `/ready` validates hybrid schema; RRF unit tests in `services/shared/tests/test_rrf.py`; collection recreate script at `scripts/recreate-qdrant-hybrid-collection.sh`.

**Why:** Delivers end-to-end hybrid retrieval in one Qdrant store per the 3.2 architecture decision, with explicit RRF and timing hooks for 3.6 OTel traces and 3.3 reranking.

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG

# Unit tests (RRF)
PYTHONPATH=services/shared python3 -c "
from rag_platform.rrf import reciprocal_rank_fusion
assert reciprocal_rank_fusion([['a','b'],['b','a']], k=60)[0][0] in ('a','b')
print('OK')
"

# Build query image (context = services/)
docker build -f query/Dockerfile -t query:local services/

# After deploy: drop old collection, re-ingest, query
bash scripts/recreate-qdrant-hybrid-collection.sh   # from cluster context
echo "test" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag

kubectl run query-hybrid-smoke --restart=Never -n platform --image=curlimages/curl:8.5.0 \
  --command -- curl -sf -X POST http://query.platform.svc.cluster.local:8080/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is retrieval-augmented generation?","top_k":5}'
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/query-hybrid-smoke -n platform --timeout=120s
kubectl logs query-hybrid-smoke -n platform
kubectl delete pod query-hybrid-smoke -n platform --ignore-not-found
```

## 2026-05-31 — 3.2 Sparse encoder FastEmbed migration

**What:** Replaced the custom BM25-style hash sparse encoder with a shared `FastEmbedSparseEncoder` adapter using `Qdrant/bm25`. The ingestion flow now calls the document sparse embedding path from workers, query retrieval calls the query sparse embedding path, `SPARSE_MODEL_NAME` controls the model name, and `query` / `workers` install `fastembed`.

**Why:** The maintained FastEmbed encoder removes custom tokenization and hash weighting logic while staying aligned with Qdrant sparse vectors and the existing dense+sparse collection design. Existing pre-FastEmbed sparse vectors must be dropped and re-ingested because sparse token IDs/weights are not compatible with the custom encoder.

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG

# Syntax validation for changed Python modules.
python3 -m compileall services/shared/rag_platform services/query services/workers/qdrant services/shared/tests
```
