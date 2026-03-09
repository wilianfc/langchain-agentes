# Terraform para Arquitetura Assíncrona AWS
# ==========================================
# Provisiona toda a infraestrutura necessária para o padrão assíncrono

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "langchain-agent"
}

variable "environment" {
  description = "Ambiente (dev/prod)"
  type        = string
  default     = "dev"
}

# ==============================================================================
# DynamoDB - Armazenamento de Status
# ==============================================================================

resource "aws_dynamodb_table" "requests" {
  name           = "${var.project_name}-requests-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"  # On-demand, sem provisionamento
  hash_key       = "request_id"
  
  attribute {
    name = "request_id"
    type = "S"
  }
  
  # TTL automático para limpar registros antigos
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ==============================================================================
# SQS - Fila Assíncrona
# ==============================================================================

resource "aws_sqs_queue" "agent_queue" {
  name                       = "${var.project_name}-queue-${var.environment}"
  visibility_timeout_seconds = 900  # 15 minutos (tempo máximo de Lambda)
  message_retention_seconds  = 1209600  # 14 dias
  receive_wait_time_seconds  = 10  # Long polling
  
  # Dead Letter Queue para mensagens que falharam após N tentativas
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.agent_dlq.arn
    maxReceiveCount     = 3  # 3 tentativas antes de ir para DLQ
  })
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Dead Letter Queue (DLQ)
resource "aws_sqs_queue" "agent_dlq" {
  name                      = "${var.project_name}-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 dias
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ==============================================================================
# SNS - Notificações
# ==============================================================================

resource "aws_sns_topic" "notifications" {
  name = "${var.project_name}-notifications-${var.environment}"
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Exemplo de subscription por email (opcional)
# resource "aws_sns_topic_subscription" "email" {
#   topic_arn = aws_sns_topic.notifications.arn
#   protocol  = "email"
#   endpoint  = "admin@example.com"
# }

# ==============================================================================
# IAM Roles
# ==============================================================================

# Role para Lambda Controller
resource "aws_iam_role" "lambda_controller" {
  name = "${var.project_name}-lambda-controller-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_controller_policy" {
  name = "controller-policy"
  role = aws_iam_role.lambda_controller.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.requests.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.agent_queue.arn
      }
    ]
  })
}

# Role para Lambda Worker
resource "aws_iam_role" "lambda_worker" {
  name = "${var.project_name}-lambda-worker-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_worker_policy" {
  name = "worker-policy"
  role = aws_iam_role.lambda_worker.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.requests.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.agent_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.notifications.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-artifacts-${var.environment}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:prod/anthropic*"
      },
      {
        Effect = "Allow"
        Action = [
          "es:ESHttp*"
        ]
        Resource = "*"  # Ajustar para OpenSearch específico
      }
    ]
  })
}

# Role para Lambda Status
resource "aws_iam_role" "lambda_status" {
  name = "${var.project_name}-lambda-status-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_status_policy" {
  name = "status-policy"
  role = aws_iam_role.lambda_status.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.requests.arn
      }
    ]
  })
}

# ==============================================================================
# Lambda Functions
# ==============================================================================

# Lambda Controller
resource "aws_lambda_function" "controller" {
  function_name = "${var.project_name}-controller-${var.environment}"
  role          = aws_iam_role.lambda_controller.arn
  
  # Usar container image ou zip
  package_type = "Zip"
  filename     = "lambda_controller.zip"  # Criar com: zip lambda_controller.zip lambda_controller.py
  handler      = "lambda_controller.lambda_handler"
  runtime      = "python3.11"
  
  timeout     = 30  # Rápido, apenas enfileira
  memory_size = 512
  
  environment {
    variables = {
      SQS_QUEUE_URL  = aws_sqs_queue.agent_queue.url
      DYNAMODB_TABLE = aws_dynamodb_table.requests.name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda Worker
resource "aws_lambda_function" "worker" {
  function_name = "${var.project_name}-worker-${var.environment}"
  role          = aws_iam_role.lambda_worker.arn
  
  package_type = "Zip"
  filename     = "lambda_worker.zip"  # Incluir aws_pipeline_clientes.py e dependências
  handler      = "lambda_worker.lambda_handler"
  runtime      = "python3.11"
  
  timeout     = 900  # 15 minutos máximo
  memory_size = 3008  # 3GB para modelos grandes
  
  environment {
    variables = {
      DYNAMODB_TABLE    = aws_dynamodb_table.requests.name
      SNS_TOPIC_ARN     = aws_sns_topic.notifications.arn
      S3_BUCKET         = "${var.project_name}-artifacts-${var.environment}"
      OPENSEARCH_ENDPOINT = var.opensearch_endpoint
      # Adicionar outras variáveis do aws_pipeline_clientes.py
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Event Source Mapping (SQS → Lambda Worker)
resource "aws_lambda_event_source_mapping" "sqs_worker" {
  event_source_arn = aws_sqs_queue.agent_queue.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 1  # Processar 1 mensagem por vez (ajustar conforme necessário)
  
  # Configuração de retry
  maximum_batching_window_in_seconds = 0
  
  # Configuração de erro
  function_response_types = ["ReportBatchItemFailures"]
}

# Lambda Status
resource "aws_lambda_function" "status" {
  function_name = "${var.project_name}-status-${var.environment}"
  role          = aws_iam_role.lambda_status.arn
  
  package_type = "Zip"
  filename     = "lambda_status.zip"
  handler      = "lambda_status.lambda_handler"
  runtime      = "python3.11"
  
  timeout     = 10
  memory_size = 256
  
  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.requests.name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ==============================================================================
# API Gateway
# ==============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["*"]
  }
}

# Stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# Integração: POST /query → Lambda Controller
resource "aws_apigatewayv2_integration" "controller" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  
  integration_uri    = aws_lambda_function.controller.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "query" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /query"
  target    = "integrations/${aws_apigatewayv2_integration.controller.id}"
}

# Integração: GET /status/{request_id} → Lambda Status
resource "aws_apigatewayv2_integration" "status" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  
  integration_uri    = aws_lambda_function.status.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "status" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /status/{request_id}"
  target    = "integrations/${aws_apigatewayv2_integration.status.id}"
}

# Permissões para API Gateway invocar Lambdas
resource "aws_lambda_permission" "controller" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.controller.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "status" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ==============================================================================
# Outputs
# ==============================================================================

output "api_endpoint" {
  description = "URL da API"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "dynamodb_table" {
  description = "Nome da tabela DynamoDB"
  value       = aws_dynamodb_table.requests.name
}

output "sqs_queue_url" {
  description = "URL da fila SQS"
  value       = aws_sqs_queue.agent_queue.url
}

output "sns_topic_arn" {
  description = "ARN do tópico SNS"
  value       = aws_sns_topic.notifications.arn
}

variable "opensearch_endpoint" {
  description = "Endpoint do OpenSearch (criar separadamente)"
  type        = string
  default     = ""
}
