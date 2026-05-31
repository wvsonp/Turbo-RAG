locals {
  accessor_sa_id = "secret-accessor-${var.environment}"
}

resource "google_secret_manager_secret" "platform" {
  for_each = toset(var.secret_ids)

  project   = var.project_id
  secret_id = each.value

  replication {
    auto {}
  }
}

resource "google_service_account" "secret_accessor" {
  project      = var.project_id
  account_id   = local.accessor_sa_id
  display_name = "Secret Manager accessor (${var.environment})"
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = google_secret_manager_secret.platform

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.secret_accessor.email}"
}

resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.secret_accessor.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.k8s_namespace}/${var.k8s_service_account}]"
}
