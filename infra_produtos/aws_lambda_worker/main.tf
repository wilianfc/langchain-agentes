module "product" {
  source = "../../infraestrutura/modules/lambda"
  project_name = var.project_name
  environment = var.environment
  controller_role_arn = var.controller_role_arn
  worker_role_arn = var.worker_role_arn
  status_role_arn = var.status_role_arn
  ingester_role_arn = var.ingester_role_arn
  sqs_queue_url = var.sqs_queue_url
  sqs_queue_arn = var.sqs_queue_arn
  dynamodb_table_name = var.dynamodb_table_name
  sns_topic_arn = var.sns_topic_arn
  opensearch_endpoint = var.opensearch_endpoint
  neptune_endpoint = var.neptune_endpoint
  neptune_proxy_function = var.neptune_proxy_function
  s3_bucket_name = var.s3_bucket_name
  s3_bucket_name_for_trigger = var.s3_bucket_name_for_trigger
  s3_bucket_arn = var.s3_bucket_arn
  layer_arn = var.layer_arn
  enable_s3_ingester_trigger = var.enable_s3_ingester_trigger
  athena_database = var.athena_database
  athena_output_bucket = var.athena_output_bucket
  langfuse_public_key = var.langfuse_public_key
  langfuse_secret_key = var.langfuse_secret_key
}

