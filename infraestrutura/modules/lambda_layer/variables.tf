variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev/prod)"
  type        = string
}

variable "s3_bucket_name" {
  description = "Bucket S3 para upload do layer zip (necessário quando zip > 50 MB)"
  type        = string
}
