# Lessons

## GCP bootstrap — Terraform CI service account

> **Note:** Editor + IAM Admin is powerful — fine for early bootstrap; plan to narrow permissions in prod.

## GKE — regional node pools

> **Note:** On a regional cluster, `node_count` and `min_node_count` / `max_node_count` are **per zone** (≈3× nodes in us-central1). Use `total_min_node_count` / `total_max_node_count` for region-wide limits. Default 100GB boot disks add up fast against `SSD_TOTAL_GB` (500 in new projects).
