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

variable "cloudsql_tier" {
  type        = string
  description = "Cloud SQL machine tier"
}

variable "cloudsql_availability_type" {
  type        = string
  description = "ZONAL or REGIONAL (HA)"
  default     = "ZONAL"
}

variable "cloudsql_deletion_protection" {
  type        = bool
  description = "Block accidental Cloud SQL instance delete"
  default     = false
}

variable "cloudsql_enable_pitr" {
  type        = bool
  description = "Enable point-in-time recovery for automated backups"
  default     = false
}