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

locals {
  cluster_name = coalesce(var.cluster_name, "rag-platform-${var.environment}")
}
