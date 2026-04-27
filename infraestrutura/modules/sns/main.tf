resource "aws_sns_topic" "notifications" {
  name = "${var.project_name}-notifications-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
