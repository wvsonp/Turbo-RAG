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