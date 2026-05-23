module "network" {
  source = "./modules/network"

  project_id       = var.project_id
  region           = var.region
  environment      = var.environment
  enable_flow_logs = var.network_enable_flow_logs
}

module "gke" {
  source = "./modules/gke"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  network                  = module.network.network_name
  subnetwork               = module.network.subnet_name
  pods_secondary_range     = module.network.pods_secondary_range_name
  services_secondary_range = module.network.services_secondary_range_name
}

module "artifact_registry" {
  source = "./modules/artifact_registry"

  project_id = var.project_id
  region     = var.region
}

module "cloudsql" {
  source = "./modules/cloudsql"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  network_self_link = module.network.network_self_link

  tier                = var.cloudsql_tier
  availability_type   = var.cloudsql_availability_type
  deletion_protection = var.cloudsql_deletion_protection
  enable_pitr         = var.cloudsql_enable_pitr

  depends_on = [module.network]
}

module "secret_manager" {
  source = "./modules/secret_manager"

  project_id  = var.project_id
  environment = var.environment
}

module "pubsub" {
  source = "./modules/pubsub"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

module "iam" {
  source = "./modules/iam"

  project_id                = var.project_id
  environment               = var.environment
  secret_ids                = module.secret_manager.secret_ids
  cloudsql_instance_name    = module.cloudsql.instance_name
  ingestion_bucket_name       = module.pubsub.ingestion_bucket_name
  ingestion_subscription_name = module.pubsub.ingestion_subscription_name

  depends_on = [module.secret_manager, module.cloudsql, module.pubsub]
}
