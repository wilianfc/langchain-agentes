variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev/homol/prod)"
  type        = string
}

variable "api_endpoint" {
  description = "URL base da API Gateway a ser consumida pelo frontend"
  type        = string
}
