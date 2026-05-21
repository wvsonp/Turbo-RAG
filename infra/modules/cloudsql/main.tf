locals {
  instance_name = coalesce(var.instance_name, "rag-platform-${var.environment}")
  databases     = ["rag_metadata", "langfuse", "mlflow"]
}

resource "google_sql_database_instance" "primary" {
  name             = local.instance_name
  project          = var.project_id
  region           = var.region
  database_version = "POSTGRES_15"

  deletion_protection = var.deletion_protection

  settings {
    tier              = var.tier
    availability_type = var.availability_type
    disk_type         = "PD_SSD"
    disk_size         = var.disk_size_gb

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_self_link
    }

    backup_configuration {
      enabled                        = true
      start_time                     = var.backup_start_time
      point_in_time_recovery_enabled = var.enable_pitr

      backup_retention_settings {
        retained_backups = var.backup_retained_count
        retention_unit   = "COUNT"
      }
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    maintenance_window {
      day          = 7
      hour         = 4
      update_track = "stable"
    }
  }
}

resource "google_sql_database" "platform" {
  for_each = toset(local.databases)

  name     = each.key
  project  = var.project_id
  instance = google_sql_database_instance.primary.name
}
