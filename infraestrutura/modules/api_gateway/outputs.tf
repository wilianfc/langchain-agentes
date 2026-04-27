output "api_endpoint" {
  description = "URL da API"
  value       = aws_apigatewayv2_stage.default.invoke_url
}
