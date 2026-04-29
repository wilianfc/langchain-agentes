# ── Lambda de replicação Neptune → OpenSearch ─────────────────────────────────
data "archive_file" "replicator" {
  type        = "zip"
  source_file = "${path.module}/src/replicator.py"
  output_path = "${path.module}/dist/replicator.zip"
}

resource "aws_iam_role" "replicator" {
  name = "${var.project_name}-neptune-replicator-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "replicator" {
  name = "replicator-policy"
  role = aws_iam_role.replicator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["es:ESHttp*"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["neptune-db:ReadDataViaQuery", "neptune-db:GetStreamRecords"]
        Resource = "arn:aws:neptune-db:*:*:${var.neptune_cluster_resource_id}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "replicator" {
  function_name    = "${var.project_name}-neptune-replicator-${var.environment}"
  role             = aws_iam_role.replicator.arn
  filename         = data.archive_file.replicator.output_path
  source_code_hash = data.archive_file.replicator.output_base64sha256
  handler          = "replicator.lambda_handler"
  runtime          = "python3.11"
  timeout          = 300
  memory_size      = 512
  layers           = [var.layer_arn]

  environment {
    variables = {
      OPENSEARCH_ENDPOINT = var.opensearch_endpoint
      NEPTUNE_ENDPOINT    = var.neptune_endpoint
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── EventBridge Schedule — polling a cada 5 minutos ──────────────────────────
resource "aws_cloudwatch_event_rule" "replicator_schedule" {
  name                = "${var.project_name}-neptune-sync-${var.environment}"
  description         = "Polling Neptune Streams → OpenSearch a cada 5 min"
  schedule_expression = "rate(5 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "replicator" {
  rule      = aws_cloudwatch_event_rule.replicator_schedule.name
  target_id = "NeptuneReplicator"
  arn       = aws_lambda_function.replicator.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.replicator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.replicator_schedule.arn
}
