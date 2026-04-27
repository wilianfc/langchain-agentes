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
  description = "Chave de API da Anthropic (Claude)"
  type        = string
  sensitive   = true
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
