## History

What we did so far, in order (logic over detail):

1. **Module scaffold** — `infra/modules/gke/` with placeholder `main.tf` (Phase 1.3). Folder and `variables.tf` only; not wired in root `main.tf`; no GKE resources or apply yet.
2. **Phase 1.3 GKE** — Standard regional cluster (`rag-platform-{environment}`) with Workload Identity, three node pools (system `e2-standard-2`×2, application `e2-standard-4` autoscale 1–5, worker `e2-standard-2` Spot autoscale 0–3), module wired in root `infra/main.tf`. Not applied yet.

## Runbook

Plan and apply (dev):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars
```

Fetch kubeconfig after apply:

```bash
gcloud container clusters get-credentials rag-platform-dev \
  --region us-central1 \
  --project turbo-rag
```

Verify node pools:

```bash
kubectl get nodes -L cloud.google.com/gke-nodepool
```
