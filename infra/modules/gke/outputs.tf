output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "GKE API server endpoint"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_location" {
  description = "Region of the regional GKE cluster"
  value       = google_container_cluster.primary.location
}

output "workload_identity_pool" {
  description = "Workload Identity pool for Kubernetes service account bindings"
  value       = google_container_cluster.primary.workload_identity_config[0].workload_pool
}
