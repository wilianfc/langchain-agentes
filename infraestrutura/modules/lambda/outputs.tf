output "controller_invoke_arn" {
  description = "ARN de invocação do Lambda Controller"
  value       = aws_lambda_function.controller.invoke_arn
}

output "controller_function_name" {
  description = "Nome do Lambda Controller"
  value       = aws_lambda_function.controller.function_name
}

output "status_invoke_arn" {
  description = "ARN de invocação do Lambda Status"
  value       = aws_lambda_function.status.invoke_arn
}

output "status_function_name" {
  description = "Nome do Lambda Status"
  value       = aws_lambda_function.status.function_name
}

output "ingester_invoke_arn" {
  description = "ARN de invocação do Lambda Ingester"
  value       = aws_lambda_function.ingester.invoke_arn
}

output "ingester_function_name" {
  description = "Nome do Lambda Ingester"
  value       = aws_lambda_function.ingester.function_name
}
