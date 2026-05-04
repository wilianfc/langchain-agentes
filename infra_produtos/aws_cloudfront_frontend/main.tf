module "product" {
  source = "../../infraestrutura/modules/cloudfront_frontend"
  project_name = var.project_name
  environment = var.environment
  api_endpoint = var.api_endpoint
}

