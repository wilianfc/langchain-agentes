terraform {
  required_version = ">= 1.0"

  backend "s3" {
    bucket         = "langchain-agent-artifacts-dev"
    key            = "infra_produtos/aws_lambda_layer/terraform.tfstate"
    region         = "sa-east-1"
    dynamodb_table = "langchain-agent-dev"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
