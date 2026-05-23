resource "google_storage_bucket_iam_member" "ingestion_object_viewer" {
  count = var.ingestion_bucket_name != "" ? 1 : 0

  bucket = var.ingestion_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.service["ingestion"].email}"
}

resource "google_storage_bucket_iam_member" "workers_object_viewer" {
  count = var.ingestion_bucket_name != "" ? 1 : 0

  bucket = var.ingestion_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.service["workers"].email}"
}

resource "google_pubsub_subscription_iam_member" "ingestion_subscriber" {
  count = var.ingestion_subscription_name != "" ? 1 : 0

  project      = var.project_id
  subscription = var.ingestion_subscription_name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.service["ingestion"].email}"
}

resource "google_pubsub_subscription_iam_member" "ingestion_dlq_subscriber" {
  count = var.ingestion_dlq_subscription_name != "" ? 1 : 0

  project      = var.project_id
  subscription = var.ingestion_dlq_subscription_name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.service["ingestion"].email}"
}

resource "google_project_iam_member" "workers_aiplatform_user" {
  count = var.ingestion_bucket_name != "" ? 1 : 0

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.service["workers"].email}"
}
