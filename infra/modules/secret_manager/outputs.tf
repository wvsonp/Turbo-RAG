output "secret_ids" {
  description = "Secret Manager secret IDs managed as containers"
  value       = sort(keys(google_secret_manager_secret.platform))
}

output "secret_accessor_email" {
  description = "GCP service account email for pod Workload Identity secret access"
  value       = google_service_account.secret_accessor.email
}

output "k8s_service_account_annotation" {
  description = "Kubernetes ServiceAccount annotation for Workload Identity"
  value       = "iam.gke.io/gcp-service-account: ${google_service_account.secret_accessor.email}"
}
