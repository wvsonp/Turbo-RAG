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

## [Phase 3] Hybrid retrieval deploy — wrong Dockerfile path and missing Prefect namespace
**Date:** 2026-05-31
**What happened:** The 3.2 deploy runbook used Dockerfile paths relative to the Docker build context instead of the repo root, and the Prefect deployment registration was attempted before the `prefect` namespace existed.
**Symptoms:** `ERROR: failed to build: resolve : lstat ingestion: no such file or directory`, `ERROR: failed to build: resolve : lstat workers: no such file or directory`, followed by `Error from server (NotFound): namespaces "prefect" not found`.
**What was tried:** Running the section 18 loop with `docker build -f "${svc}/Dockerfile" ... services/`, then pushing and upgrading Helm despite the failed builds.
**Fix:** Update `quick-dev-reset.md` to use repo-root Dockerfile paths (`services/${svc}/Dockerfile` and `services/query/Dockerfile`) while keeping `services/` as the build context; ensure Prefect section 14 is complete before re-registering the ingest deployment.
**Rule added:** _(none)_

## [Phase 3] Ingestion rollout — dispatcher exits after early Prefect DNS failure
**Date:** 2026-05-31
**What happened:** The new ingestion pod started before the Prefect service was resolvable; the dispatcher thread crashed during startup and readiness stayed 503.
**Symptoms:** `httpx.ConnectError: [Errno -2] Name or service not known` from `PrefectClient.resolve_deployment_id()`, followed by repeated `/ready` 503 responses.
**What was tried:** Restarting section 18 after Prefect install while the old ingestion pod was still serving and the new pod had already crashed its dispatcher thread.
**Fix:** Restart/rollout the ingestion deployment after Prefect service `prefect-server.prefect.svc.cluster.local` exists; longer-term fix is making dispatcher startup retry instead of permanently killing readiness on one transient DNS failure.
**Rule added:** _(none)_

## [Phase 3] Sparse encoder dependency check — local pip unavailable
**Date:** 2026-05-31
**What happened:** A local package-version check for `fastembed` could not run because the WSL `python3` environment has no `pip` module installed.
**Symptoms:** `/usr/bin/python3: No module named pip`
**What was tried:** `python3 -m pip index versions fastembed`
**Fix:** Use the repo's existing requirements-file style and let Docker build/install resolve the dependency.
**Rule added:** _(none)_

## [Phase 3] GKE cost teardown — Qdrant PVC delete wait timed out
**Date:** 2026-05-31
**What happened:** The GKE-only cost teardown runbook deleted the Qdrant PVC but timed out waiting for Kubernetes to finish the delete.
**Symptoms:** `persistentvolumeclaim "qdrant-storage-qdrant-0" deleted from platform namespace` followed by `error: timed out waiting for the condition on persistentvolumeclaims/qdrant-storage-qdrant-0`; `mlruns-pvc` deletion returned without a timeout.
**What was tried:** `kubectl delete pvc qdrant-storage-qdrant-0 -n platform --ignore-not-found --wait=true --timeout=300s` and `kubectl delete pvc mlruns-pvc -n prefect --ignore-not-found --wait=true --timeout=300s`
**Fix:** Stop the Qdrant StatefulSet before deleting its PVC (`kubectl scale statefulset qdrant -n platform --replicas=0`, wait for `pod/qdrant-0` deletion, then wait for the PVC delete); update `quick-dev-reset.md` so future GKE-only teardowns stop Qdrant before PVC cleanup.
**Rule added:** _(none)_
