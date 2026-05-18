variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for the regional cluster and node pools"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, prod); used in cluster name when cluster_name is unset"
}

variable "cluster_name" {
  type        = string
  description = "GKE cluster name"
  default     = null
}

variable "node_disk_size_gb" {
  type        = number
  description = "Boot disk size (GB) per node; keep low in dev to stay under regional SSD_TOTAL_GB quota"
  default     = 50
}

variable "deletion_protection" {
  type        = bool
  description = "Block accidental cluster delete; set false before terraform destroy"
  default     = false
}

variable "network" {
  type        = string
  description = "VPC network name for the cluster"
}

variable "subnetwork" {
  type        = string
  description = "Regional subnet name for nodes"
}

variable "pods_secondary_range" {
  type        = string
  description = "Subnet secondary range name for pod alias IPs"
}

variable "services_secondary_range" {
  type        = string
  description = "Subnet secondary range name for ClusterIP services"
}

variable "master_ipv4_cidr_block" {
  type        = string
  description = "RFC 1918 /28 for private cluster control plane (required with private nodes)"
  default     = "172.16.0.0/28"
}

locals {
  cluster_name = coalesce(var.cluster_name, "rag-platform-${var.environment}")
}
