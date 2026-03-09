# Migração para Arquitetura Assíncrona

## 🎯 Objetivo

Resolver o problema de **timeout de 30 segundos** no API Gateway implementando um padrão assíncrono com:
- Resposta imediata ao cliente (< 1s)
- Processamento em background (até 15 minutos)
- Consulta de status via polling
- Notificações via SNS

---

## 📊 Comparação: Arquitetura Atual vs. Nova

| Aspecto | Síncrona (Atual) | Assíncrona (Nova) |
|---------|------------------|-------------------|
| **Timeout API** | 30 segundos ❌ | Sem limite ✅ |
| **Tempo de resposta** | Espera processar tudo | < 1 segundo |
| **Experiência do usuário** | Bloqueado aguardando | Polling ou notificação |
| **Escalabilidade** | Limitada | Alta (fila gerencia backlog) |
| **Retry automático** | Não | Sim (SQS DLQ) |
| **Monitoramento** | Limitado | Completo (CloudWatch + status) |
| **Custo** | Médio | Otimizado (pay-per-use) |

---

## 🏗️ Arquitetura Nova

```
┌─────────────────────────────────────────────────────────────────────┐
│ Cliente                                                              │
│   ↓ POST /query                                                      │
│   ↓ {cliente_id, dados_cliente, pergunta}                           │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ API Gateway (HTTP REST)                                              │
│   → Sem timeout (resposta < 1s)                                      │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Lambda Controller (lambda_controller.py)                             │
│   1. Gera request_id único                                           │
│   2. Salva status=PENDING no DynamoDB                                │
│   3. Enfileira mensagem no SQS                                       │
│   4. ← Retorna {request_id, status: "PENDING"} imediatamente         │
└─────────────────────────────────────────────────────────────────────┘
          ↓ (enfileirado)                      ↑ (polling)
┌─────────────────────┐              ┌────────────────────────┐
│ SQS Queue           │              │ Cliente consulta       │
│ (buffer assíncrono) │              │ GET /status/{id}       │
└─────────────────────┘              └────────────────────────┘
          ↓ (trigger)                          ↑
┌─────────────────────────────────────────────────────────────────────┐
│ Lambda Worker (lambda_worker.py)                                     │
│   1. Consome mensagem da fila                                        │
│   2. Atualiza status=PROCESSING                                      │
│   3. Executa pipeline LangChain (5-15 minutos) ⏱️                    │
│   4. Salva resultado no DynamoDB                                     │
│   5. Atualiza status=COMPLETED                                       │
│   6. Publica notificação no SNS                                      │
└─────────────────────────────────────────────────────────────────────┘
          ↓ (consulta/atualiza)                ↓ (notifica)
┌──────────────────────┐              ┌────────────────────────┐
│ DynamoDB             │              │ SNS Topic              │
│ - request_id (PK)    │              │ (webhook/email)        │
│ - status             │              └────────────────────────┘
│ - result             │
│ - timestamps         │
└──────────────────────┘
          ↑
          │ (lê status)
┌─────────────────────────────────────────────────────────────────────┐
│ Lambda Status (lambda_status.py)                                     │
│   GET /status/{request_id}                                           │
│   → Retorna: {status, result, timestamps}                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Novos Arquivos Criados

### 1. **lambda_controller.py**
Lambda que recebe requisições e retorna `request_id` imediatamente.
- ✅ Sem timeout (< 1s de execução)
- ✅ Enfileira no SQS
- ✅ Salva status inicial no DynamoDB

### 2. **lambda_worker.py**
Lambda que processa mensagens da fila em background.
- ✅ Timeout: 15 minutos (suficiente para LLMs)
- ✅ Importa `aws_pipeline_clientes.py` (código existente)
- ✅ Atualiza status no DynamoDB
- ✅ Retry automático via SQS

### 3. **lambda_status.py**
Lambda para consultar status e resultado.
- ✅ Endpoint: `GET /status/{request_id}`
- ✅ Retorna PENDING/PROCESSING/COMPLETED/FAILED

### 4. **terraform_async_infra.tf**
Infraestrutura como código para provisionar:
- ✅ DynamoDB (status storage)
- ✅ SQS Queue + DLQ (fila assíncrona)
- ✅ SNS Topic (notificações)
- ✅ 3 Lambdas (Controller, Worker, Status)
- ✅ API Gateway HTTP
- ✅ IAM Roles e Policies

---

## 🚀 Como Implementar

### Passo 1: Configurar Ambiente Local

```bash
# Instalar Terraform
brew install terraform  # macOS
# ou
choco install terraform  # Windows

# Instalar AWS CLI
pip install awscli

# Configurar credenciais AWS
aws configure
```

### Passo 2: Criar Pacotes Lambda

```bash
# Controller
cd c:/Documentos/langchain
zip lambda_controller.zip lambda_controller.py

# Worker (incluir dependências)
pip install -t package/ langchain langchain-anthropic boto3
cd package && zip -r ../lambda_worker.zip . && cd ..
zip lambda_worker.zip lambda_worker.py aws_pipeline_clientes.py

# Status
zip lambda_status.zip lambda_status.py
```

### Passo 3: Provisionar Infraestrutura

```bash
# Inicializar Terraform
terraform init

