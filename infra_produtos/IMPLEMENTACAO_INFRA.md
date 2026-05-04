# Runbook de Implementação — Infraestrutura AWS por Produto

> **Público**: Time de Infraestrutura  
> **Projeto**: langchain-agent  
> **Conta AWS**: 113677611404  
> **Região**: sa-east-1  
> **Última atualização**: 2026-05-03

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Estrutura de diretórios](#2-estrutura-de-diretórios)
3. [Ordem de dependência entre produtos](#3-ordem-de-dependência-entre-produtos)
4. [Configuração inicial do engenheiro](#4-configuração-inicial-do-engenheiro)
5. [Deploy faseado](#5-deploy-faseado)
6. [Rollback e destroy](#6-rollback-e-destroy)
7. [Troubleshooting](#7-troubleshooting)
8. [Checklist de compliance BACEN / LGPD](#8-checklist-de-compliance-bacen--lgpd)

---

## 1. Pré-requisitos

### 1.1 Ferramentas locais

| Ferramenta | Versão mínima | Verificação |
|---|---|---|
| Terraform | >= 1.0 | `terraform version` |
| AWS CLI | >= 2.x | `aws --version` |
| PowerShell | >= 7.2 | `pwsh --version` |
| Git | >= 2.x | `git --version` |

### 1.2 Perfil IAM do engenheiro

O deploy exige permissões nas seguintes categorias:

```
AmazonDynamoDBFullAccess
AmazonSQSFullAccess
AmazonSNSFullAccess
AmazonS3FullAccess
IAMFullAccess
AmazonOpenSearchServiceFullAccess
NeptuneFullAccess
AmazonVPCFullAccess
AWSLambda_FullAccess
AmazonAPIGatewayAdministrator
CloudFrontFullAccess
SecretsManagerReadWrite
AmazonBedrockFullAccess
```

> **Recomendação**: criar um perfil IAM dedicado `langchain-infra-deployer` com política customizada restrita às ações acima no escopo do projeto (`arn:aws:*:sa-east-1:113677611404:*langchain-agent*`).

### 1.3 Configuração do perfil AWS CLI

```powershell
# Criar perfil nomeado (recomendado sobre default)
aws configure --profile langchain-infra

# Campos:
# AWS Access Key ID     : <sua-access-key>
# AWS Secret Access Key : <sua-secret-key>
# Default region name   : sa-east-1
# Default output format : json

# Exportar para sessão PowerShell atual
$env:AWS_PROFILE = "langchain-infra"
$env:AWS_REGION  = "sa-east-1"

# Verificar identidade
aws sts get-caller-identity --profile langchain-infra
```

Saída esperada:
```json
{
  "UserId": "AIDAXXXXXXXXXXXXXXXXX",
  "Account": "113677611404",
  "Arn": "arn:aws:iam::113677611404:user/<seu-usuario>"
}
```

### 1.4 MFA (se habilitado na conta)

Se a conta exigir MFA para ações destrutivas:

```powershell
# Obter credenciais temporárias com MFA
$TOKEN_CODE = "<codigo-6-digitos-do-autenticador>"
$MFA_ARN    = "arn:aws:iam::113677611404:mfa/<seu-usuario>"

$creds = aws sts get-session-token `
  --serial-number $MFA_ARN `
  --token-code $TOKEN_CODE `
  --profile langchain-infra | ConvertFrom-Json

$env:AWS_ACCESS_KEY_ID     = $creds.Credentials.AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $creds.Credentials.SecretAccessKey
$env:AWS_SESSION_TOKEN     = $creds.Credentials.SessionToken
```

As credenciais temporárias têm validade de 12h por padrão.

### 1.5 VPN / Acesso à rede

- O cluster Neptune está em VPC privada. Para rodar comandos Terraform que consultam endpoints Neptune, o engenheiro deve estar conectado à VPN corporativa ou operar via bastion host na mesma VPC.
- OpenSearch também é provisionado em VPC; o endpoint interno não é roteável publicamente.
- O deploy Terraform em si **não** exige VPN — apenas operações de teste de conectividade direto ao cluster exigem.

### 1.6 Backend S3 — permissões adicionais

O state remoto usa:
- **Bucket**: `langchain-agent-artifacts-dev`
- **Tabela DynamoDB lock**: `langchain-agent-dev`

O perfil IAM do deployer precisa ter acesso a:
```
s3:GetObject, s3:PutObject, s3:DeleteObject  em langchain-agent-artifacts-dev/infra_produtos/*
dynamodb:GetItem, dynamodb:PutItem, dynamodb:DeleteItem  em langchain-agent-dev
```

---

## 2. Estrutura de diretórios

```
infra_produtos/
├── aws_dynamodb/           # Tabela principal langchain-agent-dev
├── aws_sqs/                # Fila de processamento assíncrono
├── aws_sns/                # Tópico de notificações
├── aws_s3/                 # Bucket de artefatos
├── aws_vpc_endpoints/      # VPC Endpoints: S3, DynamoDB, Bedrock
├── aws_secrets/            # Secrets Manager (chaves de API)
├── aws_iam/                # Roles e policies de execução
├── aws_lambda_layer/       # Layer Python compartilhado
├── aws_opensearch/         # Domínio OpenSearch 2.11
├── aws_neptune/            # Cluster Neptune 1.3.2.1
├── aws_neptune_proxy/      # Lambda proxy de consultas Neptune
├── aws_neptune_replication/# Lambda de replicação + EventBridge
├── aws_lambda_worker/      # Lambda worker, controller, ingester, status
├── aws_api_gateway/        # HTTP API Gateway
├── aws_cloudfront_frontend/# CloudFront + S3 para console web
│
├── deploy_faseado.ps1      # Orquestrador PowerShell (validate/plan/apply)
├── deploy_faseado.sh       # Orquestrador Bash (Linux nativo)
├── migrate_backend.ps1     # Script de migração de backend S3
├── ESTRATEGIA_BACKEND.md   # Documentação da estratégia de state remoto
└── IMPLEMENTACAO_INFRA.md  # Este arquivo
```

Cada pasta de produto contém:
```
<produto>/
├── versions.tf    # Terraform/providers + backend S3
├── variables.tf   # Variáveis de entrada do produto
├── main.tf        # Módulo apontando para infraestrutura/modules/<produto>
└── outputs.tf     # Outputs exportados pelo produto
```

---

## 3. Ordem de dependência entre produtos

A ordem abaixo é obrigatória para `apply`. O `destroy` deve ser feito na ordem inversa.

```
 1. aws_dynamodb              (sem dependências externas)
 2. aws_sqs                   (sem dependências externas)
 3. aws_sns                   (sem dependências externas)
 4. aws_s3                    (sem dependências externas)
 5. aws_vpc_endpoints         (depende de VPC existente)
 6. aws_secrets               (sem dependências externas)
 7. aws_iam                   (depende de: s3, dynamodb, sqs, opensearch, neptune, bedrock ARNs)
 8. aws_lambda_layer          (depende de: s3 — bucket para upload do layer)
 9. aws_opensearch            (depende de: iam — roles de acesso)
10. aws_neptune               (depende de: iam — cluster role)
11. aws_neptune_proxy         (depende de: neptune, lambda_layer, iam)
12. aws_neptune_replication   (depende de: neptune, lambda_layer, iam, dynamodb)
13. aws_lambda_worker         (depende de: dynamodb, sqs, s3, opensearch, neptune, lambda_layer, iam, secrets)
14. aws_api_gateway           (depende de: lambda_worker — ARN da função)
15. aws_cloudfront_frontend   (depende de: s3 — bucket do frontend)
```

> O script `deploy_faseado.ps1` já codifica essa ordem e executa em sequência automaticamente.

---

## 4. Configuração inicial do engenheiro

### 4.1 Clonar o repositório

```powershell
git clone <url-do-repositorio> C:\Documentos\langchain
cd C:\Documentos\langchain
```

### 4.2 Configurar variáveis sensíveis

Criar arquivo `infra_produtos/<produto>/terraform.tfvars` para produtos que exigem variáveis sensíveis. Nunca commitar arquivos `.tfvars` com secrets.

Variáveis obrigatórias para `aws_opensearch`:
```hcl
# infra_produtos/aws_opensearch/terraform.tfvars
opensearch_extra_arns = ["arn:aws:iam::113677611404:user/<seu-usuario>"]
```

Variáveis opcionais globais (se quiser sobrescrever defaults):
```hcl
aws_region   = "sa-east-1"
project_name = "langchain-agent"
environment  = "dev"
```

### 4.3 Inicializar backends (primeira vez)

Se os backends já foram migrados (como neste projeto), apenas inicializar:

```powershell
cd C:\Documentos\langchain
pwsh -File .\infra_produtos\migrate_backend.ps1 -Mode reconfigure
```

Para dry-run (sem executar, apenas listar):
```powershell
pwsh -File .\infra_produtos\migrate_backend.ps1 -Mode reconfigure -DryRun
```

---

## 5. Deploy faseado

### 5.1 Validar sintaxe de todos os produtos

```powershell
cd C:\Documentos\langchain
pwsh -File .\infra_produtos\deploy_faseado.ps1 -Mode validate
```

Resultado esperado: 15/15 `Success! The configuration is valid.`

### 5.2 Plan — revisar mudanças antes de aplicar

```powershell
pwsh -File .\infra_produtos\deploy_faseado.ps1 -Mode plan
```

Revisar o output de cada produto antes de prosseguir. Preste atenção especial em:
- Recursos marcados como `destroy` (vermelho/`-`)
- Mudanças em `aws_opensearch_domain` (podem causar blue/green com downtime)
- Mudanças em `aws_neptune_cluster` (podem causar failover)

### 5.3 Apply — provisionar infraestrutura

```powershell
pwsh -File .\infra_produtos\deploy_faseado.ps1 -Mode apply
```

O script executa `terraform apply -auto-approve` em cada produto na ordem correta.

> **Atenção**: o apply do OpenSearch pode levar 15-30 minutos na primeira criação.  
> O apply do Neptune pode levar 10-20 minutos na primeira criação.

### 5.4 Deploy de produto único (manutenção)

```powershell
# Exemplo: aplicar apenas lambda_worker
cd C:\Documentos\langchain\infra_produtos\aws_lambda_worker
terraform plan
terraform apply -auto-approve
```

### 5.5 Verificar outputs após apply

```powershell
# Dentro de cada produto
cd C:\Documentos\langchain\infra_produtos\aws_api_gateway
terraform output

# Saídas esperadas do projeto completo:
# api_endpoint          = https://ak0b2w5wcb.execute-api.sa-east-1.amazonaws.com/
# opensearch_endpoint   = search-langchain-agent-dev-<hash>.sa-east-1.es.amazonaws.com
# s3_bucket_name        = langchain-agent-artifacts-dev
# neptune_endpoint      = <cluster>.cluster-<id>.sa-east-1.neptune.amazonaws.com
# frontend_url          = https://<hash>.cloudfront.net
```

---

## 6. Rollback e destroy

### 6.1 Rollback de um produto específico

```powershell
cd C:\Documentos\langchain\infra_produtos\aws_lambda_worker

# Ver state atual
terraform state list

# Reverter para versão anterior via state (se o erro foi de config, não de infra)
git checkout HEAD~1 -- infra_produtos/aws_lambda_worker/main.tf
terraform plan
terraform apply -auto-approve
```

### 6.2 Destroy completo (ordem inversa obrigatória)

```powershell
# ATENÇÃO: operação destrutiva e irreversível
# Executar produto por produto na ordem inversa

$ORDEM_REVERSA = @(
    "aws_cloudfront_frontend",
    "aws_api_gateway",
    "aws_lambda_worker",
    "aws_neptune_replication",
    "aws_neptune_proxy",
    "aws_neptune",
    "aws_opensearch",
    "aws_lambda_layer",
    "aws_iam",
    "aws_secrets",
    "aws_vpc_endpoints",
    "aws_s3",
    "aws_sns",
    "aws_sqs",
    "aws_dynamodb"
)

foreach ($produto in $ORDEM_REVERSA) {
    Write-Host "Destroyando $produto..." -ForegroundColor Red
    terraform -chdir=".\infra_produtos\$produto" destroy -auto-approve
}
```

> **Dados persistentes**: antes de destruir `aws_dynamodb` e `aws_s3`, exportar/backup de dados críticos.

---

## 7. Troubleshooting

### Erro: `Error acquiring the state lock`

```
Error: Error acquiring the state lock
  Lock Info: ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Solução: verificar se outro processo Terraform está rodando. Se travar por crash:
```powershell
cd C:\Documentos\langchain\infra_produtos\<produto>
terraform force-unlock <LOCK-ID>
```

### Erro: `InvalidTypeException` no OpenSearch (apply inicial)

O principal adicionado na access policy ainda não existe (ex: role IAM sendo criada no mesmo apply).

**Solução**: remover o ARN problemático de `opensearch_extra_arns`, fazer apply, depois adicionar com `terraform apply` incremental.

Ref: [opensearch_access.auto.tfvars](../infraestrutura/opensearch_access.auto.tfvars)

### Erro: `Invalid count argument` no módulo Lambda

Ocorre quando `count` depende de valor desconhecido em plan time.

**Solução já aplicada**: uso de variável booleana `enable_s3_ingester_trigger`.  
Ref: [modules/lambda/main.tf](../infraestrutura/modules/lambda/main.tf)

### Erro: `Error: configuring S3 Backend` — acesso negado

```
Error: error configuring S3 Backend: error validating provider credentials
```

Verificar:
1. `aws sts get-caller-identity` retorna conta `113677611404`
2. Perfil IAM tem acesso ao bucket `langchain-agent-artifacts-dev`
3. Variável `AWS_PROFILE` está exportada na sessão

### Deploy trava no OpenSearch / Neptune (longo)

Comportamento esperado — ambos os serviços têm provisionamento lento:
- OpenSearch: até 30 min na criação
- Neptune: até 20 min na criação

Não interromper o processo. Monitorar no console AWS se necessário.

---

## 8. Checklist de compliance BACEN / LGPD

> Aplicar antes de qualquer deploy em ambiente que processe dados de clientes reais.

### 8.1 Criptografia em repouso

- [ ] DynamoDB: criptografia gerenciada por AWS KMS habilitada (`server_side_encryption`)
- [ ] S3: `server_side_encryption_configuration` com AES-256 ou KMS
- [ ] OpenSearch: `encrypt_at_rest.enabled = true` configurado no módulo
- [ ] Neptune: `storage_encrypted = true` no cluster
- [ ] Secrets Manager: criptografia com KMS habilitada por padrão (verificar chave CMK vs. AWS managed)
- [ ] Backend S3 do Terraform state: `encrypt = true` ✅ (já configurado)

### 8.2 Criptografia em trânsito

- [ ] OpenSearch: `node_to_node_encryption.enabled = true`
- [ ] OpenSearch: `domain_endpoint_options.enforce_https = true`
- [ ] Neptune: conexões via TLS obrigatório (parâmetro `neptune_enable_audit_log`)
- [ ] API Gateway: apenas HTTPS (sem HTTP endpoint exposto)
- [ ] CloudFront: `viewer_protocol_policy = "redirect-to-https"`

### 8.3 Controle de acesso

- [ ] Nenhuma política IAM com `"*"` em `Action` e `"*"` em `Resource` simultaneamente
- [ ] Roles Lambda com princípio de menor privilégio (somente serviços que a função acessa)
- [ ] OpenSearch com access policy explícita (sem `Principal: *`)
- [ ] Bucket S3 de artefatos com `block_public_access = true`
- [ ] Bucket S3 do frontend com acesso somente via CloudFront OAC/OAI
- [ ] Neptune acessível somente de dentro da VPC (sem endpoint público)
- [ ] Secrets Manager: rotation habilitada para chaves de longa duração

### 8.4 Auditoria e rastreabilidade (BACEN Res. 4.658 / 4.893)

- [ ] AWS CloudTrail habilitado na conta com retenção mínima de 1 ano
- [ ] Logs de acesso ao S3 habilitados (`logging` block no módulo aws_s3)
- [ ] CloudWatch Logs habilitado para todas as funções Lambda (retention >= 90 dias)
- [ ] OpenSearch slow logs habilitados em produção
- [ ] Neptune audit log habilitado via cluster parameter group
- [ ] Tags obrigatórias em todos os recursos: `Projeto`, `Ambiente`, `Responsavel`, `Classificacao-Dado`

### 8.5 LGPD — dados pessoais e sensíveis

- [ ] Identificar quais recursos podem conter dados pessoais (DynamoDB, OpenSearch, S3 de entrevistas)
- [ ] Garantir que dados pessoais **não** são gravados em logs do CloudWatch sem mascaramento
- [ ] Política de retenção definida para dados em S3 (lifecycle rules)
- [ ] Processo documentado para atendimento de direito de exclusão (Art. 18 LGPD)
- [ ] Análise de impacto de privacidade (RIPD) realizada antes do deploy em produção

### 8.6 Resiliência e continuidade (BACEN Res. 4.658 art. 13)

- [ ] Neptune com Multi-AZ habilitado em produção (`availability_zones` com >= 2 zonas)
- [ ] OpenSearch com `zone_awareness_enabled = true` e 2+ nós em produção
- [ ] SQS com DLQ configurada (Dead Letter Queue para falhas de processamento)
- [ ] Backup automático habilitado no Neptune (`backup_retention_period >= 7` dias)
- [ ] RTO e RPO documentados e validados com o time de negócio

### 8.7 Rede e perímetro

- [ ] VPC Endpoints provisionados para S3, DynamoDB e Bedrock (evitar tráfego pela internet)
- [ ] Security Groups revisados — sem regras `0.0.0.0/0` em inbound para portas sensíveis
- [ ] WAF associado ao CloudFront em produção
- [ ] Shield Standard ativo por padrão (verificar necessidade de Shield Advanced)

---

*Documento gerado em 2026-05-03. Atualizar a cada mudança significativa de arquitetura.*
