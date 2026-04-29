data "archive_file" "proxy" {
  type        = "zip"
  source_file = "${path.module}/src/proxy.py"
  output_path = "${path.module}/dist/proxy.zip"
}

resource "aws_lambda_function" "proxy" {
  function_name    = "${var.project_name}-neptune-proxy-${var.environment}"
  role             = var.worker_role_arn
  filename         = data.archive_file.proxy.output_path
  source_code_hash = data.archive_file.proxy.output_base64sha256
  handler          = "proxy.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256
  layers           = [var.layer_arn]

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  environment {
    variables = {
      NEPTUNE_ENDPOINT = var.neptune_endpoint
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
