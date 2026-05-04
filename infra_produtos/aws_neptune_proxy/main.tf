module "product" {
  source = "../../infraestrutura/modules/neptune_proxy"
  project_name = var.project_name
  environment = var.environment
  neptune_endpoint = var.neptune_endpoint
  worker_role_arn = var.worker_role_arn
  vpc_subnet_ids = var.vpc_subnet_ids
  vpc_security_group_ids = var.vpc_security_group_ids
  layer_arn = var.layer_arn
}

