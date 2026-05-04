module "product" {
  source = "../../infraestrutura/modules/sqs"
  project_name = var.project_name
  environment  = var.environment
}

