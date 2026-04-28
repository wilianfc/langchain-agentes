variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev/prod)"
  type        = string
}

variable "controller_role_arn" {
  description = "ARN da role do Lambda Controller"
  type        = string
}

variable "worker_role_arn" {
  description = "ARN da role do Lambda Worker"
  type        = string
}

variable "status_role_arn" {
  description = "ARN da role do Lambda Status"
  type        = string
}

variable "sqs_queue_url" {
  description = "URL da fila SQS"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN da fila SQS"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN do tópico SNS"
  type        = string
}

variable "opensearch_endpoint" {
  description = "Endpoint do domínio OpenSearch (sem https://)"
  type        = string
  default     = ""
}

variable "s3_bucket_name" {
  description = "Nome do bucket S3 de artefatos"
  type        = string
  default     = ""
}

variable "layer_arn" {
  description = "ARN da Lambda Layer com dependências Python"
  type        = string
}

variable "neptune_endpoint" {
  description = "Endpoint de escrita do cluster Neptune"
  type        = string
  default     = ""
}

variable "bedrock_model_id" {
  description = "Model ID do Amazon Bedrock para inferência Claude"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}

variable "bedrock_region" {
  description = "Região AWS onde o Bedrock está disponível (cross-region desde sa-east-1)"
  type        = string
  default     = "us-east-1"
}

variable "langfuse_public_key" {
  description = "Chave pública Langfuse para OTel (opcional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_secret_key" {
  description = "Chave secreta Langfuse para OTel (opcional)"
  type        = string
  default     = ""
  sensitive   = true
}
