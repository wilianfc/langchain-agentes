# 14 — Plano de Escrita dos Capítulos Restantes

**Data:** 2026-05-02  
**Status:** ATIVO — guia de priorização para as próximas sessões de trabalho

---

## 1. Inventário de Estado dos Capítulos

| Cap | Título | Estado | Linhas | Código validado? |
|-----|--------|--------|--------|-----------------|
| 01 | Fundamentos de IA e LLMs | ✅ Redigido | 354 | Sem código próprio (conceitual) |
| 02 | Ambiente e Reprodutibilidade | ✅ Redigido | 270 | `langchain.ipynb` setup — **testável localmente** |
| 03 | Agentes com LangGraph e Memória | ✅ Redigido + pedagógico | 670 | `langchain.ipynb` (71 células) — **testar ReAct + MemorySaver** |
| 04 | Tools, Skills e MCP | ⚠️ Placeholder (53 linhas) | 53 | `mcp_mock_server.py` + `mcp_postgres_server.py` existem — **código disponível, capítulo em falta** |
| 05 | RAG Fundamentos | ⚠️ Placeholder (53 linhas) | 53 | `indexar_documento.py` + FAISS local — **código disponível, capítulo em falta** |
| 06 | RAG Corporativo | ✅ Redigido | 222 | `ingester.py` (236L) / `indexar_documento.py` — **validar endpoint `/documentos`** |
| 07 | Pipeline Assíncrono AWS | ✅ Redigido | 209 | `controller.py` + `worker.py` + `lambda_controller.py` + `lambda_worker.py` — **testável com SAM/moto** |
| 08 | Segmentação, Personas, Twins | ✅ Redigido | 243 | `gerar_clustering.py` + `aws_pipeline_clientes.py` modo synthetic — **testável localmente** |
| 09 | GraphRAG com Neptune | ✅ Redigido | 203 | `popular_neptune.py` + `indexar_twins_graph.py` + `seed_neptune_lambda.py` — **requer Neptune local ou mock** |
| 10 | Pipeline Integrado em Produção | ✅ Redigido | 301 | `worker.py` (883L) modo completo — **integração ainda não testada ponta a ponta** |
| 11 | Confiabilidade, Observabilidade | ⚠️ Placeholder parcial (63L) | 63 | `otel_config.py` + `test_confiabilidade.py` (não encontrado) — **código incompleto** |
| 12 | Avaliação, Métricas de Mercado | ⚠️ Placeholder (53 linhas) | 53 | **Não existe código** |
| 13 | LLM as Judge | ⚠️ Placeholder (53 linhas) | 53 | **Não existe código** |
| 14 | Golden Dataset e Regressão | ⚠️ Placeholder (53 linhas) | 53 | **Não existe código** |
| 15 | Roadmap de Produção | ⚠️ Placeholder (53 linhas) | 53 | **Sem código** (documento estratégico) |
| 16 | CI/CD Multiambiente Bancário | ✅ Redigido | 321 | `terraform_async_infra.tf` + `infraestrutura/` — **testável com `terraform plan`** |
| 17 | Qualidade e Segurança Esteiras | ✅ Redigido | 359 | Análise estática, sem código próprio |
| 18 | Frontend, CloudFront, Console | ✅ Redigido | 303 | Sem código próprio (arquitetural) |

---

## 2. Análise: Código Existente vs. Capítulos

### Código implementado SEM capítulo correspondente

| Arquivo | Funcionalidade | Capítulo que precisa | Estado de validação |
|---------|----------------|---------------------|---------------------|
| `mcp_mock_server.py` (129L) | Servidor MCP mock para testes | **Cap. 04** | ⚠️ Funcional, não testado documentado |
| `mcp_postgres_server.py` | Servidor MCP com PostgreSQL real | **Cap. 04** | ⚠️ Requer PostgreSQL local |
| `indexar_documento.py` | Ingestão FAISS local | **Cap. 05** | ⚠️ Testável sem AWS |
| `indexar_twins_graph.py` | Index de twins para grafo | **Cap. 09** | ⚠️ Requer Neptune |
| `popular_neptune.py` | Popula grafo Neptune | **Cap. 09** | ⚠️ Requer Neptune |
| `otel_config.py` (68L) | OTel + Langfuse | **Cap. 11** | ⚠️ Requer chaves Langfuse |
| `aws_pipeline_clientes.py` (1582L) | Pipeline completo modo synthetic | Caps. 07, 08, 10 | ✅ Modo `synthetic=True` rodável localmente |

### Capítulos SEM código de suporte

| Capítulo | O que precisa ser criado antes de escrever |
|----------|--------------------------------------------|
| **Cap. 12** — Métricas de Mercado | Script de cálculo: BLEU, ROUGE, BERTScore, G-Eval — **criar `avaliar_metricas.py`** |
| **Cap. 13** — LLM as Judge | Script de avaliação com Claude como juiz — **criar `llm_judge.py`** |
| **Cap. 14** — Golden Dataset | Script de criação e execução de regressão — **criar `golden_dataset.py`** |
| **Cap. 15** — Roadmap | Apenas documento estratégico, sem código |

