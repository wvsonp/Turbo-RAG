locals {
  services = {
    api = {
      k8s_sa              = "api"
      grant_secret_access = true
    }
    ingestion = {
      k8s_sa              = "ingestion"
      grant_secret_access = false
    }
    query = {
      k8s_sa              = "query"
      grant_secret_access = true
    }
    workers = {
      k8s_sa              = "workers"
      grant_secret_access = false
    }
  }

  secret_accessor_services = [
    for name, cfg in local.services : name if cfg.grant_secret_access
  ]

  secret_iam_bindings = {
    for entry in flatten([
      for svc in local.secret_accessor_services : [
        for secret_id in var.secret_ids : {
          key       = "${svc}-${secret_id}"
          service   = svc
          secret_id = secret_id
        }
      ]
    ]) : entry.key => entry
  }
}

resource "google_service_account" "service" {
  for_each = local.services

  project      = var.project_id
  account_id   = "${each.key}-sa-${var.environment}"
  display_name = "Workload Identity SA for ${each.key} (${var.environment})"
}

resource "google_service_account_iam_member" "workload_identity" {
  for_each = local.services

  service_account_id = google_service_account.service[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.k8s_namespace}/${each.value.k8s_sa}]"
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = local.secret_iam_bindings

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.service[each.value.service].email}"
}

resource "google_project_iam_member" "cloudsql_client" {
  for_each = local.services

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_sql_user" "iam" {
  for_each = local.services

  name     = trimsuffix(google_service_account.service[each.key].email, ".gserviceaccount.com")
  project  = var.project_id
  instance = var.cloudsql_instance_name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}
