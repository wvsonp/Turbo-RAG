variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, prod)"
}

variable "secret_ids" {
  type        = list(string)
  description = "Secret Manager secret IDs (containers only; values added outside Terraform)"
  default     = ["openai-api-key"]
}

variable "k8s_namespace" {
  type        = string
  description = "Kubernetes namespace for Workload Identity binding"
  default     = "platform"
}

variable "k8s_service_account" {
  type        = string
  description = "Kubernetes service account name that may access secrets via WI"
  default     = "secret-smoke"
}
