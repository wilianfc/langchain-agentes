output "queue_url" {
  description = "URL da fila SQS"
  value       = aws_sqs_queue.agent_queue.url
}

output "queue_arn" {
  description = "ARN da fila SQS"
  value       = aws_sqs_queue.agent_queue.arn
}

output "dlq_arn" {
  description = "ARN da Dead Letter Queue"
  value       = aws_sqs_queue.agent_dlq.arn
}
