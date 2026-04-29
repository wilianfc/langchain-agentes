variable "project_name" { type = string }
variable "environment" { type = string }
variable "neptune_endpoint" { type = string }
variable "worker_role_arn" {
  description = "ARN da role do worker (tem acesso Neptune)"
  type        = string
}
variable "vpc_subnet_ids" { type = list(string) }
variable "vpc_security_group_ids" { type = list(string) }
variable "layer_arn" { type = string }
