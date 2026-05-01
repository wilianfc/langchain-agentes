terraform {
  required_version = ">= 1.0"
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

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

module "dynamodb" {
  source       = "./modules/dynamodb"
  project_name = var.project_name
  environment  = var.environment
}

module "sqs" {
  source       = "./modules/sqs"
  project_name = var.project_name
  environment  = var.environment
}

module "sns" {
  source       = "./modules/sns"
  project_name = var.project_name
  environment  = var.environment
}

module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

module "iam" {
  source             = "./modules/iam"
  project_name       = var.project_name
  environment        = var.environment
  dynamodb_table_arn = module.dynamodb.table_arn
  sqs_queue_arn      = module.sqs.queue_arn
  sns_topic_arn      = module.sns.topic_arn
  s3_bucket_arn      = module.s3.bucket_arn
}

module "opensearch" {
  source               = "./modules/opensearch"
  project_name         = var.project_name
  environment          = var.environment
  worker_role_arn      = module.iam.lambda_worker_role_arn
  extra_principal_arns = var.opensearch_extra_arns
}

module "neptune" {
  source         = "./modules/neptune"
  project_name   = var.project_name
  environment    = var.environment
  worker_role_id = module.iam.lambda_worker_role_id
}

module "vpc_endpoints" {
  source       = "./modules/vpc_endpoints"
  project_name = var.project_name
  environment  = var.environment
}

module "lambda_layer" {
  source         = "./modules/lambda_layer"
  project_name   = var.project_name
  environment    = var.environment
  s3_bucket_name = module.s3.bucket_name
  depends_on     = [module.s3]
}

module "neptune_proxy" {
  source                 = "./modules/neptune_proxy"
  project_name           = var.project_name
  environment            = var.environment
  neptune_endpoint       = module.neptune.cluster_endpoint
  worker_role_arn        = module.iam.lambda_worker_role_arn
  vpc_subnet_ids         = data.aws_subnets.default.ids
  vpc_security_group_ids = [module.vpc_endpoints.lambda_security_group_id]
  layer_arn              = module.lambda_layer.layer_arn
  depends_on             = [module.neptune, module.vpc_endpoints, module.lambda_layer]
}

module "lambda" {
  source                     = "./modules/lambda"
  project_name               = var.project_name
  environment                = var.environment
  controller_role_arn        = module.iam.lambda_controller_role_arn
  worker_role_arn            = module.iam.lambda_worker_role_arn
  status_role_arn            = module.iam.lambda_status_role_arn
  ingester_role_arn          = module.iam.lambda_ingester_role_arn
  sqs_queue_url              = module.sqs.queue_url
  sqs_queue_arn              = module.sqs.queue_arn
  dynamodb_table_name        = module.dynamodb.table_name
  sns_topic_arn              = module.sns.topic_arn
  opensearch_endpoint        = module.opensearch.domain_endpoint
  neptune_endpoint           = module.neptune.cluster_endpoint
  neptune_proxy_function     = module.neptune_proxy.function_name
  s3_bucket_name             = module.s3.bucket_name
  s3_bucket_name_for_trigger = module.s3.bucket_name
  s3_bucket_arn              = module.s3.bucket_arn
  layer_arn                  = module.lambda_layer.layer_arn
  enable_llm_judge           = "false"
  athena_database            = var.athena_database
  athena_output_bucket       = var.athena_output_bucket
  langfuse_public_key        = var.langfuse_public_key
  langfuse_secret_key        = var.langfuse_secret_key
  depends_on                 = [module.neptune_proxy]
}

module "neptune_replication" {
  source                      = "./modules/neptune_replication"
  project_name                = var.project_name
  environment                 = var.environment
  neptune_endpoint            = module.neptune.cluster_endpoint
  neptune_cluster_resource_id = module.neptune.cluster_resource_id
  opensearch_endpoint         = module.opensearch.domain_endpoint
  layer_arn                   = module.lambda_layer.layer_arn
  vpc_subnet_ids              = data.aws_subnets.default.ids
  vpc_security_group_ids      = [module.vpc_endpoints.lambda_security_group_id]
  depends_on                  = [module.neptune, module.opensearch, module.lambda_layer, module.vpc_endpoints]
}

module "api_gateway" {
  source                   = "./modules/api_gateway"
  project_name             = var.project_name
  environment              = var.environment
  controller_invoke_arn    = module.lambda.controller_invoke_arn
  controller_function_name = module.lambda.controller_function_name
  status_invoke_arn        = module.lambda.status_invoke_arn
  status_function_name     = module.lambda.status_function_name
  ingester_invoke_arn      = module.lambda.ingester_invoke_arn
  ingester_function_name   = module.lambda.ingester_function_name
  depends_on               = [module.lambda]
}
