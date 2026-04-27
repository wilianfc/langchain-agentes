variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev/prod)"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN da tabela DynamoDB"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN da fila SQS"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN do tópico SNS"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN do bucket S3 de artefatos"
  type        = string
}
