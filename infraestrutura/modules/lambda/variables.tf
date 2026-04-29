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
  default     = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
}

variable "bedrock_region" {
  description = "Região AWS do Bedrock (sa-east-1 — Sonnet 4.5 disponível via global inference profile)"
  type        = string
  default     = "sa-east-1"
}

variable "vpc_subnet_ids" {
  description = "Subnet IDs para colocar o worker Lambda na VPC (acesso ao Neptune)"
  type        = list(string)
  default     = []
}

variable "vpc_security_group_ids" {
  description = "Security group IDs para o worker Lambda na VPC"
  type        = list(string)
  default     = []
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
