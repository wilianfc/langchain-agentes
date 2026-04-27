output "bucket_name" {
  description = "Nome do bucket S3 de artefatos"
  value       = aws_s3_bucket.artifacts.id
}

output "bucket_arn" {
  description = "ARN do bucket S3 de artefatos"
  value       = aws_s3_bucket.artifacts.arn
}
