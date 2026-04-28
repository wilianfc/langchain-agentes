output "replicator_function_name" {
  description = "Nome da Lambda de replicação Neptune → OpenSearch"
  value       = aws_lambda_function.replicator.function_name
}

output "sync_index" {
  description = "Nome do índice OpenSearch com snapshot do grafo Neptune"
  value       = "neptune-graph-sync"
}
