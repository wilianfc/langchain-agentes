output "layer_arn" {
  description = "ARN da Lambda Layer com dependências Python"
  value       = aws_lambda_layer_version.dependencies.arn
}
