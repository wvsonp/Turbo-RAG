# RAG ML Platform on GCP — Project Roadmap

> **Purpose:** A production-grade, MLOps-focused RAG system deployed on Google Cloud Platform.
> The goal is platform engineering depth — scalability, observability, and deployment lifecycle — not RAG accuracy optimization.
>
> **Stack:** FastAPI · Qdrant · Prefect · Langfuse · Prometheus · Grafana · OpenTelemetry · MLflow · GKE · Terraform · Helm · GitHub Actions

---

## Phase Overview


| #   | Phase                      | Focus                                               | Est. Duration |
| --- | -------------------------- | --------------------------------------------------- | ------------- |
| 1   | Foundation — Infra as Code | GCP setup, GKE, Terraform, Docker, Helm             | ~1.5 weeks    |
| 2   | Ingestion Pipeline         | GCS → Pub/Sub → Prefect → Chunking → Qdrant         | ~2 weeks      |
| 3   | Query & Retrieval Service  | FastAPI + Hybrid Search + Reranker + LLM            | ~2 weeks      |
| 4   | Observability Stack        | Langfuse + Prometheus + Grafana + OTel              | ~2 weeks      |
| 5   | CI/CD + MLflow Registry    | GitHub Actions + Helm deploy + Embedding versioning | ~1.5 weeks    |
| 6   | Scaling & Hardening        | HPA, load testing, DR, ADRs                         | ~2 weeks      |


---

## Phase 1 — Foundation: Infrastructure as Code

**Goal:** A reproducible GCP environment where every resource is defined in Terraform and every service runs as a Docker container on GKE.

No service code yet. This phase is entirely about the platform underneath everything else.

### 1.1 GCP Project Bootstrap

**Where:** GCP Console → then move everything to Terraform immediately after.

- Create a new GCP project (e.g., `rag-platform-prod`)
- Enable APIs: `container.googleapis.com`, `sqladmin.googleapis.com`, `pubsub.googleapis.com`, `artifactregistry.googleapis.com`, `secretmanager.googleapis.com`, `storage.googleapis.com`, `aiplatform.googleapis.com`
- Create a GCS bucket for Terraform remote state: `gs://rag-platform-tf-state`
- Create a service account for Terraform CI with roles: `Editor`, `Storage Admin`, `IAM Admin` — download a JSON key only for the initial bootstrap; rotate it out later

> **Learning point:** Enabling APIs via Terraform (`google_project_service`) is idempotent and trackable. Do the first enable manually just once to get started, then add them to Terraform.

### 1.2 Terraform Project Structure

**Where:** Local repo → `infra/` directory.

Suggested layout:

```
infra/
├── main.tf
├── variables.tf
├── outputs.tf
├── backend.tf          # GCS remote state
├── modules/
│   ├── gke/
│   ├── cloudsql/
│   ├── artifact_registry/
│   ├── pubsub/
│   ├── secret_manager/
│   └── iam/
└── environments/
    ├── dev.tfvars
    └── prod.tfvars
```

Configure remote state in `backend.tf`:

```hcl
terraform {
  backend "gcs" {
    bucket = "rag-platform-tf-state"
    prefix = "terraform/state"
  }
}
```

Run `terraform init` to connect to the remote backend. This is the first real Terraform command in the project.

### 1.3 GKE Cluster

**Where:** `infra/modules/gke/main.tf`

Provision a **Standard** GKE cluster (not Autopilot — you need manual control over node pools for the interview story):

- **System node pool:** `e2-standard-2`, 2 nodes, for Kubernetes system pods
- **Application node pool:** `e2-standard-4`, autoscaling 1–5 nodes, for platform services
- **Worker node pool:** `e2-standard-2`, autoscaling 0–3 nodes, preemptible/Spot — for Prefect workers (cost saving)
- Enable **Workload Identity** at cluster level — this is the foundation of all pod-to-GCP-service auth

```hcl
resource "google_container_cluster" "primary" {
  name     = "rag-platform"
  location = var.region
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  # ...
}
```

> **Learning point:** With Workload Identity, a Kubernetes Service Account is bound to a GCP Service Account. Pods get GCP credentials automatically — no JSON keys inside containers ever.

### 1.4 Artifact Registry

**Where:** `infra/modules/artifact_registry/main.tf`

Create a Docker repository:

```hcl
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "rag-platform"
  format        = "DOCKER"
}
```

Configure local Docker to push to it:

```bash
gcloud auth configure-docker {REGION}-docker.pkg.dev
```

