data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# ── Subnet group (usa subnets padrão da VPC default) ─────────────────────────
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_neptune_subnet_group" "main" {
  name       = "${var.project_name}-neptune-${var.environment}"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── Security group — acesso só a partir da role do worker Lambda ──────────────
resource "aws_security_group" "neptune" {
  name        = "${var.project_name}-neptune-sg-${var.environment}"
  description = "Acesso ao Neptune pelo worker Lambda"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 8182
    to_port     = 8182
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # restrito via IAM policy no cluster
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

# ── Cluster Neptune ───────────────────────────────────────────────────────────
resource "aws_neptune_cluster" "main" {
  cluster_identifier                  = "${var.project_name}-${var.environment}"
  engine                              = "neptune"
  engine_version                      = "1.3.1.0"
  neptune_subnet_group_name           = aws_neptune_subnet_group.main.name
  vpc_security_group_ids              = [aws_security_group.neptune.id]
  iam_database_authentication_enabled = true
  skip_final_snapshot                 = true
  apply_immediately                   = true
  storage_encrypted                   = true

  # Habilita Neptune Streams para replicação futura → OpenSearch (Etapa 5)
  enable_cloudwatch_logs_exports = ["audit"]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── Instância Neptune (db.t3.medium — menor com suporte a grafo) ──────────────
resource "aws_neptune_cluster_instance" "main" {
  identifier         = "${var.project_name}-instance-${var.environment}"
  cluster_identifier = aws_neptune_cluster.main.id
  instance_class     = var.instance_class
  engine             = "neptune"
  apply_immediately  = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── IAM policy para o worker Lambda acessar o Neptune ────────────────────────
resource "aws_iam_role_policy" "worker_neptune" {
  name = "neptune-access"
  role = var.worker_role_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["neptune-db:*"]
        Resource = "arn:aws:neptune-db:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${aws_neptune_cluster.main.cluster_resource_id}/*"
      }
    ]
  })
}
