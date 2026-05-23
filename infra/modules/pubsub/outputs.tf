output "ingestion_bucket_name" {
  description = "GCS bucket for document uploads"
  value       = local.bucket_name
}

output "ingestion_bucket_url" {
  description = "GCS bucket URL prefix"
  value       = "gs://${google_storage_bucket.ingestion.name}"
}

output "ingestion_topic_id" {
  description = "Pub/Sub topic ID for ingestion uploads"
  value       = google_pubsub_topic.ingestion_uploads.id
}

output "ingestion_topic_name" {
  description = "Pub/Sub topic name for ingestion uploads"
  value       = local.topic_name
}

output "ingestion_subscription_id" {
  description = "Main Pub/Sub subscription ID (dispatcher consumer)"
  value       = google_pubsub_subscription.ingestion_uploads.id
}

output "ingestion_subscription_name" {
  description = "Main Pub/Sub subscription name"
  value       = local.subscription_name
}

output "ingestion_test_subscription_id" {
  description = "Test Pub/Sub subscription ID (manual validation only)"
  value       = google_pubsub_subscription.ingestion_uploads_test.id
}

output "ingestion_test_subscription_name" {
  description = "Test Pub/Sub subscription name"
  value       = local.test_subscription_name
}
