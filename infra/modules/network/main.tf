locals {
  network_name = "rag-platform-${var.environment}"
  subnet_name  = "rag-platform-${var.environment}-${var.region}"

  pods_range_name     = "pods"
  services_range_name = "services"
}

resource "google_compute_network" "vpc" {
  name                    = local.network_name
  project                 = var.project_id
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "gke" {
  name    = local.subnet_name
  project = var.project_id
  region  = var.region
  network = google_compute_network.vpc.id

  ip_cidr_range = var.nodes_cidr

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = local.pods_range_name
    ip_cidr_range = var.pods_cidr
  }

  secondary_ip_range {
    range_name    = local.services_range_name
    ip_cidr_range = var.services_cidr
  }

  dynamic "log_config" {
    for_each = var.enable_flow_logs ? [1] : []
    content {
      aggregation_interval = var.flow_logs_interval
      flow_sampling        = var.flow_logs_sampling
      metadata             = "INCLUDE_ALL_METADATA"
    }
  }
}

resource "google_compute_global_address" "psa" {
  name          = "rag-platform-${var.environment}-psa"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = tonumber(split("/", var.psa_cidr)[1])
  address       = split("/", var.psa_cidr)[0]
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.psa.name]
}

resource "google_compute_router" "nat_router" {
  name    = "rag-platform-${var.environment}-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name    = "rag-platform-${var.environment}-nat"
  project = var.project_id
  region  = var.region
  router  = google_compute_router.nat_router.name

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# GCP load balancer health checks (GKE Ingress / Services).
resource "google_compute_firewall" "allow_health_checks" {
  name    = "rag-platform-${var.environment}-allow-health-checks"
  project = var.project_id
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 1000

  source_ranges = [
    "35.191.0.0/16",
    "130.211.0.0/22",
  ]

  allow {
    protocol = "tcp"
  }
}

# Node-to-node and pod traffic within the VPC.
resource "google_compute_firewall" "allow_internal" {
  name    = "rag-platform-${var.environment}-allow-internal"
  project = var.project_id
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 1000

  source_ranges = [
    var.nodes_cidr,
    var.pods_cidr,
    var.services_cidr,
  ]

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }
}

resource "google_compute_firewall" "deny_all_ingress" {
  name    = "rag-platform-${var.environment}-deny-all-ingress"
  project = var.project_id
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 65534

  source_ranges = ["0.0.0.0/0"]

  deny {
    protocol = "all"
  }
}
