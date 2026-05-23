variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, prod)"
}

variable "k8s_namespace" {
  type        = string
  description = "Kubernetes namespace for Workload Identity bindings"
  default     = "platform"
}

variable "secret_ids" {
  type        = list(string)
  description = "Secret Manager secret IDs to grant accessor role (api and query only)"
  default     = []
}

variable "cloudsql_instance_name" {
  type        = string
  description = "Cloud SQL instance name for IAM database users"
}

variable "ingestion_bucket_name" {
  type        = string
  description = "GCS ingestion bucket name for scoped IAM (empty skips bucket bindings)"
  default     = ""
}

variable "ingestion_subscription_name" {
  type        = string
  description = "Main Pub/Sub subscription name for scoped IAM (empty skips subscriber bindings)"
  default     = ""
}
