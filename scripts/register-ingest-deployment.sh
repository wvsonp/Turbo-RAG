#!/usr/bin/env bash
# Register ingest-document Prefect deployment on the kubernetes work pool.
set -euo pipefail

NAMESPACE="${PREFECT_NAMESPACE:-prefect}"
API_URL="${PREFECT_API_URL:-http://prefect-server.prefect.svc.cluster.local:4200/api}"
WORKERS_IMAGE="${WORKERS_IMAGE:?Set WORKERS_IMAGE (e.g. us-central1-docker.pkg.dev/turbo-rag/rag-platform/workers:TAG)}"

# Requires ConfigMap prefect-worker-base-job-template (see install_guide §14).
kubectl run prefect-deploy-ingest --restart=Never -n "$NAMESPACE" \
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
        {"name": "PREFECT_LOGGING_LEVEL", "value": "INFO"}
      ],
      "volumeMounts": [{"name": "tpl", "mountPath": "/tpl"}],
      "command": ["sh", "-c", "prefect work-pool inspect kubernetes >/dev/null 2>&1 || prefect work-pool create kubernetes --type kubernetes; prefect work-pool update kubernetes --base-job-template /tpl/baseJobTemplate.json; prefect deploy --name ingest-document --pool kubernetes --job-variable image=${WORKERS_IMAGE} --job-variable namespace=${NAMESPACE} --job-variable service_account_name=workers && echo DEPLOY_OK && sleep 120"]
    }],
    "volumes": [{
      "name": "tpl",
      "configMap": {"name": "prefect-worker-base-job-template"}
    }]
  }
}
EOF
)"

echo "Waiting for deploy job..."
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/prefect-deploy-ingest -n "$NAMESPACE" --timeout=180s || true
kubectl logs prefect-deploy-ingest -n "$NAMESPACE"
kubectl delete pod prefect-deploy-ingest -n "$NAMESPACE" --ignore-not-found
