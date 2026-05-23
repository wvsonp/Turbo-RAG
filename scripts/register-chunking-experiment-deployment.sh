#!/usr/bin/env bash
# Register chunking-experiment Prefect deployment on the kubernetes work pool.
set -euo pipefail

NAMESPACE="${PREFECT_NAMESPACE:-prefect}"
API_URL="${PREFECT_API_URL:-http://prefect-server.prefect.svc.cluster.local:4200/api}"
WORKERS_IMAGE="${WORKERS_IMAGE:?Set WORKERS_IMAGE (e.g. us-central1-docker.pkg.dev/turbo-rag/rag-platform/workers:TAG)}"

kubectl run prefect-deploy-chunking-experiment --restart=Never -n "$NAMESPACE" \
  --image="$WORKERS_IMAGE" \
  --overrides="$(cat <<EOF
{
  "spec": {
    "serviceAccountName": "workers",
    "containers": [{
      "name": "c",
      "image": "${WORKERS_IMAGE}",
      "env": [
        {"name": "PREFECT_API_URL", "value": "${API_URL}"},
        {"name": "PREFECT_LOGGING_LEVEL", "value": "INFO"},
        {"name": "MLFLOW_TRACKING_URI", "value": "file:/mlruns"},
        {"name": "EXPERIMENT_TEST_GCS_URI", "value": "gs://rag-ingestion-dev/experiments/chunking-sample.txt"}
      ],
      "command": ["sh", "-c", "prefect work-pool inspect kubernetes >/dev/null 2>&1 || prefect work-pool create kubernetes --type kubernetes; prefect deploy flows/chunking_experiment.py:chunking_experiment --name chunking-experiment --pool kubernetes --job-variable image=${WORKERS_IMAGE} && echo DEPLOY_OK && sleep 120"]
    }]
  }
}
EOF
)"

echo "Waiting for deploy job..."
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/prefect-deploy-chunking-experiment -n "$NAMESPACE" --timeout=180s || true
kubectl logs prefect-deploy-chunking-experiment -n "$NAMESPACE"
kubectl delete pod prefect-deploy-chunking-experiment -n "$NAMESPACE" --ignore-not-found
