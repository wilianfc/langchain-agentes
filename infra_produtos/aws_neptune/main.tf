module "product" {
  source = "../../infraestrutura/modules/neptune"
  project_name = var.project_name
  environment = var.environment
  worker_role_id = var.worker_role_id
  instance_class = var.instance_class
}

