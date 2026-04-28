variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev/prod)"
  type        = string
}

variable "instance_class" {
  description = "Classe da instância Neptune"
  type        = string
  default     = "db.t3.medium"
}

variable "worker_role_id" {
  description = "ID da IAM role do worker Lambda (para policy de acesso ao Neptune)"
  type        = string
}
