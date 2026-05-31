project_id               = "turbo-rag"
region                   = "us-central1"
environment              = "prod"
network_enable_flow_logs = true

cloudsql_tier                = "db-g1-small"
cloudsql_availability_type   = "REGIONAL"
cloudsql_deletion_protection = true
cloudsql_enable_pitr         = true