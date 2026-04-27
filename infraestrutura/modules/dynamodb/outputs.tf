output "table_name" {
  description = "Nome da tabela DynamoDB"
  value       = aws_dynamodb_table.requests.name
}

output "table_arn" {
  description = "ARN da tabela DynamoDB"
  value       = aws_dynamodb_table.requests.arn
}
