module "product" {
  source = "../../infraestrutura/modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

