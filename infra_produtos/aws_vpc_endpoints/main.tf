module "product" {
  source = "../../infraestrutura/modules/vpc_endpoints"
  project_name = var.project_name
  environment  = var.environment
}

