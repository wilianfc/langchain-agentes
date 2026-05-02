# Decisões de Arquitetura de Produção AWS — Partes 8 e 9

## Data: 2026-05-01

---

### Parte 8 — Arquitetura Assíncrona

#### Decisão: Padrão POST→202 + Polling GET
**Escolha:** Lambda Controller (< 1s) → SQS → Lambda Worker (até 15min) + Lambda Status

**Motivação:**
- API Gateway tem timeout de 29s; pipeline RAG + LLM leva minutos
- Retorno imediato de `request_id` elimina bloqueio no cliente
- SQS garante reprocessamento automático via DLQ

**Componentes:**
| Componente | Papel |
|---|---|
| Lambda Controller | Gera `request_id`, salva PENDING no DynamoDB, enfileira no SQS |
| Lambda Worker | Processa pipeline completo: RAG + Bedrock + resposta |
| Lambda Status | Polling: lê DynamoDB e retorna status/resultado |
| SQS | Fila assíncrona (visibilidade 15min, DLQ automático) |
| DynamoDB | Estado da requisição (TTL 7 dias) |
| SNS | Notificação opcional de conclusão |

**Modos suportados no Worker:** `segmento` / `persona` / `twin`

**Status:** ✅ Implementado e deployado via Terraform

---

### Parte 9 — GraphRAG com Amazon Neptune

#### Decisão: Retrieval em 3 camadas com grafo de conhecimento
**Escolha:** BM25 (OpenSearch) + índice replicado (`neptune-graph-sync`) + Neptune live (OpenCypher)

**Motivação:**
- BM25 isolado não resolve raciocínio multi-hop ("produtos para clientes similares a X com inadimplência baixa")
- Neptune live direto seria bloqueado por conectividade VPC; índice replicado serve o caminho rápido
- Três camadas permitem degradação gradual (camada 1 sempre disponível)

**Componentes:**
| Componente | Papel |
|---|---|
| Amazon Neptune | Grafo de conhecimento (engine 1.3.1.0, `db.t3.medium`, IAM auth) |
| Lambda Proxy | Intermediário Worker → Neptune (resolve problema VPC-only do Neptune) |
| Lambda Replicador | Lê Neptune Streams a cada 5min → sincroniza índice `neptune-graph-sync` no OpenSearch |
| VPC Endpoints | S3 Gateway (gratuito) + Bedrock Runtime Interface (sem NAT Gateway) |

**Esquema do grafo:**
```
(:Segmento)-[:RECOMENDA]->(:Produto)
(:Segmento)-[:TEM_PERSONA]->(:Persona)
(:Cliente)-[:PERTENCE_A]->(:Segmento)
(:Cliente)-[:SIMILAR_A]->(:Cliente)   // k-NN top-3 intra-cluster
```

**Scripts de seed e ingestão:**
- `popular_neptune.py` — cria nós/arestas do grafo a partir do modelo de clustering
- `seed_neptune_lambda.py` — versão Lambda (executa dentro da VPC)
- `indexar_documento.py` — ingere documento: chunk → entidades Neptune → OpenSearch BM25
- `indexar_twins_graph.py` — indexa clientes GRAPH-C* no OpenSearch (digital twins faltantes)

**Decisão de conectividade:**
```
Worker Lambda (fora da VPC)
  ├─ OpenSearch: direto (endpoint público, SigV4)
  ├─ Bedrock:    via VPC Endpoint (Bedrock Runtime Interface)
  └─ Neptune:    via invoke() → Lambda Proxy (na VPC)
```

**Testes:**
- `tests/test_confiabilidade.py` — pytest unitário para índice de confiabilidade do pipeline RAG
  (sem credenciais AWS; mock de Bedrock via `unittest.mock`)

**Status:** ✅ Infraestrutura deployada; grafo populado com clientes GRAPH-C*; replicação ativa (5min)

---

### Arquivos de decisão anteriores referenciados
- `01_arquitetura_principal.md` — LangGraph + LangChain
- `02_modelo_linguagem.md` — Claude Sonnet 4.6 via Bedrock
- `03_sistema_memoria.md` — Memória em 3 camadas (MemorySaver, FAISS/OpenSearch, MemPalace)
- `04_tools_skills.md` — 7 tools customizadas
- `05_integracao_vscode.md` — Tasks e scripts VS Code
- `06_estrutura_projeto.md` — Estrutura modular Partes 1–9
- `07_implementacao_mempalace.md` — MemPalace operacional (723 tokens wake-up, 12 drawers)
