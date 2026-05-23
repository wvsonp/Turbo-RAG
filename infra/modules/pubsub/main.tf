locals {
  bucket_name              = "rag-ingestion-${var.environment}"
  topic_name               = "ingestion-uploads"
  subscription_name        = "ingestion-uploads-sub"
  test_subscription_name   = "ingestion-uploads-test-sub"
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_storage_bucket" "ingestion" {
  name     = local.bucket_name
  project  = var.project_id
  location = var.region

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }
}

resource "google_pubsub_topic" "ingestion_uploads" {
  name    = local.topic_name
  project = var.project_id
}

resource "google_pubsub_subscription" "ingestion_uploads" {
  name    = local.subscription_name
  project = var.project_id
  topic   = google_pubsub_topic.ingestion_uploads.id

  ack_deadline_seconds       = 600
  message_retention_duration = "604800s"
  retain_acked_messages      = false
}

resource "google_pubsub_subscription" "ingestion_uploads_test" {
  name    = local.test_subscription_name
  project = var.project_id
  topic   = google_pubsub_topic.ingestion_uploads.id

  ack_deadline_seconds       = 600
  message_retention_duration = "604800s"
  retain_acked_messages      = false
}

resource "google_pubsub_topic_iam_member" "gcs_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.ingestion_uploads.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.current.number}@gs-project-accounts.iam.gserviceaccount.com"
}

resource "google_storage_notification" "ingestion" {
  bucket         = google_storage_bucket.ingestion.name
  payload_format = "JSON_API_V1"
  topic          = google_pubsub_topic.ingestion_uploads.id
  event_types    = ["OBJECT_FINALIZE"]

  depends_on = [google_pubsub_topic_iam_member.gcs_publisher]
}
