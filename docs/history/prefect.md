## History

What we did so far, in order (logic over detail):

1. **2.2 Prefect on GKE (2026-05-23)** — Terraform `prefect` DB + `prefect-server-sa`; Helm values for official `prefect/prefect-server` and `prefect/prefect-worker`; Cloud SQL Auth Proxy sidecar with IAM auth; sample `hello-flow` on worker pool.

## Runbook

Terraform (dev):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.cloudsql -target=module.iam
terraform output cloudsql_database_names | grep prefect
terraform output iam_service_account_emails | grep prefect_server
```

Helm (official Prefect charts + repo values in `helm/prefect/`):

```bash
gcloud container clusters get-credentials rag-platform-dev --region us-central1 --project turbo-rag
helm repo add prefect https://prefecthq.github.io/prefect-helm
helm repo update prefect

kubectl create namespace prefect --dry-run=client -o yaml | kubectl apply -f -

# URL-encode @ in IAM DB username; proxy listens on 127.0.0.1 (sidecar uses --private-ip --auto-iam-authn)
kubectl create secret generic prefect-server-postgresql-connection \
  --from-literal=connection-string='postgresql+asyncpg://prefect-server-sa-dev%40turbo-rag.iam@127.0.0.1:5432/prefect' \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap prefect-worker-base-job-template \
  --from-file=baseJobTemplate.json=helm/prefect/base-job-template-dev.json \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -

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
kubectl get sa -n prefect prefect-server workers \
  -o custom-columns=NAME:.metadata.name,GSA:.metadata.annotations.'iam\.gke\.io/gcp-service-account'
```

Cloud SQL IAM user grants (once per fresh `prefect` database — see `docs/history/cloudsql.md`):

```bash
# After setting a known postgres password (dev bootstrap only)
CLOUDSQL_IP="$(cd infra && terraform output -raw cloudsql_private_ip)"
kubectl run db-grant-prefect --restart=Never -n prefect \
  --image=postgres:15-alpine \
  --env="PGPASSWORD=<postgres-password>" \
  --command -- sh -c "
psql -h ${CLOUDSQL_IP} -U postgres -d prefect -c \"GRANT ALL ON SCHEMA public TO \\\"prefect-server-sa-dev@turbo-rag.iam\\\";\"
psql -h ${CLOUDSQL_IP} -U postgres -d prefect -c \"GRANT cloudsqlsuperuser TO \\\"prefect-server-sa-dev@turbo-rag.iam\\\";\"
psql -h ${CLOUDSQL_IP} -U postgres -d rag_metadata -c \"GRANT cloudsqlsuperuser TO \\\"workers-sa-dev@turbo-rag.iam\\\";\"
echo GRANTS_OK"
kubectl wait --for=jsonpath='{.status.containerStatuses[0].state.terminated.reason}'=Completed \
  pod/db-grant-prefect -n prefect --timeout=90s
kubectl logs db-grant-prefect -n prefect
kubectl delete pod db-grant-prefect -n prefect --ignore-not-found
```

Sample flow validation:

```bash
kubectl create configmap hello-flow-source \
  --from-file=hello_flow.py=helm/prefect/sample-flow/hello_flow.py \
  -n prefect --dry-run=client -o yaml | kubectl apply -f -

kubectl run prefect-pool-update --restart=Never -n prefect \
  --image=prefecthq/prefect:3-python3.11-kubernetes \
  --overrides='{"spec":{"containers":[{"name":"c","image":"prefecthq/prefect:3-python3.11-kubernetes","env":[{"name":"PREFECT_API_URL","value":"http://prefect-server.prefect.svc.cluster.local:4200/api"}],"volumeMounts":[{"name":"tpl","mountPath":"/tpl"},{"name":"flow","mountPath":"/flow"}],"command":["sh","-c","prefect work-pool update kubernetes --base-job-template /tpl/baseJobTemplate.json && cd /flow && prefect deploy hello_flow.py:hello_flow --name hello-flow --pool kubernetes && prefect deployment run hello-flow/hello-flow --job-variable namespace=prefect --job-variable service_account_name=workers && sleep 60"]}],"volumes":[{"name":"tpl","configMap":{"name":"prefect-worker-base-job-template"}},{"name":"flow","configMap":{"name":"hello-flow-source"}}]}}'

kubectl get jobs -n prefect
kubectl get pods -n prefect -o wide
```

**Chart choice:** Official [`prefect/prefect-server`](https://github.com/PrefectHQ/prefect-helm) and [`prefect/prefect-worker`](https://github.com/PrefectHQ/prefect-helm) from `https://prefecthq.github.io/prefect-helm`.

**Connector:** Cloud SQL Auth Proxy v2 sidecar (`gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.3`) with `--auto-iam-authn --private-ip`; TCP to `127.0.0.1:5432`. No postgres password in Kubernetes Secrets.

**Destroy order:** `helm uninstall prefect-worker prefect-server -n prefect` before dropping `prefect` database or removing `prefect-server-sa` WI bindings.

## 2026-05-23 — 2.2 Prefect on GKE dev apply

**What:** Added `prefect` database and `prefect-server-sa-{env}` with WI to `prefect/prefect-server`; extended `workers-sa` WI to `prefect/workers`; granted `roles/cloudsql.instanceUser` for IAM DB login; deployed Prefect server (system pool) and worker (Spot worker pool) via official Helm charts; validated `hello-flow` job on worker pool with Cloud SQL `rag_metadata` IAM auth.

**Why:** Phase 2 ingestion requires Prefect orchestration on GKE with Cloud SQL metadata store and flow jobs on the Spot worker pool before building the dispatcher and ingestion flow (2.3).

**Commands:** See Runbook above.
