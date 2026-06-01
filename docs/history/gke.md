## History

What we did so far, in order (logic over detail):

1. **Module scaffold** — `infra/modules/gke/` with placeholder `main.tf` (Phase 1.3). Folder and `variables.tf` only; not wired in root `main.tf`; no GKE resources or apply yet.
2. **Phase 1.3 GKE** — Standard regional cluster (`rag-platform-{environment}`) with Workload Identity, three node pools (system `e2-standard-2`×2, application `e2-standard-4` autoscale 1–5, worker `e2-standard-2` Spot autoscale 0–3), module wired in root `infra/main.tf`. Not applied yet.
3. **Dev apply fix** — Hit `SSD_TOTAL_GB` (500) because regional `node_count` is per-zone and default disks are 100GB. System pool: `node_locations = [{region}-a]`, `node_count = 2`. Application/worker: `total_*_node_count`. Boot disks 50GB via `node_disk_size_gb`.
4. **Phase 1.3 dev apply** — GKE dev cluster applied on the custom VPC.
5. **Application pool validation fix** — `initial_node_count = 1` was added to the application pool after it initially had no backing VM; `kubectl` then showed Ready application and system nodes.

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

Note for dev cost control: without `node_locations`, `initial_node_count = 1` on a regional node pool can start one node per zone. Pin the application pool to one zone if dev should run a single application node.

## 2026-05-21 — 1.3 GKE dev apply

**What:** Applied the dev GKE cluster from Terraform after the custom VPC foundation was ready. The cluster uses VPC-native networking, private nodes, Workload Identity at cluster level, and separate system, application, and worker node pools.

**Why:** This creates the Kubernetes runtime that later foundation steps depend on: container image deployment, Helm releases, Qdrant, workers, and Workload Identity bindings.

**Commands:**
```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars
gcloud container clusters get-credentials rag-platform-dev --region us-central1 --project turbo-rag
kubectl get nodes -L cloud.google.com/gke-nodepool
```

## 2026-05-21 — 1.3 GKE validation complete

**What:** Validated GKE access with `kubectl` and confirmed Ready nodes for the system and application pools. The worker pool scaled down as expected because its total minimum is zero.

**Why:** Ready application nodes confirm the cluster can host the platform services planned in later Phase 1 steps, while the worker pool behavior confirms autoscaling can reduce idle background capacity.

**Commands:**
```bash
gcloud container clusters get-credentials rag-platform-dev --region us-central1 --project turbo-rag
kubectl get nodes -L cloud.google.com/gke-nodepool
gcloud container node-pools list --cluster rag-platform-dev --region us-central1 --project turbo-rag
```

## 2026-05-31 — GKE-only cost control runbook

**What:** Updated `quick-dev-reset.md` with a cleaner GKE-only destroy and restore path: delete regenerable PVCs first, preview a targeted `module.gke` destroy, keep stateful GCP services, and resume through Prefect, ingestion, and hybrid query validation.

**Why:** GKE nodes are the main dev cost driver, but deleting only the cluster should not force a full platform rebuild. The runbook now makes the cheap/painful resources explicit and avoids stale Docker build context commands during restore.

**Commands:**
```bash
kubectl get statefulset qdrant -n platform >/dev/null 2>&1 && \
  kubectl scale statefulset qdrant -n platform --replicas=0

kubectl get pod qdrant-0 -n platform >/dev/null 2>&1 && \
  kubectl wait --for=delete pod/qdrant-0 -n platform --timeout=300s

kubectl get namespace platform >/dev/null 2>&1 && \
  kubectl delete pvc qdrant-storage-qdrant-0 \
    -n platform --ignore-not-found --wait=true --timeout=300s

kubectl get namespace prefect >/dev/null 2>&1 && \
  kubectl delete pvc mlruns-pvc \
    -n prefect --ignore-not-found --wait=true --timeout=300s

cd /home/wvsonp/Turbo-RAG/infra
terraform plan -destroy -var-file=environments/dev.tfvars -target=module.gke
terraform destroy -var-file=environments/dev.tfvars -target=module.gke
terraform apply -var-file=environments/dev.tfvars -target=module.gke
```
