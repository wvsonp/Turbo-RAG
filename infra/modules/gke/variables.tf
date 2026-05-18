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

locals {
  cluster_name = coalesce(var.cluster_name, "rag-platform-${var.environment}")
}
