variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for the Cloud SQL instance"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, prod); used in default instance naming"
}

variable "instance_name" {
  type        = string
  description = "Cloud SQL instance name; defaults to rag-platform-{environment}"
  default     = null
}

variable "network_self_link" {
  type        = string
  description = "VPC network self link for private IP (PSA peering must be active)"
}

variable "tier" {
  type        = string
  description = "Cloud SQL machine tier (e.g. db-f1-micro, db-g1-small)"
}

variable "availability_type" {
  type        = string
  description = "ZONAL for dev; REGIONAL for prod HA"
  default     = "ZONAL"
}

variable "disk_size_gb" {
  type        = number
  description = "Initial data disk size in GB"
  default     = 10
}

variable "deletion_protection" {
  type        = bool
  description = "Prevent accidental instance delete via Terraform or Console"
  default     = false
}

variable "enable_pitr" {
  type        = bool
  description = "Enable point-in-time recovery (recommended for prod)"
  default     = false
}

variable "backup_retained_count" {
  type        = number
  description = "Number of automated backups to retain"
  default     = 7
}

variable "backup_start_time" {
  type        = string
  description = "Daily backup window start (UTC, HH:MM)"
  default     = "03:00"
}
