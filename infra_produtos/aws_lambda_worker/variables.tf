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
variable "controller_role_arn" {
  description = "ARN controller"
  type        = string
  default     = ""
}

variable "worker_role_arn" {
  description = "ARN worker"
  type        = string
  default     = ""
}

variable "status_role_arn" {
  description = "ARN status"
  type        = string
  default     = ""
}

variable "ingester_role_arn" {
  description = "ARN ingester"
  type        = string
  default     = ""
}

variable "sqs_queue_url" {
  description = "URL SQS"
  type        = string
  default     = ""
}

variable "sqs_queue_arn" {
  description = "ARN SQS"
  type        = string
  default     = ""
}

variable "dynamodb_table_name" {
  description = "Tabela DynamoDB"
  type        = string
  default     = ""
}

variable "sns_topic_arn" {
  description = "ARN SNS"
  type        = string
  default     = ""
}

variable "opensearch_endpoint" {
  description = "Endpoint OpenSearch"
  type        = string
  default     = ""
}

variable "neptune_endpoint" {
  description = "Endpoint Neptune"
  type        = string
  default     = ""
}

variable "neptune_proxy_function" {
  description = "Nome Lambda proxy"
  type        = string
  default     = ""
}

variable "s3_bucket_name" {
  description = "Bucket S3"
  type        = string
  default     = ""
}

variable "s3_bucket_name_for_trigger" {
  description = "Bucket trigger"
  type        = string
  default     = ""
}

variable "s3_bucket_arn" {
  description = "ARN S3"
  type        = string
  default     = ""
}

variable "layer_arn" {
  description = "ARN layer"
  type        = string
  default     = ""
}

variable "enable_s3_ingester_trigger" {
  description = "Habilita trigger S3"
  type        = bool
  default     = true
}

variable "athena_database" {
  description = "Banco Athena"
  type        = string
  default     = ""
}

variable "athena_output_bucket" {
  description = "Bucket Athena"
  type        = string
  default     = ""
}

variable "langfuse_public_key" {
  description = "Langfuse PK"
  type        = string
  default     = ""
}

variable "langfuse_secret_key" {
  description = "Langfuse SK"
  type        = string
  default     = ""
}

