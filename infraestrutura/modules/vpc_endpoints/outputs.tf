output "lambda_security_group_id" {
  description = "SG para usar no Lambda que fica na VPC"
  value       = aws_security_group.lambda.id
}
