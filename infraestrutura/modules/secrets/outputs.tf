output "anthropic_secret_arn" {
  description = "ARN do secret da Anthropic no Secrets Manager"
  value       = aws_secretsmanager_secret.anthropic.arn
}
