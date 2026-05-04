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
variable "neptune_endpoint" {
  description = "Endpoint Neptune"
  type        = string
  default     = ""
}

variable "neptune_cluster_resource_id" {
  description = "Cluster resource ID"
  type        = string
  default     = ""
}

variable "opensearch_endpoint" {
  description = "Endpoint OpenSearch"
  type        = string
  default     = ""
}

variable "layer_arn" {
  description = "ARN layer"
  type        = string
  default     = ""
}

variable "vpc_subnet_ids" {
  description = "Subnets"
  type        = list(string)
  default     = []
}

variable "vpc_security_group_ids" {
  description = "Security groups"
  type        = list(string)
  default     = []
}

