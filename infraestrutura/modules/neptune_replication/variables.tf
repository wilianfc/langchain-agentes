variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "neptune_endpoint" {
  description = "Endpoint de escrita do cluster Neptune"
  type        = string
}

variable "neptune_cluster_resource_id" {
  description = "Resource ID do cluster Neptune (para policy IAM)"
  type        = string
}

variable "opensearch_endpoint" {
  description = "Endpoint do domínio OpenSearch (sem https://)"
  type        = string
}

variable "layer_arn" {
  description = "ARN da Lambda Layer com dependências Python"
  type        = string
}
