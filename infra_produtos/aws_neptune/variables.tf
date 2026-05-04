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
variable "worker_role_id" {
  description = "ID role worker"
  type        = string
  default     = ""
}

variable "instance_class" {
  description = "Classe Neptune"
  type        = string
  default     = "db.t3.medium"
}

