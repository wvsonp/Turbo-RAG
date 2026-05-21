output "instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.primary.name
}

output "connection_name" {
  description = "Instance connection name for Auth Proxy and Helm (project:region:instance)"
  value       = google_sql_database_instance.primary.connection_name
}

output "private_ip_address" {
  description = "Private IP address allocated from the PSA range"
  value       = google_sql_database_instance.primary.private_ip_address
}

output "database_names" {
  description = "Platform database names on the instance"
  value       = [for db in google_sql_database.platform : db.name]
}
