# Execution plans

Step-by-step plans with acceptance criteria for each phase. The high-level roadmap lives in [`docs/project-roadmap.md`](../project-roadmap.md).

| Phase | Folder | Focus |
| ----- | ------ | ----- |
| 1 | [phase-1-foundation/](phase-1-foundation/) | GCP, Terraform, network, GKE, data plane, skeleton deploy |
| 2 | [phase-2-ingestion/](phase-2-ingestion/) | GCS → Pub/Sub → Prefect → Qdrant |
| 3 | [phase-3-query-retrieval/](phase-3-query-retrieval/) | FastAPI query, hybrid search, auth |
| 4 | [phase-4-observability/](phase-4-observability/) | Langfuse, Prometheus, Grafana, OTel |
| 5 | [phase-5-cicd-mlflow/](phase-5-cicd-mlflow/) | GitHub Actions, MLflow, canary |
| 6 | [phase-6-scaling-hardening/](phase-6-scaling-hardening/) | HPA, load test, DR, ADRs |

**How to use:** Complete steps in order within a phase unless a step explicitly allows parallel work. Mark progress in [`docs/STATUS.md`](../STATUS.md).
