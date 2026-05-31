locals {
  prefect_server_k8s_sa = "prefect-server"
  prefect_namespace     = "prefect"
  prefect_workers_k8s_sa = "workers"
}

resource "google_service_account" "prefect_server" {
  project      = var.project_id
  account_id   = "prefect-server-sa-${var.environment}"
  display_name = "Workload Identity SA for Prefect server (${var.environment})"
}

resource "google_service_account_iam_member" "prefect_server_workload_identity" {
  service_account_id = google_service_account.prefect_server.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${local.prefect_namespace}/${local.prefect_server_k8s_sa}]"
}

resource "google_service_account_iam_member" "workers_prefect_workload_identity" {
  service_account_id = google_service_account.service["workers"].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${local.prefect_namespace}/${local.prefect_workers_k8s_sa}]"
}

resource "google_project_iam_member" "prefect_server_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.prefect_server.email}"
}

resource "google_project_iam_member" "prefect_server_cloudsql_instance_user" {
  project = var.project_id
  role    = "roles/cloudsql.instanceUser"
  member  = "serviceAccount:${google_service_account.prefect_server.email}"
}

resource "google_sql_user" "prefect_server_iam" {
  name     = trimsuffix(google_service_account.prefect_server.email, ".gserviceaccount.com")
  project  = var.project_id
  instance = var.cloudsql_instance_name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}
