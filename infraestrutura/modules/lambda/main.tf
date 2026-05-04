data "archive_file" "controller" {
  type        = "zip"
  source_file = "${path.module}/src/controller.py"
  output_path = "${path.module}/dist/lambda_controller.zip"
}

data "archive_file" "worker" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  excludes    = ["controller.py", "status.py", "ingester.py"]
  output_path = "${path.module}/dist/lambda_worker.zip"
}

data "archive_file" "ingester" {
  type        = "zip"
  source_file = "${path.module}/src/ingester.py"
  output_path = "${path.module}/dist/lambda_ingester.zip"
}

data "archive_file" "status" {
  type        = "zip"
  source_file = "${path.module}/src/status.py"
  output_path = "${path.module}/dist/lambda_status.zip"
}

resource "aws_lambda_function" "controller" {
  function_name    = "${var.project_name}-controller-${var.environment}"
  role             = var.controller_role_arn
  package_type     = "Zip"
  filename         = data.archive_file.controller.output_path
  source_code_hash = data.archive_file.controller.output_base64sha256
  handler          = "controller.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 512
  layers           = [var.layer_arn]

  environment {
    variables = {
      SQS_QUEUE_URL  = var.sqs_queue_url
      DYNAMODB_TABLE = var.dynamodb_table_name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_function" "worker" {
  function_name    = "${var.project_name}-worker-${var.environment}"
  role             = var.worker_role_arn
  package_type     = "Zip"
  filename         = data.archive_file.worker.output_path
  source_code_hash = data.archive_file.worker.output_base64sha256
  handler          = "worker.lambda_handler"
  runtime          = "python3.11"
  timeout          = 900
  memory_size      = 3008
  layers           = [var.layer_arn]

  environment {
    variables = {
      DYNAMODB_TABLE         = var.dynamodb_table_name
      SNS_TOPIC_ARN          = var.sns_topic_arn
      S3_BUCKET              = var.s3_bucket_name
      S3_PREFIX              = "clientes-agente/"
      OPENSEARCH_ENDPOINT    = var.opensearch_endpoint
      NEPTUNE_ENDPOINT       = var.neptune_endpoint
      NEPTUNE_PROXY_FUNCTION = var.neptune_proxy_function
      BEDROCK_MODEL_ID       = var.bedrock_model_id
      BEDROCK_REGION         = var.bedrock_region
      ENABLE_LLM_JUDGE       = var.enable_llm_judge
      ATHENA_DATABASE        = var.athena_database
      ATHENA_OUTPUT_BUCKET   = var.athena_output_bucket
      LANGFUSE_PUBLIC_KEY    = var.langfuse_public_key
      LANGFUSE_SECRET_KEY    = var.langfuse_secret_key
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_event_source_mapping" "sqs_worker" {
  event_source_arn                   = var.sqs_queue_arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0
  function_response_types            = ["ReportBatchItemFailures"]
}

resource "aws_lambda_function" "ingester" {
  function_name    = "${var.project_name}-ingester-${var.environment}"
  role             = var.ingester_role_arn
  package_type     = "Zip"
  filename         = data.archive_file.ingester.output_path
  source_code_hash = data.archive_file.ingester.output_base64sha256
  handler          = "ingester.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 512
  layers           = [var.layer_arn]

  environment {
    variables = {
      OPENSEARCH_ENDPOINT = var.opensearch_endpoint
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lambda_permission" "allow_s3_ingester" {
  count         = var.enable_s3_ingester_trigger ? 1 : 0
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingester.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.s3_bucket_arn
}

resource "aws_s3_bucket_notification" "entrevistas_trigger" {
  count  = var.enable_s3_ingester_trigger ? 1 : 0
  bucket = var.s3_bucket_name_for_trigger

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingester.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "entrevistas/"
    filter_suffix       = ".txt"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingester.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "documentos/"
    filter_suffix       = ".txt"
  }

  depends_on = [aws_lambda_permission.allow_s3_ingester]
}

resource "aws_lambda_function" "status" {
  function_name    = "${var.project_name}-status-${var.environment}"
  role             = var.status_role_arn
  package_type     = "Zip"
  filename         = data.archive_file.status.output_path
  source_code_hash = data.archive_file.status.output_base64sha256
  handler          = "status.lambda_handler"
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 256
  layers           = [var.layer_arn]

  environment {
    variables = {
      DYNAMODB_TABLE = var.dynamodb_table_name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
