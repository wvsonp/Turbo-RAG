output "service_account_emails" {
  description = "GCP service account email per platform service"
  value = {
    for name, sa in google_service_account.service : name => sa.email
  }
}

output "k8s_service_account_annotations" {
  description = "Kubernetes ServiceAccount Workload Identity annotations per service"
  value = {
    for name, sa in google_service_account.service : name =>
    "iam.gke.io/gcp-service-account: ${sa.email}"
  }
}

output "workload_identity_members" {
  description = "Workload Identity member strings (project.svc.id.goog[namespace/ksa])"
  value = {
    for name, cfg in local.services : name =>
    "serviceAccount:${var.project_id}.svc.id.goog[${var.k8s_namespace}/${cfg.k8s_sa}]"
  }
}
