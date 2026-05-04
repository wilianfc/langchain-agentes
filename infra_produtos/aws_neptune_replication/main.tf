module "product" {
  source = "../../infraestrutura/modules/neptune_replication"
  project_name = var.project_name
  environment = var.environment
  neptune_endpoint = var.neptune_endpoint
  neptune_cluster_resource_id = var.neptune_cluster_resource_id
  opensearch_endpoint = var.opensearch_endpoint
  layer_arn = var.layer_arn
  vpc_subnet_ids = var.vpc_subnet_ids
  vpc_security_group_ids = var.vpc_security_group_ids
}

