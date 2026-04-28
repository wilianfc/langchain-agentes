output "cluster_endpoint" {
  description = "Endpoint de escrita do cluster Neptune"
  value       = aws_neptune_cluster.main.endpoint
}

output "reader_endpoint" {
  description = "Endpoint de leitura do cluster Neptune"
  value       = aws_neptune_cluster.main.reader_endpoint
}

output "cluster_resource_id" {
  description = "Resource ID do cluster (usado em políticas IAM)"
  value       = aws_neptune_cluster.main.cluster_resource_id
}

output "port" {
  description = "Porta do Neptune"
  value       = aws_neptune_cluster.main.port
}