# Planejar mudanças
terraform plan

# Aplicar (criar recursos)
terraform apply
# Digite 'yes' para confirmar

# Salvar outputs
terraform output > outputs.txt
```

### Passo 4: Testar API

```bash
# Obter URL da API
export API_URL=$(terraform output -raw api_endpoint)

# Fazer requisição assíncrona
curl -X POST "$API_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": "C12345",
    "dados_cliente": {
      "idade": 35,
      "renda_mensal": 5000,
      "saldo_medio": 8000,
      "transacoes_mes": 15,
      "score_credito": 680,
      "num_produtos": 3
    },
    "pergunta": "Quais produtos você recomenda?",
    "modo": "segmento"
  }'

# Resposta imediata:
# {
#   "request_id": "req_abc123",
#   "status": "PENDING",
#   "message": "Consulte GET /status/req_abc123"
# }

# Consultar status (polling)
curl "$API_URL/status/req_abc123"

# Resposta após processamento:
# {
#   "request_id": "req_abc123",
#   "status": "COMPLETED",
#   "result": {
#     "cliente_id": "C12345",
#     "cluster_id": 2,
#     "segmento": "Massa Estável",
#     "resposta": "..."
#   }
# }
```

---

## 📋 Checklist de Migração

### Infraestrutura
- [ ] Provisionar DynamoDB (requests table)
- [ ] Criar SQS Queue + DLQ
- [ ] Criar SNS Topic
- [ ] Deploy das 3 Lambdas
- [ ] Configurar API Gateway
- [ ] Configurar IAM Roles/Policies

### Código
- [ ] Testar `lambda_controller.py` isoladamente
- [ ] Testar `lambda_worker.py` com SQS local (LocalStack)
- [ ] Testar `lambda_status.py` com DynamoDB local
- [ ] Validar integração completa

### Monitoramento
- [ ] Configurar CloudWatch Dashboards
- [ ] Criar alarmes para DLQ (mensagens falhadas)
- [ ] Configurar alertas SNS para equipe
- [ ] Adicionar métricas customizadas

### Cliente
- [ ] Implementar polling com exponential backoff
- [ ] Adicionar timeout no cliente (ex: 5 minutos)
- [ ] Implementar UI de loading/progress
- [ ] Adicionar tratamento de erros

---

## 💰 Estimativa de Custos (AWS us-east-1)

**Premissas:** 10.000 requisições/mês, tempo médio 2 minutos/requisição

| Recurso | Custo/mês |
|---------|-----------|
| API Gateway | $0.35 (10k requests × $0.000035) |
| Lambda Controller | $0.01 (256MB × 1s × 10k) |
| Lambda Worker | $12.00 (3GB × 120s × 10k) |
| DynamoDB | $2.50 (on-demand, 40k ops) |
| SQS | $0.00 (dentro free tier) |
| SNS | $0.50 (10k notificações) |
| CloudWatch Logs | $5.00 |
| **TOTAL** | **~$20/mês** |

*Comparado com instância EC2 t3.medium 24/7: ~$30/mês*

---

## 🔄 Fluxo de Dados Completo

### 1. Cliente envia requisição
```http
POST /query
{
  "cliente_id": "C001",
  "dados_cliente": {...},
  "pergunta": "...",
  "modo": "segmento"
}
```

### 2. Lambda Controller responde
```json
{
  "request_id": "req_abc123",
  "status": "PENDING",
  "message": "Consulte GET /status/req_abc123"
}
```

### 3. Cliente faz polling
```http
GET /status/req_abc123

# Resposta inicial:
{"status": "PROCESSING", "started_at": "2026-03-09T10:30:00"}

# Após 2 minutos:
{"status": "COMPLETED", "result": {...}, "completed_at": "..."}
```

### 4. (Opcional) SNS notifica webhook
```json
{
  "request_id": "req_abc123",
  "status": "COMPLETED",
  "result": {...}
}
```

---

## 🛠️ Troubleshooting

### Q: Lambda Worker está falhando
**A:** Verificar:
1. CloudWatch Logs: `/aws/lambda/{function-name}`
2. SQS DLQ: mensagens que falharam 3x
3. IAM Permissions: Worker precisa acessar S3, OpenSearch, Secrets Manager

### Q: Cliente está recebendo timeout
**A:** API Gateway tem limite de 30s, mas Controller deve responder em < 1s. Verificar logs.

### Q: Processamento está muito lento
**A:** Aumentar memória da Lambda Worker (mais memória = mais CPU). Testar com 4-6GB.

### Q: Custos estão altos
**A:** 
1. Reduzir logs do CloudWatch (retention de 7 dias)
2. Usar Reserved Capacity no DynamoDB se houver tráfego constante
3. Otimizar tamanho de mensagens SQS

---

## 📚 Referências

- [AWS Lambda Async Patterns](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [SQS Long Polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)
- [API Gateway Timeout Limits](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)

---

## ✅ Conclusão

A nova arquitetura assíncrona resolve completamente o problema de timeout de 30s, melhora a experiência do usuário e aumenta a escalabilidade do sistema. 

**Próximos passos:**
1. Provisionar infraestrutura com Terraform
2. Deploy das Lambdas
3. Testar integração completa
4. Migrar clientes para novo endpoint
