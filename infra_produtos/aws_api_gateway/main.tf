module "product" {
  source = "../../infraestrutura/modules/api_gateway"
  project_name = var.project_name
  environment = var.environment
  controller_invoke_arn = var.controller_invoke_arn
  controller_function_name = var.controller_function_name
  status_invoke_arn = var.status_invoke_arn
  status_function_name = var.status_function_name
  ingester_invoke_arn = var.ingester_invoke_arn
  ingester_function_name = var.ingester_function_name
}

