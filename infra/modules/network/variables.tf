variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for subnet, router, and NAT"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, prod); used in resource naming"
}

variable "nodes_cidr" {
  type        = string
  description = "Primary subnet CIDR for GKE nodes"
  default     = "10.0.0.0/20"
}

variable "pods_cidr" {
  type        = string
  description = "Secondary range CIDR for pod alias IPs"
  default     = "10.4.0.0/14"
}

variable "services_cidr" {
  type        = string
  description = "Secondary range CIDR for ClusterIP services"
  default     = "10.8.0.0/20"
}

variable "psa_cidr" {
  type        = string
  description = "Reserved range for Private Service Access (Cloud SQL private IP)"
  default     = "10.16.0.0/16"
}

variable "enable_flow_logs" {
  type        = bool
  description = "Enable VPC flow logs on the GKE subnet (recommended for prod)"
  default     = false
}

variable "flow_logs_sampling" {
  type        = number
  description = "Flow log sampling rate (0.0–1.0) when flow logs are enabled"
  default     = 0.5
}

variable "flow_logs_interval" {
  type        = string
  description = "Flow log aggregation interval when flow logs are enabled"
  default     = "INTERVAL_5_SEC"
}
