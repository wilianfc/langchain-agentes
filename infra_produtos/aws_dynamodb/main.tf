module "product" {
  source = "../../infraestrutura/modules/dynamodb"
  project_name = var.project_name
  environment  = var.environment
}

