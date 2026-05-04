module "product" {
  source = "../../infraestrutura/modules/lambda_layer"
  project_name = var.project_name
  environment = var.environment
  s3_bucket_name = var.s3_bucket_name
}

