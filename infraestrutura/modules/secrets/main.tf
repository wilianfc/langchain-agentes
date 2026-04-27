resource "aws_secretsmanager_secret" "anthropic" {
  name                    = "prod/anthropic/api-key"
  description             = "Chave de API da Anthropic (Claude)"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "anthropic" {
  secret_id     = aws_secretsmanager_secret.anthropic.id
  secret_string = var.anthropic_api_key
}
