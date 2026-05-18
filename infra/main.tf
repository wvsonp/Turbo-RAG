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
