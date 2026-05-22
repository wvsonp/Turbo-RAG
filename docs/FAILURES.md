## [Phase 1] PSA apply — Service Networking API disabled
**Date:** 2026-05-19
**What happened:** `terraform apply -target=module.network` created VPC, subnet, NAT, and PSA global address but failed on `google_service_networking_connection` because `servicenetworking.googleapis.com` was not enabled on project `turbo-rag`.
**Symptoms:** `Error 403: Service Networking API has not been used in project ... or it is disabled`
**What was tried:** Targeted apply without pre-checking API enablement
**Fix:** `gcloud services enable servicenetworking.googleapis.com --project=turbo-rag`, then re-run `terraform apply -target=module.network`
**Rule added:** _(none)_

## [Phase 1] GKE validation — kubectl missing locally
**Date:** 2026-05-21
**What happened:** GKE apply completed, but local cluster validation could not run because `kubectl` was not installed in the WSL environment.
**Symptoms:** `'kubectl' not found`
**What was tried:** Running `kubectl get nodes` before installing the Kubernetes CLI
**Fix:** Install `kubectl`, fetch GKE credentials, then rerun `kubectl get nodes`.
**Rule added:** _(none)_

## [Phase 1] GKE validation — GKE auth plugin missing locally
**Date:** 2026-05-21
**What happened:** `kubectl` was installed, but it could not authenticate to GKE because the required `gke-gcloud-auth-plugin` binary was missing locally.
**Symptoms:** `Unable to connect to the server: getting credentials: exec: executable gke-gcloud-auth-plugin not found`
**What was tried:** Running `kubectl get nodes` after fetching GKE credentials without installing the GKE auth plugin.
**Fix:** Install `google-cloud-cli-gke-gcloud-auth-plugin`, then rerun `gcloud container clusters get-credentials` and `kubectl get nodes`.
**Rule added:** _(none)_

## [Phase 1] GKE validation — application pool has no VM
**Date:** 2026-05-21
**What happened:** The GKE application node pool reports `RUNNING` with `totalMinNodeCount: 1`, but no matching Compute Engine VM is listed and no application node appears in `kubectl get nodes`.
**Symptoms:** `gcloud compute instances list --filter='name~gke-rag-platform-dev-application'` returned `Listed 0 items.`
**What was tried:** Verified node pool existence with `gcloud container node-pools list` and described the application pool.
**Fix:** Added `initial_node_count = 1` to the application node pool and re-applied; `kubectl get nodes -L cloud.google.com/gke-nodepool` showed application nodes as `Ready`.
**Rule added:** _(none)_

## [Phase 1] Secret Manager CSI — Helm not installed locally
**Date:** 2026-05-22
**What happened:** After `gcloud container clusters get-credentials`, CSI driver install failed because `helm` is not on the WSL PATH.
**Symptoms:** `Command 'helm' not found, but can be installed with: sudo snap install helm`
**What was tried:** Helm `upgrade --install` for base CSI driver and GCP provider
**Fix:** Install Helm (curl script) **or** install both drivers with `kubectl apply` from upstream release manifests (see `docs/history/secret_manager.md`).
**Rule added:** _(none)_

## [Phase 1] Qdrant StatefulSet — CrashLoopBackOff on snapshots path
**Date:** 2026-05-22
**What happened:** Qdrant pod crashed on startup with permission denied creating `./snapshots/tmp` because only `/qdrant/storage` was mounted on the PVC while `/qdrant` is root-owned in the container image.
**Symptoms:** `Failed to create snapshots temp directory at ./snapshots/tmp: Permission denied (os error 13)`; pod in `CrashLoopBackOff`.
**What was tried:** Mounting PVC at `/qdrant/storage` alone with default Qdrant paths.
**Fix:** Set `QDRANT__STORAGE__STORAGE_PATH=/qdrant/storage` and `QDRANT__STORAGE__SNAPSHOTS_PATH=/qdrant/storage/snapshots` in the Helm chart so all durable writes land on the PVC; delete pod to pick up env vars after upgrade.
**Rule added:** _(none)_
