variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for the ingestion bucket"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, prod)"
}