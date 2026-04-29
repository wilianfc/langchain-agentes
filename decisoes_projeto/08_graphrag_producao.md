# Arquitetura GraphRAG em Produção — AWS

## Data: 2026-04-29

### Decisão: Worker Lambda fora da VPC + Neptune Proxy dentro da VPC

**Contexto:**
O worker Lambda foi inicialmente colocado na VPC para acessar Neptune (VPC-only). Isso quebrou o acesso ao OpenSearch (endpoint público), pois Lambda em VPC não tem rota internet sem NAT Gateway, e o VPC endpoint `com.amazonaws.sa-east-1.es` não existe em sa-east-1.

**Escolha:**
- Worker Lambda **fora** da VPC → acessa OpenSearch, Bedrock, S3, DynamoDB diretamente
- Módulo `neptune_proxy`: Lambda **dentro** da VPC → acessa Neptune com SigV4, retorna resultados
- Worker invoca Neptune Proxy via `boto3.invoke(FunctionName=NEPTUNE_PROXY_FUNCTION)`

**Alternativas descartadas:**
- NAT Gateway: ~$32/mês, custo alto para dev
- Lambda VPC endpoint + "OS writer" Lambda: complexidade adicional
- OpenSearch em VPC: requer recriar o domínio (destrutivo)

**Status:** ✅ Implementado e validado em produção

---

### Decisão: SigV4 Neptune via botocore.auth.SigV4Auth

**Contexto:**
`requests_aws4auth` causava 403 quando `Host` header sem `:8182`. Neptune verifica SigV4 incluindo porta não-padrão no Host canônico.

**Escolha:**
```python
aws_req = botocore.awsrequest.AWSRequest(
    method="POST", url=url, data=body,
    headers={"Content-Type": "application/json", "Host": f"{NEPTUNE_ENDPOINT}:8182"},
)
botocore.auth.SigV4Auth(creds, "neptune-db", AWS_REGION).add_auth(aws_req)
resp = requests.post(url, data=body, headers=dict(aws_req.headers), timeout=15)
```

**Quirks Neptune OpenCypher:**
- Serviço SigV4: `neptune-db` (não `neptune`)
- `parameters` no body JSON deve ser string JSON: `json.dumps(params)` (não dict)
- Host obrigatório com porta: `hostname:8182`

**Status:** ✅ Corrigido e funcionando

---

### Decisão: Bedrock em sa-east-1 com global inference profile

**Contexto:**
`us.anthropic.claude-sonnet-4-5-20250514-v1:0` estava desativado. `global.anthropic.claude-sonnet-4-6` requer formulário de aprovação Anthropic.

**Escolha:** `global.anthropic.claude-sonnet-4-5-20250929-v1:0` em sa-east-1
- Disponível sem aprovação especial
- Performance adequada para o caso de uso

**Status:** ✅ Funcionando

---

### Decisão: Replicação Neptune → OpenSearch (Etapa 5) adiada

**Contexto:**
Lambda `neptune-replicator` dentro da VPC não consegue acessar OpenSearch (sem VPC endpoint `es` em sa-east-1, sem NAT).

**Decisão:**
Manter o código deployado (EventBridge ativo) mas aceitar que o índice `neptune-graph-sync` ficará vazio. Worker usa BM25 direto + Neptune proxy live (sem a camada de grafo replicado).

**Quando resolver:**
Quando houver justificativa de custo para NAT ($32/mês) ou Lambda VPC endpoint ($7/mês/AZ).

**Status:** ⚠️ Bloqueado — replicação inativa, demais funcionalidades OK

---

### Grafo Neptune — esquema e conteúdo (2026-04-29)

```
4 Segmentos (Premium Conservador, Jovem Digital, Alto Risco, Massa Estável)
16 Produtos (4 por segmento)
4 Personas (Carlos, Júlia, Roberto, Ana)
200 Clientes (50 por cluster, gerados por perturbação de centróides)
Arestas: RECOMENDA, TEM_PERSONA, PERTENCE_A, SIMILAR_A (k-NN top-3)
```

Seed via Lambda `langchain-neptune-seeder-tmp` + `model_data.json` (gerado de `modelo_clustering_slim.pkl`).
