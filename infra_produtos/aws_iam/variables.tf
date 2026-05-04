variable "aws_region" {
  description = "Regiao AWS"
  type        = string
  default     = "sa-east-1"
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "langchain-agent"
}

variable "environment" {
  description = "Ambiente"
  type        = string
  default     = "dev"
}
variable "dynamodb_table_arn" {
  description = "ARN DynamoDB"
  type        = string
  default     = ""
}

variable "sqs_queue_arn" {
  description = "ARN SQS"
  type        = string
  default     = ""
}

variable "sns_topic_arn" {
  description = "ARN SNS"
  type        = string
  default     = ""
}

variable "s3_bucket_arn" {
  description = "ARN S3"
  type        = string
  default     = ""
}