---

## 3. Validações Necessárias Antes de Escrever

### ALTA prioridade (bloqueiam cap. 04 e 05 — posição central na narrativa)

| # | Validação | Arquivo | Comando de teste |
|---|-----------|---------|-----------------|
| V1 | MCP mock server funciona e responde às ferramentas | `mcp_mock_server.py` | `python mcp_mock_server.py` + `curl` |
| V2 | Indexação FAISS local com `indexar_documento.py` | `indexar_documento.py` | `python indexar_documento.py --help` |
| V3 | Agente usa tool MCP no LangGraph (cap. 04) | `langchain.ipynb` células MCP | executar no notebook |

### MÉDIA prioridade (bloqueiam caps. 11–14 — loop externo)

| # | Validação | Arquivo | O que criar |
|---|-----------|---------|-------------|
| V4 | `otel_config.py` funciona sem credenciais Langfuse (modo silencioso) | `otel_config.py` | testar import + `enable_otel()` |
| V5 | Cálculo de métricas BLEU/ROUGE/BERTScore funciona offline | — | criar `avaliar_metricas.py` |
| V6 | LLM Judge retorna pontuação estruturada (0–1 com razão) | — | criar `llm_judge.py` |
| V7 | Golden dataset: carga + execução + comparação retorna diff legível | — | criar `golden_dataset.py` |

### BAIXA prioridade (infraestrutura, não bloqueia escrita conceitual)

| # | Validação | Arquivo | Observação |
|---|-----------|---------|------------|
| V8 | `popular_neptune.py` funciona com Neptune local (Docker) | `popular_neptune.py` | cap. 09 já redigido |
| V9 | Pipeline completo ponta a ponta com mock AWS | `aws_pipeline_clientes.py` | cap. 10 já redigido |

---

## 4. Plano de Escrita — Sequência de Sprints

### Sprint A — Completar loop interno (caps. 04 e 05)
**Pré-condição:** executar validações V1, V2, V3

| Passo | Ação |
|-------|------|
| A1 | Validar `mcp_mock_server.py` + `mcp_postgres_server.py` localmente |
| A2 | Redigir **cap. 04** (Tools, Skills, MCP): conceitos + código do servidor mock + integração com LangGraph |
| A3 | Validar `indexar_documento.py` com FAISS |
| A4 | Redigir **cap. 05** (RAG Fundamentos): chunking, embeddings, FAISS, busca semântica |

### Sprint B — Fechar gap do loop externo (caps. 11–14)
**Pré-condição:** executar validações V4, V5, V6, V7

| Passo | Ação |
|-------|------|
| B1 | Criar e testar `avaliar_metricas.py` (BLEU, ROUGE, BERTScore, G-Eval) |
| B2 | Criar e testar `llm_judge.py` (Claude como juiz por segmento) |
| B3 | Criar e testar `golden_dataset.py` (carga + diff + regressão) |
| B4 | Expandir **cap. 11** com `otel_config.py` + índice de confiabilidade real |
| B5 | Redigir **cap. 12** (Métricas de Mercado) usando `avaliar_metricas.py` |
| B6 | Redigir **cap. 13** (LLM as Judge) usando `llm_judge.py` |
| B7 | Redigir **cap. 14** (Golden Dataset) usando `golden_dataset.py` |

### Sprint C — Documento estratégico e revisão final
| Passo | Ação |
|-------|------|
| C1 | Redigir **cap. 15** (Roadmap) — análise de lacunas + diagrama v7 → v8 |
| C2 | Adicionar blocos de posicionamento narrativo nos caps. 02, 04–09, 12–18 |
| C3 | Revisar transições entre capítulos (gancho para o próximo) |
| C4 | Compilar PDF final e validar todas as referências cruzadas |

---

## 5. Critérios para "Código Pronto para Virar Livro"

Um script pode se tornar insumo de capítulo quando:

1. ✅ Executa sem erros com `python arquivo.py --help` ou equivalente
2. ✅ Tem ao menos um caso de teste documentado (input → output esperado)
3. ✅ Modo offline/mock disponível (não requer AWS em produção)
4. ✅ Saída legível e reproduzível para o leitor (sem credenciais hardcoded)
5. ✅ Encaixa no fluxo narrativo do capítulo (inner loop ou outer loop)

---

## 6. Próxima Ação Imediata

**Iniciar Sprint A, passo A1:** validar `mcp_mock_server.py` localmente.

```bash
cd C:\Documentos\langchain
python mcp_mock_server.py
```

Verificar se o servidor sobe, responde ao protocolo MCP e pode ser chamado
como ferramenta pelo agente LangGraph do cap. 03.
