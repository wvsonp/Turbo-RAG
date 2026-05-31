## History

What we did so far, in order (logic over detail):

1. **Module scaffold** — `infra/modules/secret_manager/` with placeholder `main.tf` (Phase 1.6). Folder and `variables.tf` only; not wired in root `main.tf`; no Secret Manager resources or apply yet.
2. **Phase 1.6 implementation** — Secret containers (`openai-api-key`), GCP SA `secret-accessor-<env>`, per-secret `secretAccessor` IAM, Workload Identity binding to `platform/secret-smoke`. CSI smoke manifests under `k8s/secret-manager-csi/`.

## Runbook

Terraform (dev):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars -target=module.secret_manager
terraform apply -var-file=environments/dev.tfvars -target=module.secret_manager
terraform output secret_manager_secret_ids secret_accessor_gcp_sa_email
```

Add secret **value** manually (never commit):

```bash
echo -n 'sk-your-dev-key' | gcloud secrets versions add openai-api-key \
  --project=turbo-rag --data-file=-
gcloud secrets list --project=turbo-rag
```

Cluster credentials and CSI drivers:

```bash
gcloud container clusters get-credentials rag-platform-dev --region us-central1 --project turbo-rag
```

**Option A — Helm** (needs `helm` on PATH; install: `curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash`):

```bash
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo update
helm upgrade --install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system --set syncSecret.enabled=false
helm upgrade --install secrets-store-csi-driver-provider-gcp \
  oci://ghcr.io/googlecloudplatform/secrets-store-csi-driver-provider-gcp/charts/secrets-store-csi-driver-provider-gcp \
  --namespace kube-system
```

**Option B — kubectl only** (no Helm; use when `helm: command not found`):

```bash
CSI_TAG=v1.4.7
BASE="https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/${CSI_TAG}/deploy"
kubectl apply -f "${BASE}/rbac-secretproviderclass.yaml"
kubectl apply -f "${BASE}/csidriver.yaml"
kubectl apply -f "${BASE}/secrets-store.csi.x-k8s.io_secretproviderclasses.yaml"
kubectl apply -f "${BASE}/secrets-store.csi.x-k8s.io_secretproviderclasspodstatuses.yaml"
kubectl apply -f "${BASE}/secrets-store-csi-driver.yaml"
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/secrets-store-csi-driver-provider-gcp/main/deploy/provider-gcp-plugin.yaml
kubectl get pods -n kube-system | grep -E 'csi-secrets-store|csi-secrets-store-provider-gcp'
```

Smoke workload (update SA annotation if `secret_accessor_gcp_sa_email` differs):

```bash
kubectl apply -f /home/wvsonp/Turbo-RAG/k8s/secret-manager-csi/namespace.yaml
kubectl apply -f /home/wvsonp/Turbo-RAG/k8s/secret-manager-csi/serviceaccount.yaml
kubectl apply -f /home/wvsonp/Turbo-RAG/k8s/secret-manager-csi/secretproviderclass.yaml
kubectl apply -f /home/wvsonp/Turbo-RAG/k8s/secret-manager-csi/smoke-pod.yaml
kubectl describe pod -n platform secret-csi-smoke
kubectl logs -n platform secret-csi-smoke
kubectl delete pod -n platform secret-csi-smoke
```

**Destroy order:** remove CSI volumes from workloads → delete smoke pod → `terraform destroy -target=module.secret_manager`.

## 2026-05-22 — 1.6 Secret Manager dev validation

**What:** Applied `module.secret_manager`, added `openai-api-key` version via `gcloud`, installed CSI drivers with kubectl (Helm not on PATH), validated `secret-csi-smoke` pod: CSI volume `secrets-store.csi.k8s.io`, mount `/var/secrets`, no secret in env.

**Why:** Third-party API keys must mount as files via Secret Manager + CSI before service skeletons and Helm charts reference them.

**Commands:**
```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.secret_manager
# add secret version with gcloud (see runbook above)
# CSI kubectl apply block from runbook
kubectl wait --for=condition=ready pod/secret-csi-smoke -n platform --timeout=120s
kubectl describe pod -n platform secret-csi-smoke
kubectl logs -n platform secret-csi-smoke
```
