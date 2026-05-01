variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "langchain-agent"
}

variable "environment" {
  description = "Ambiente (dev/prod)"
  type        = string
  default     = "dev"
}

variable "anthropic_api_key" {
  description = "Chave de API da Anthropic — não mais usada (migrado para Bedrock). Mantida para compatibilidade."
  type        = string
  sensitive   = true
  default     = ""
}

variable "opensearch_extra_arns" {
  description = "ARNs IAM extras com acesso ao OpenSearch (ex: usuário local de desenvolvimento)"
  type        = list(string)
  default     = []
}

variable "langfuse_public_key" {
  description = "Chave pública do Langfuse (pk-lf-...) — opcional; OTel desabilitado se vazio"
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_secret_key" {
  description = "Chave secreta do Langfuse (sk-lf-...) — opcional; OTel desabilitado se vazio"
  type        = string
  default     = ""
  sensitive   = true
}

variable "athena_database" {
  description = "Nome do banco de dados Athena com a tabela nps_feedbacks (vazio desativa NPS tool_use)"
  type        = string
  default     = ""
}

variable "athena_output_bucket" {
  description = "Nome do bucket S3 para resultados de queries Athena (sem s3://)"
  type        = string
  default     = ""
}
