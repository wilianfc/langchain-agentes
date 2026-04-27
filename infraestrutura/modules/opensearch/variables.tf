variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev/prod)"
  type        = string
}

variable "worker_role_arn" {
  description = "ARN da IAM role do Lambda Worker (concede acesso ao domínio)"
  type        = string
}
