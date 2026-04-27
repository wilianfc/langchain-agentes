output "topic_arn" {
  description = "ARN do tópico SNS"
  value       = aws_sns_topic.notifications.arn
}