All service images will be tagged as:
`{REGION}-docker.pkg.dev/{PROJECT_ID}/rag-platform/{service-name}:{git-sha}`

### 1.5 CloudSQL (PostgreSQL)

**Where:** `infra/modules/cloudsql/main.tf`

- PostgreSQL 15, `db-f1-micro` for dev, `db-g1-small` for prod
- Enable **IAM database authentication** — no username/password for application connections
- Private IP only (no public endpoint) — accessible only within the VPC
- Create databases: `rag_metadata`, `langfuse`, `mlflow`

> **Learning point:** IAM database auth means pods authenticate with their Workload Identity token. No secrets to rotate, no passwords to leak.

### 1.6 Secret Manager

**Where:** `infra/modules/secret_manager/main.tf`

Store secrets that cannot use Workload Identity (e.g., OpenAI API key, external webhook tokens):

```hcl
resource "google_secret_manager_secret" "openai_key" {
  secret_id = "openai-api-key"
  replication { automatic {} }
}
```

In Kubernetes, use the **Secret Manager CSI driver** to mount secrets as files into pods — no secrets in environment variables, no secrets in Kubernetes Secrets objects.

### 1.7 Dockerize Services (Skeleton)

**Where:** Each service directory, e.g., `services/api/Dockerfile`

Write a multi-stage Dockerfile for each service using a build stage and a minimal runtime stage:

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

At this stage, services can be skeleton apps — a FastAPI app with just `/health` and `/ready` endpoints. The goal is a buildable, pushable image.

> **Learning point:** Multi-stage builds keep production images small (no build tools included). The build stage installs dependencies; the runtime stage copies only what's needed.

### 1.8 Helm Charts

**Where:** `helm/` directory, one chart per service.

Suggested layout:

```
helm/
├── api/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── hpa.yaml
│       └── serviceaccount.yaml
├── qdrant/
├── workers/
└── ...
```

Every `Deployment` template must include:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 15
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 10
```

> **Learning point:** Without probes, Kubernetes routes traffic to pods that aren't ready. Liveness = restart if broken; Readiness = only send traffic when ready.

### 1.9 Deploy Qdrant on GKE

**Where:** `helm/qdrant/` or use the official Qdrant Helm chart.

Qdrant must be a **StatefulSet** (not a Deployment) because it writes data to disk:

```yaml
kind: StatefulSet
spec:
  volumeClaimTemplates:
    - metadata:
        name: qdrant-storage
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: standard-rwo
        resources:
          requests:
            storage: 10Gi
```

> **Learning point:** StatefulSet gives each pod a stable identity and its own PVC. If the pod restarts, it reattaches to the same volume — data is preserved. A Deployment with a shared PVC would not give this guarantee.

### 1.10 Workload Identity Binding

**Where:** Terraform IAM module + Kubernetes Service Account annotation.

For each service that needs GCP access, bind its Kubernetes Service Account to a GCP Service Account:

```hcl
resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.api.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.namespace}/${var.ksa_name}]"
}
```

In the Kubernetes manifest, annotate the Service Account:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    iam.gke.io/gcp-service-account: api-sa@{PROJECT_ID}.iam.gserviceaccount.com
```

After this, any pod using this Service Account can call GCP APIs (GCS, Secret Manager, Vertex AI) without any credentials in the container.

---

### Phase 1 Checklist

- GCP project created, APIs enabled
- Terraform remote state in GCS
- GKE cluster with 3 node pools (system, app, worker/spot)
- Workload Identity enabled at cluster level
- Artifact Registry repository created
- CloudSQL (PostgreSQL) — private IP, IAM auth
- Secret Manager secrets created
- Skeleton Docker images built and pushed to Artifact Registry
- Helm charts written for all services (skeleton)
- Qdrant deployed as StatefulSet with PVC
- Workload Identity bindings for each service
- All services have `/health` and `/ready` probes

---

## Phase 2 — Ingestion Pipeline

**Goal:** Upload a document → it automatically gets parsed, chunked, embedded, and stored in Qdrant without any manual intervention.

### Key tasks

- Set up GCS bucket with Pub/Sub event notifications on object upload
- Write Prefect flow: `parse → chunk → embed → upsert to Qdrant → write metadata to PostgreSQL`
- Implement 3 chunking strategies: fixed-size, recursive, semantic — log all three as MLflow experiments
- Build async embedding worker with batched calls to Vertex AI `text-embedding-004`
- Configure Dead Letter Queue (DLQ) for failed Pub/Sub messages
- Make all flows idempotent (re-runnable without creating duplicates)

