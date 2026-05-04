module "product" {
  source = "../../infraestrutura/modules/opensearch"
  project_name = var.project_name
  environment = var.environment
  worker_role_arn = var.worker_role_arn
  extra_principal_arns = var.extra_principal_arns
}

