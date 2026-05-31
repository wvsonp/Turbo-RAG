# Lessons

## GCP bootstrap — Terraform CI service account

> **Note:** Editor + IAM Admin is powerful — fine for early bootstrap; plan to narrow permissions in prod.

## GKE — regional node pools

> **Note:** On a regional cluster, `node_count` and `min_node_count` / `max_node_count` are **per zone** (≈3× nodes in us-central1). Use `total_min_node_count` / `total_max_node_count` for region-wide limits. Default 100GB boot disks add up fast against `SSD_TOTAL_GB` (500 in new projects).

## GKE — PVC disks after cluster deletion

> **Note:** Deleting a GKE cluster removes workloads and nodes, but persistent disks backing PVCs can remain detached and keep billing. For disposable dev data, stop pods that mount the PVCs first (for example scale Qdrant StatefulSet to zero), delete known PVCs such as Qdrant and MLflow before destroying the cluster, then check for old detached `pvc-*` disks.

## kubectl — smoke pod attach race

> **Note:** `kubectl run --rm -i` on fast one-shot containers (curl, `nc`, short
> `gcloud`) often reports `terminated (Error)` when kubectl fails to attach before
> the container exits — the check may still have passed. Use create → wait for
> `Completed` → `kubectl logs` → delete (see `quick-dev-reset.md`).

## Qdrant on GKE — snapshot path permissions

> **Note:** Mounting a PVC at `/qdrant/storage` alone is not enough: Qdrant defaults write snapshots to `./snapshots` under WORKDIR (`/qdrant`), which is root-owned in the image. Set `QDRANT__STORAGE__SNAPSHOTS_PATH` (and `STORAGE_PATH`) under the PVC mount or the pod CrashLoops with permission denied on `./snapshots/tmp`.

## Prefect + Cloud SQL IAM auth

> **Note:** Cloud SQL Auth Proxy on private-IP-only instances needs `--private-ip` (otherwise: "instance does not have IP of type PUBLIC"). GCP SAs also need `roles/cloudsql.instanceUser` (not just `cloudsql.client`) for IAM database login. URL-encode `@` in IAM usernames in connection strings (`%40`). New IAM DB users need postgres bootstrap grants (`GRANT cloudsqlsuperuser`, schema grants) on the `prefect` database before Prefect server migrations succeed. Kubernetes work pool base job templates must set `"namespace": "{{ namespace }}"` at the `job_configuration` top level — not only in `job_manifest.metadata` — or flow jobs land in `default`.
