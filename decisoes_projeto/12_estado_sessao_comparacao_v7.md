# 12 — Estado da Sessão: Comparação diagram_v7 vs. Implementação Atual

**Data:** 2026-05-02
**Tipo:** Registro de continuidade — análise comparativa concluída
**Versão do diagrama:** `C:\Documentos\diagram_v7.drawio` (3 páginas, 423 linhas)

---

## Resumo da análise concluída

O arquivo `diagram_v7.drawio` contém a **visão-alvo do projeto** em 3 páginas:
- **Pág.1 (P1Runtime):** Agentes, KBs, Judges, Few-Shot DB, Meta-Judge, Aggregator, Observabilidade
- **Pág.2 (P2ML):** Pipeline ML de clustering com 6 etapas: Coleta → Pré-proc → Embedding → Clustering → Análise LLM → Saídas
- **Pág.3 (P3HumanEval):** Framework de avaliação humana (questionários Q1/Q2/Q3, Cohen's Kappa, painel web + FullStory)

---

## O que o projeto já implementa (relação com diagrama)

| Componente | Diagrama | Projeto |
|---|---|---|
| Vector Store por segmento | Vector Store PF/PJ/FP/PJA | OpenSearch `clientes-segmento-{0..3}` |
| Agentes LangChain | LangChain AgentExecutor | LangGraph `create_react_agent` + `MemorySaver` |
| Async pipeline | Implícito no runtime | SQS → Lambda worker → DynamoDB → status |
| BedrockEmbeddings | Titan Text v2 | `amazon.titan-embed-text-v1` |
| Claude Sonnet | Bedrock LLM | `claude-sonnet-4-5` via Bedrock |

## O que o projeto tem ALÉM do diagrama (evoluções não previstas)

- **Digital Twin** — índice `clientes-digital-twins`, modo `twin` — não estava no diagrama
- **Neptune GraphRAG** — grafo k-NN multi-hop — diagrama usa apenas Vector Stores planas
- **Índice de confiabilidade** — score calculado (BM25=0.40, Neptune live=0.30, sync=0.15) — não previsto
- **CloudFront + frontend console** — camada de apresentação — diagrama não inclui

---

## Lacunas confirmadas: diagrama especifica, projeto NÃO implementou

### Alta prioridade (impactam qualidade de resposta)

| Componente | Diagrama | Onde documentado no livro |
|---|---|---|
| LLM Judge por segmento (PF/PJ/FP/PJA) | Few-Shot + LangChain LLMChain por segmento | Cap. 13 (LLM-as-Judge) |
| DeepEval metrics | AnswerRelevancy, Faithfulness, GEval, BiasMetric, ContextualPrecision | Cap. 12 (Avaliação) |
| Few-Shot DB validado por humanos | Por segmento, anotado por especialistas | Cap. 14 (Golden Dataset) |
| Meta-Judge + feedback loop | Recalibra judges automaticamente | Cap. 13 |

### Média prioridade (pipeline ML)

| Componente | Diagrama | Situação |
|---|---|---|
| 4 segmentos regulatórios PF/PJ/FP/PJA | Segmentos bancários reais com sub-clusters | Projeto usa 4 clusters K-Means genéricos (nomes arbitrários) |
| KBs domain-specific | KB:Produtos, KB:Regulatório, KB:Perfil por segmento | Não existem — dados sintéticos sem KBs reais |
| HDBSCAN + UMAP | Clustering hierárquico + redução dimensional 2D/3D | Projeto usa K-Means direto |
| Evaluation Orchestrator | LangChain RouterChain por segmento | Lambda controller faz roteamento simples |
| Results Aggregator | Consolida scores PF+PJ+FP+PJA | Não existe |

### Baixa prioridade (observabilidade)

| Componente | Diagrama | Situação |
|---|---|---|
| LangSmith Traces → Datadog | APM com traces de agentes/judges | Não configurado |
| Datadog APM | Métricas, alertas, logs centralizados | Não implementado |
| FullStory | Session recording do painel de avaliação | Não implementado |
| DeepEval Synthesizer | Geração do Golden Dataset candidato | Não implementado |
| Avaliação humana (Pág.3) | Questionários Q1/Q2/Q3, Cohen's Kappa, IAA | Não implementado |
| Re-clustering periódico | A partir de CRM real | Não implementado |

---

## Sub-clusters previstos no diagrama (Pág.2)

| Segmento | Sub-clusters |
|---|---|
| PF — Pessoa Física | PF-Varejo, PF-Investidor, PF-Crédito |
| PJ — Pessoa Jurídica | PJ-MEI/ME, PJ-Médias, PJ-Corporate |
| FP — Funcionário Público | FP-Federal, FP-Estadual, FP-Aposentado |
| PJA — PJ Agronegócio | PJA-Custeio, PJA-Investimento, PJA-Hedge |

---

## Roadmap sugerido para próximo ciclo

1. **Sprint 1 — Judge básico:** implementar `LLMChain` como LLM Judge para PF com GEval (AnswerRelevancy + Faithfulness) via DeepEval
2. **Sprint 2 — Golden Dataset:** usar `DeepEval Synthesizer` para gerar dataset candidato + criar estrutura de Few-Shot DB
3. **Sprint 3 — Segmentação real:** migrar clusters genéricos → segmentos PF/PJ/FP/PJA no `aws_pipeline_clientes.py` + criar KBs de domínio
4. **Sprint 4 — Meta-Judge:** implementar Meta-Judge com feedback loop para recalibrar judges por segmento
5. **Sprint 5 — Observabilidade:** integrar LangSmith + Datadog APM

---

## Estado do livro LaTeX após esta sessão

- **PDF:** `livro/main.pdf` — 763.333 bytes, 18 capítulos, zero erros fatais
- **Novo capítulo:** `10_pipeline_integrado_producao.tex` — cobre as 4 lacunas de documentação identificadas
- **Capítulos renumerados:** 10→11 a 17→18 para acomodar o novo cap. 10
- **Sequência final:** 01–10 (pipeline integrado, novo) → 11 (confiabilidade) → 12 (avaliação) → 13 (LLM-as-judge) → 14 (golden) → 15 (roadmap) → 16 (CICD) → 17 (qualidade) → 18 (frontend)

---

## Infraestrutura AWS

- **Status:** `terraform destroy` executado na sessão anterior — infraestrutura derrubada intencionalmente
- **Região:** `sa-east-1`
- **Módulos Terraform disponíveis:** dynamodb, sqs, sns, s3, iam, opensearch, neptune, neptune_replication, api_gateway, lambda, lambda_layer, secrets, vpc_endpoints
- **Para recriar:** `cd infraestrutura && terraform init && terraform apply`
