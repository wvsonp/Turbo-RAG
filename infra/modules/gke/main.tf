resource "google_container_cluster" "primary" {
  name     = local.cluster_name
  location = var.region

  deletion_protection      = var.deletion_protection
  remove_default_node_pool = true
  initial_node_count       = 1

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

resource "google_container_node_pool" "system" {
  name     = "system"
  location = var.region
  cluster  = google_container_cluster.primary.name

  # Pin to one zone so node_count is exactly 2 (regional pools treat node_count as per-zone).
  node_locations = ["${var.region}-a"]
  node_count     = 2

  node_config {
    machine_type  = "e2-standard-2"
    disk_size_gb  = var.node_disk_size_gb
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

resource "google_container_node_pool" "application" {
  name     = "application"
  location = var.region
  cluster  = google_container_cluster.primary.name

  autoscaling {
    total_min_node_count = 1
    total_max_node_count = 5
  }

  node_config {
    machine_type  = "e2-standard-4"
    disk_size_gb  = var.node_disk_size_gb
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

resource "google_container_node_pool" "worker" {
  name     = "worker"
  location = var.region
  cluster  = google_container_cluster.primary.name

  autoscaling {
    total_min_node_count = 0
    total_max_node_count = 3
  }

  node_config {
    machine_type  = "e2-standard-2"
    disk_size_gb  = var.node_disk_size_gb
    spot          = true
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}
