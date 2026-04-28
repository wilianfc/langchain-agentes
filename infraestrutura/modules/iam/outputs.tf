output "lambda_controller_role_arn" {
  description = "ARN da role do Lambda Controller"
  value       = aws_iam_role.lambda_controller.arn
}

output "lambda_worker_role_arn" {
  description = "ARN da role do Lambda Worker"
  value       = aws_iam_role.lambda_worker.arn
}

output "lambda_status_role_arn" {
  description = "ARN da role do Lambda Status"
  value       = aws_iam_role.lambda_status.arn
}

output "lambda_worker_role_id" {
  description = "ID da role do Lambda Worker (para políticas inline de outros módulos)"
  value       = aws_iam_role.lambda_worker.id
}
