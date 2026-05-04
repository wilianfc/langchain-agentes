# Infra por Produto (Fase 2)

Este diretorio separa a infraestrutura em pastas por produto no padrao tipo_nome.

## Ordem de deploy (baseada no projeto original)
1. aws_dynamodb
2. aws_sqs
3. aws_sns
4. aws_s3
5. aws_vpc_endpoints
6. aws_secrets
7. aws_iam
8. aws_lambda_layer
9. aws_opensearch
10. aws_neptune
11. aws_neptune_proxy
12. aws_neptune_replication
13. aws_lambda_worker
14. aws_api_gateway
15. aws_cloudfront_frontend

## Execucao
Windows:
- pwsh -File infra_produtos/deploy_faseado.ps1 -Mode validate
- pwsh -File infra_produtos/deploy_faseado.ps1 -Mode plan

Linux:
- bash infra_produtos/deploy_faseado.sh validate
- bash infra_produtos/deploy_faseado.sh plan

Observacao:
- Nesta fase, os stacks foram especializados por produto e validados estruturalmente.
- O acoplamento de estados remotos por produto sera definido no proximo passo de endurecimento de backend.
