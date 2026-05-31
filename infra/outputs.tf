output "project_id" {
  value = var.project_id
}

output "environment" {
  value = var.environment
}

output "region" {
  value = var.region
}

output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = module.gke.cluster_name
}

output "gke_cluster_endpoint" {
  description = "GKE API server endpoint"
  value       = module.gke.cluster_endpoint
  sensitive   = true
}

output "gke_cluster_location" {
  description = "GKE cluster region"
  value       = module.gke.cluster_location
}

output "gke_workload_identity_pool" {
  description = "Workload Identity pool for pod-to-GCP auth bindings"
  value       = module.gke.workload_identity_pool
}

output "network_name" {
  description = "VPC network name"
  value       = module.network.network_name
}

output "network_subnet_name" {
  description = "GKE regional subnet name"
  value       = module.network.subnet_name
}

output "network_psa_range" {
  description = "CIDR reserved for Private Service Access (Cloud SQL)"
  value       = module.network.psa_allocated_range
}

output "artifact_registry_repository_id" {
  description = "Docker Artifact Registry repository ID"
  value       = module.artifact_registry.repository_id
}

output "artifact_registry_url" {
  description = "Base URL for service images: {url}/{service}:{git-sha}"
  value       = module.artifact_registry.repository_url
}

output "cloudsql_instance_name" {
  description = "Cloud SQL PostgreSQL instance name"
  value       = module.cloudsql.instance_name
}

output "cloudsql_connection_name" {
  description = "Connection name for Cloud SQL Auth Proxy and Helm"
  value       = module.cloudsql.connection_name
}

output "cloudsql_private_ip" {
  description = "Private IP of the Cloud SQL instance (PSA range)"
  value       = module.cloudsql.private_ip_address
}

output "cloudsql_database_names" {
  description = "Platform databases on the instance"
  value       = module.cloudsql.database_names
}

output "secret_manager_secret_ids" {
  description = "Secret Manager secret container IDs (values added outside Terraform)"
  value       = module.secret_manager.secret_ids
}

output "secret_accessor_gcp_sa_email" {
  description = "GCP SA for pods that mount secrets via CSI + Workload Identity"
  value       = module.secret_manager.secret_accessor_email
}

output "iam_service_account_emails" {
  description = "Per-service GCP SA emails for Workload Identity (api, ingestion, query, workers)"
  value       = module.iam.service_account_emails
}

output "iam_k8s_service_account_annotations" {
  description = "Helm serviceAccount.annotations values per service"
  value       = module.iam.k8s_service_account_annotations
}

output "ingestion_bucket_name" {
  description = "GCS bucket for document uploads"
  value       = module.pubsub.ingestion_bucket_name
}

output "ingestion_bucket_url" {
  description = "GCS bucket URL prefix for ingestion uploads"
  value       = module.pubsub.ingestion_bucket_url
}

output "ingestion_topic_name" {
  description = "Pub/Sub topic for GCS upload notifications"
  value       = module.pubsub.ingestion_topic_name
}

output "ingestion_subscription_name" {
  description = "Main Pub/Sub subscription (dispatcher consumer)"
  value       = module.pubsub.ingestion_subscription_name
}

output "ingestion_test_subscription_name" {
  description = "Test Pub/Sub subscription for manual validation"
  value       = module.pubsub.ingestion_test_subscription_name
}