---

## Phase 3 — Query & Retrieval Service

**Goal:** A production-ready query endpoint with hybrid search, reranking, and streamed LLM responses.

### Key tasks

- Build FastAPI query endpoint with async handlers and Pydantic request validation
- Implement hybrid search: dense (Qdrant ANN) + sparse (BM25) with Reciprocal Rank Fusion (RRF)
- Add CrossEncoder reranker (`ms-marco-MiniLM-L-6-v2`) — top-50 candidates → top-5 final
- Implement JWT-based auth + RBAC middleware (admin / user / readonly roles)
- Add streaming response via Server-Sent Events (SSE)
- Instrument with OpenTelemetry: trace per request, span per pipeline step

---

## Phase 4 — Observability Stack

**Goal:** Full visibility into system health, LLM costs, and RAG quality — all in one place.

### Key tasks

- Deploy self-hosted Langfuse on Cloud Run with CloudSQL backend
- Instrument all LLM calls with Langfuse SDK: trace → span → generation (token counts, latency)
- Deploy Prometheus + Grafana using `kube-prometheus-stack` Helm chart
- Expose `GET /metrics` endpoint on every service (Prometheus format)
- Build Grafana dashboards: ingestion throughput, query P50/P95/P99, token usage, RAGAS scores
- Define alerting rules: `error_rate > 1%`, `p99_latency > 3s`, `qdrant_disk_usage > 80%`
- Set up OpenTelemetry Collector as a DaemonSet — single export target for all services

---

## Phase 5 — CI/CD + MLflow Model Registry

**Goal:** Every code push automatically builds, tests, and deploys. Embedding model changes go through a quality gate before reaching production.

### Key tasks

- Build GitHub Actions pipeline: `lint → unit tests → docker build → push to Artifact Registry → helm upgrade`
- Deploy MLflow Tracking Server with GCS artifact store and CloudSQL backend
- Register chunking configs and embedding model versions in MLflow Model Registry
- Implement canary deployment: route 10% of traffic to new embedding model, compare RAGAS scores
- Add automated rollback: if RAGAS `faithfulness` drops below threshold, roll back to previous model

---

## Phase 6 — Scaling & Production Hardening

**Goal:** Demonstrate the platform handles load, recovers from failure, and is documented for handoff.

### Key tasks

- Configure HPA on the query service: scale on CPU + custom metric (`active_queries`)
- Enable GKE node auto-provisioning with Spot instances for the worker node pool
- Load test with Locust: 100 concurrent users, validate P99 latency SLO holds under load
- Schedule Qdrant collection snapshots to GCS (Prefect cron flow, daily)
- Write Architecture Decision Records (ADRs) for key design choices:
  - Why Qdrant over Pinecone
  - Why Prefect over Airflow
  - Why self-hosted Langfuse over LangSmith
  - Workload Identity vs service account key files

---

## Repository Structure (suggested)

```
rag-platform/
├── infra/                  # Terraform — all GCP resources
│   ├── modules/
│   └── environments/
├── services/
│   ├── api/                # API Gateway (FastAPI)
│   ├── ingestion/          # Ingestion Service (FastAPI)
│   ├── query/              # Query/Retrieval Service (FastAPI)
│   └── workers/            # Prefect flows
├── helm/                   # Helm charts — one per service
├── .github/workflows/      # GitHub Actions CI/CD
├── docs/
│   └── adr/                # Architecture Decision Records
└── README.md
```

---

## Key Design Decisions (ADR Stubs)


| Decision      | Choice                       | Rejected Alternative      | Reason                                                 |
| ------------- | ---------------------------- | ------------------------- | ------------------------------------------------------ |
| Vector DB     | Qdrant (self-hosted on GKE)  | Pinecone                  | Full infra ownership; StatefulSet story for interviews |
| Orchestration | Prefect 2.x                  | Airflow                   | Native Python, better DX, deployable on K8s Jobs       |
| LLM Tracing   | Langfuse (self-hosted)       | LangSmith                 | Open-source, self-hosted = no data leaves GCP          |
| Auth to GCP   | Workload Identity            | Service account JSON keys | No credentials in containers, automatic rotation       |
| Messaging     | GCP Pub/Sub                  | Kafka                     | Managed service, lower ops overhead, native GCP        |
| Embeddings    | Vertex AI text-embedding-004 | OpenAI ada-002            | Stays within GCP, Workload Identity auth               |


