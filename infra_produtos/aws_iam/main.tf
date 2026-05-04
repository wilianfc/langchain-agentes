module "product" {
  source = "../../infraestrutura/modules/iam"
  project_name = var.project_name
  environment = var.environment
  dynamodb_table_arn = var.dynamodb_table_arn
  sqs_queue_arn = var.sqs_queue_arn
  sns_topic_arn = var.sns_topic_arn
  s3_bucket_arn = var.s3_bucket_arn
}

