output "network_name" {
  description = "VPC network name for GKE and Cloud SQL"
  value       = google_compute_network.vpc.name
}

output "network_id" {
  description = "VPC network self link ID"
  value       = google_compute_network.vpc.id
}

output "network_self_link" {
  description = "VPC network self link"
  value       = google_compute_network.vpc.self_link
}

output "subnet_name" {
  description = "Regional subnet name for GKE nodes"
  value       = google_compute_subnetwork.gke.name
}

output "subnet_id" {
  description = "Regional subnet self link ID"
  value       = google_compute_subnetwork.gke.id
}

output "subnet_self_link" {
  description = "Regional subnet self link"
  value       = google_compute_subnetwork.gke.self_link
}

output "pods_secondary_range_name" {
  description = "Secondary IP range name for GKE pods (alias IPs)"
  value       = local.pods_range_name
}

output "services_secondary_range_name" {
  description = "Secondary IP range name for GKE services (alias IPs)"
  value       = local.services_range_name
}

output "psa_allocated_range" {
  description = "CIDR reserved for Private Service Access (Cloud SQL)"
  value       = var.psa_cidr
}

output "psa_address_name" {
  description = "Global address resource name used for PSA peering"
  value       = google_compute_global_address.psa.name
}

output "router_name" {
  description = "Cloud Router name used for NAT"
  value       = google_compute_router.nat_router.name
}
