# Estrategia de Backend Terraform por Produto

Data: 2026-05-03
Escopo: stacks em infra_produtos/* no padrao tipo_nome.

## Contexto
A separacao por produto foi feita em um unico repositorio, com uma pasta Terraform por produto AWS.

## Opcoes de estado (backend)

### Opcao A - Estado local por pasta (fase de transicao)
- Cada pasta usa estado local proprio.
- Vantagem: simplicidade inicial e baixa friccao.
- Risco: sem lock distribuido; maior risco operacional em equipe.

### Opcao B - Backend remoto por produto (recomendado)
- Um backend S3 por produto, com lock em DynamoDB.
- Vantagem: lock transacional, rastreabilidade e operacao multiusuario.
- Risco: precisa padronizar naming, IAM e bootstrap de backend.

## Recomendacao
Adotar Opcao B para operacao definitiva, mantendo Opcao A apenas durante a migracao inicial.

## Padrao sugerido (Opcao B)
- Bucket de estado: tfstate-langchain-agent-sa-east-1
- Tabela de lock: tfstate-lock-langchain-agent
- Chaves (key) por produto:
  - aws_dynamodb/dev.tfstate
  - aws_sqs/dev.tfstate
  - aws_sns/dev.tfstate
  - aws_s3/dev.tfstate
  - aws_vpc_endpoints/dev.tfstate
  - aws_secrets/dev.tfstate
  - aws_iam/dev.tfstate
  - aws_lambda_layer/dev.tfstate
  - aws_opensearch/dev.tfstate
  - aws_neptune/dev.tfstate
  - aws_neptune_proxy/dev.tfstate
  - aws_neptune_replication/dev.tfstate
  - aws_lambda_worker/dev.tfstate
  - aws_api_gateway/dev.tfstate
  - aws_cloudfront_frontend/dev.tfstate

## Ordem de aplicacao
Seguir a ordem do projeto original, já implementada em deploy_faseado.ps1 e deploy_faseado.sh.

## Parametros de backend por stack
Exemplo de backend.hcl por stack:

bucket         = "tfstate-langchain-agent-sa-east-1"
key            = "aws_lambda_worker/dev.tfstate"
region         = "sa-east-1"
dynamodb_table = "tfstate-lock-langchain-agent"
encrypt        = true

## Passos para endurecimento
1. Criar bucket e tabela de lock de forma centralizada.
2. Criar backend.hcl por produto.
3. Executar terraform init -migrate-state em cada produto na ordem faseada.
4. Validar lock concorrente e rollback por produto.
5. Atualizar runbook final de operacao.

## Criterio de aceite
- Cada produto com estado remoto isolado e lock ativo.
- Deploy faseado executando sem conflito de estado.
- Evidencias de init/plan/apply armazenadas no pacote de reproducao.
