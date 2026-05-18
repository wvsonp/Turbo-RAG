terraform {
  backend "gcs" {
    bucket = "rag-platform-tf-state"
    prefix = "terraform/state"
  }
}