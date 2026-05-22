# 1.7 Service skeletons

## What was done

Created minimal FastAPI skeleton images for all four services: `api`, `ingestion`, `query`, `workers`.

Each service directory (`services/<name>/`) contains:

- `requirements.txt` — `fastapi>=0.110.0`, `uvicorn[standard]>=0.29.0`
- `main.py` — identical across all services; reads `SERVICE_NAME` from env; exposes `/health`, `/ready`, `/metrics`
- `Dockerfile` — multi-stage Python 3.11-slim build; non-root `appuser`; only `ENV SERVICE_NAME` differs per service

## Why it mattered

Provides buildable, pushable container images before any RAG business logic exists, so Helm charts and GKE deployments (1.8+) can wire up the platform endpoints immediately.

## Commands that worked

```bash
# Build
for svc in api ingestion query workers; do
  docker build -t "${svc}:local" "services/${svc}"
done

# Smoke test
docker run --rm -d --name test-api -p 8080:8080 api:local
sleep 2
curl -sf localhost:8080/health && curl -sf localhost:8080/ready
docker stop test-api

# Push
gcloud auth configure-docker us-central1-docker.pkg.dev
REGISTRY="us-central1-docker.pkg.dev/turbo-rag/rag-platform"
SHA=$(git rev-parse --short HEAD)
for svc in api ingestion query workers; do
  docker tag "${svc}:local" "${REGISTRY}/${svc}:${SHA}"
  docker push "${REGISTRY}/${svc}:${SHA}"
done

# Verify
gcloud artifacts docker images list us-central1-docker.pkg.dev/turbo-rag/rag-platform
```

## Notes

- `main.py` is identical across all services — DRY via `SERVICE_NAME` env var set in Dockerfile
- `/metrics` returns a hardcoded Prometheus stub (`up 1`); full metrics wired in Phase 4
- Images carry no secrets; all config injected at runtime via env / Secret Manager CSI
