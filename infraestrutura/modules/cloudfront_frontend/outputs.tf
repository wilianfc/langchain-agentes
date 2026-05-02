output "distribution_domain_name" {
  description = "Domínio da distribuição CloudFront do frontend"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "distribution_id" {
  description = "ID da distribuição CloudFront"
  value       = aws_cloudfront_distribution.frontend.id
}

output "bucket_name" {
  description = "Bucket S3 privado que armazena os arquivos estáticos do frontend"
  value       = aws_s3_bucket.frontend.id
}
