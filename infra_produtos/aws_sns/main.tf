module "product" {
  source = "../../infraestrutura/modules/sns"
  project_name = var.project_name
  environment  = var.environment
}

