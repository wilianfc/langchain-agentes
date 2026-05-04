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
variable "controller_invoke_arn" {
  description = "Invoke ARN controller"
  type        = string
  default     = ""
}

variable "controller_function_name" {
  description = "Nome controller"
  type        = string
  default     = ""
}

variable "status_invoke_arn" {
  description = "Invoke ARN status"
  type        = string
  default     = ""
}

variable "status_function_name" {
  description = "Nome status"
  type        = string
  default     = ""
}

variable "ingester_invoke_arn" {
  description = "Invoke ARN ingester"
  type        = string
  default     = ""
}

variable "ingester_function_name" {
  description = "Nome ingester"
  type        = string
  default     = ""
}

