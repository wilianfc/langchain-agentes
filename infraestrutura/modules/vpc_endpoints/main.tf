data "aws_region" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_route_tables" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ── Security group para Lambda na VPC ────────────────────────────────────────
resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-lambda-vpc-${var.environment}"
  description = "SG do Lambda worker na VPC (acesso Neptune + VPC endpoints)"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── S3 Gateway Endpoint (gratuito) ────────────────────────────────────────────
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = data.aws_route_tables.default.ids

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── Bedrock Runtime Interface Endpoint ───────────────────────────────────────
resource "aws_security_group" "bedrock_endpoint" {
  name        = "${var.project_name}-bedrock-ep-${var.environment}"
  description = "SG do VPC endpoint Bedrock Runtime"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port                = 443
    to_port                  = 443
    protocol                 = "tcp"
    security_groups          = [aws_security_group.lambda.id]
    description              = "HTTPS do Lambda"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_vpc_endpoint" "bedrock_runtime" {
  vpc_id              = data.aws_vpc.default.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.bedrock_endpoint.id]
  private_dns_enabled = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── DynamoDB Gateway Endpoint (gratuito) ─────────────────────────────────────
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = data.aws_route_tables.default.ids

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
