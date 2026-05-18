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