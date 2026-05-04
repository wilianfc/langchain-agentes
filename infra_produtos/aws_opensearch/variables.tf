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
variable "worker_role_arn" {
  description = "ARN role worker"
  type        = string
  default     = ""
}

variable "extra_principal_arns" {
  description = "Principals adicionais"
  type        = list(string)
  default     = []
}

