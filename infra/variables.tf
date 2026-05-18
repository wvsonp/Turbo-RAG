variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, prod)"
}

variable "network_enable_flow_logs" {
  type        = bool
  description = "Enable VPC flow logs on the GKE subnet (recommended for prod)"
  default     = false
}