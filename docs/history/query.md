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
