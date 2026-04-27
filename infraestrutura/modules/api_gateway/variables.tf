variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev/prod)"
  type        = string
}

variable "controller_invoke_arn" {
  description = "ARN de invocação do Lambda Controller"
  type        = string
}

variable "controller_function_name" {
  description = "Nome do Lambda Controller"
  type        = string
}

variable "status_invoke_arn" {
  description = "ARN de invocação do Lambda Status"
  type        = string
}

variable "status_function_name" {
  description = "Nome do Lambda Status"
  type        = string
}
