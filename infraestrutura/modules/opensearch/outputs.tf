output "domain_endpoint" {
  description = "Endpoint do domínio OpenSearch (sem https://)"
  value       = aws_opensearch_domain.main.endpoint
}

output "domain_arn" {
  description = "ARN do domínio OpenSearch"
  value       = aws_opensearch_domain.main.arn
}
