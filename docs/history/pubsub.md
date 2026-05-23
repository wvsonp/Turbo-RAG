## History

What we did so far, in order (logic over detail):

1. **Module scaffold** — `infra/modules/pubsub/` with placeholder `main.tf` (Phase 2). Folder and `variables.tf` only; not wired in root `main.tf`.
2. **Phase 2.1 implementation** — GCS bucket `rag-ingestion-{env}`, Pub/Sub topic/subscriptions, GCS `OBJECT_FINALIZE` notification, GCS publisher IAM, root wiring and outputs.

## Runbook

Terraform (dev — apply pubsub before or with IAM ingestion bindings):

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform plan -var-file=environments/dev.tfvars -target=module.pubsub -target=module.iam
terraform apply -var-file=environments/dev.tfvars -target=module.pubsub -target=module.iam
terraform output ingestion_bucket_name ingestion_topic_name ingestion_subscription_name
```

Upload → Pub/Sub validation (use **test** sub for `--auto-ack`; never on main sub once dispatcher runs):

```bash
echo "test-$(date +%s)" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag
sleep 5
gcloud pubsub subscriptions pull ingestion-uploads-test-sub --auto-ack --limit=1 --project=turbo-rag

gcloud pubsub subscriptions describe ingestion-uploads-sub \
  --project=turbo-rag --format="value(ackDeadlineSeconds)"
# Expected: 600

gcloud pubsub topics get-iam-policy ingestion-uploads --project=turbo-rag
# Expected: service-{project_number}@gs-project-accounts.iam.gserviceaccount.com → roles/pubsub.publisher
```

WI proof (ingestion KSA lists bucket):

```bash
kubectl run wi-gcs-ingestion --rm -i --restart=Never -n platform \
  --image=google/cloud-sdk:slim \
  --overrides='{"spec":{"serviceAccountName":"ingestion"}}' \
  -- gcloud storage ls gs://rag-ingestion-dev/incoming/ --project=turbo-rag
```

**Destroy order:** stop dispatcher/consumers → drain `ingestion-uploads-dlq-sub` → remove `dead_letter_policy` from main sub (via Terraform) → remove GCS notification → delete subscription IAM before subscriptions.

## 2026-05-23 — 2.1 GCS + Pub/Sub dev apply

**What:** Implemented `infra/modules/pubsub/`: bucket `rag-ingestion-dev` (regional, versioning, uniform access, public access prevention), topic `ingestion-uploads`, subscriptions `ingestion-uploads-sub` (600s ack, 7d retention) and `ingestion-uploads-test-sub`, GCS notification + publisher IAM for the GCS service account. Wired `module.pubsub` in root; extended `module.iam` with scoped ingestion roles.

**Why:** Object uploads must trigger Pub/Sub messages with `bucket`, `name`, and `generation` so the dispatcher (2.3) can start idempotent Prefect flow runs.

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.pubsub -target=module.iam

echo "test-$(date +%s)" > /tmp/sample.txt
gcloud storage cp /tmp/sample.txt gs://rag-ingestion-dev/incoming/sample.txt --project=turbo-rag
gcloud pubsub subscriptions pull ingestion-uploads-test-sub --auto-ack --limit=1 --project=turbo-rag
```

**Not in 2.1:** DLQ topology ([2.5](docs/plan/phase-2-ingestion/2.5-dlq-idempotency.md)); dispatcher service code ([2.3](docs/plan/phase-2-ingestion/2.3-ingestion-flow.md)).

## 2026-05-24 — 2.5 DLQ topology dev apply

**What:** Extended `infra/modules/pubsub/`: DLQ topic `ingestion-uploads-dlq`, subscription `ingestion-uploads-dlq-sub`, `dead_letter_policy` on main sub (`max_delivery_attempts = 5`), Pub/Sub service agent IAM (publisher on DLQ topic, subscriber on main sub). Helm `PUBSUB_DLQ_SUBSCRIPTION` on ingestion dispatcher.

**Why:** Failed deliveries must land in an inspectable DLQ after bounded retries; Pub/Sub SA grants are required for forwarding (commonly missed).

**Commands:**

```bash
cd /home/wvsonp/Turbo-RAG/infra
terraform apply -var-file=environments/dev.tfvars -target=module.pubsub

gcloud pubsub subscriptions describe ingestion-uploads-sub \
  --project=turbo-rag --format="yaml(deadLetterPolicy)"

gcloud pubsub topics get-iam-policy ingestion-uploads-dlq --project=turbo-rag

# Inspect DLQ (no --auto-ack until payload recorded)
gcloud pubsub subscriptions pull ingestion-uploads-dlq-sub \
  --project=turbo-rag --limit=1
```

**Rollback:** Remove `dead_letter_policy` before destroying DLQ topic; drain DLQ sub first; scale ingestion dispatcher to 0 before subscription destroy.
