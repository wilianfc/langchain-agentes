output "api_endpoint" {
  description = "URL da API"
  value       = module.api_gateway.api_endpoint
}

output "dynamodb_table" {
  description = "Nome da tabela DynamoDB"
  value       = module.dynamodb.table_name
}

output "sqs_queue_url" {
  description = "URL da fila SQS"
  value       = module.sqs.queue_url
}

output "sns_topic_arn" {
  description = "ARN do tópico SNS"
  value       = module.sns.topic_arn
}

output "s3_bucket_name" {
  description = "Nome do bucket S3 de artefatos"
  value       = module.s3.bucket_name
}

output "opensearch_endpoint" {
  description = "Endpoint do domínio OpenSearch"
  value       = module.opensearch.domain_endpoint
}
