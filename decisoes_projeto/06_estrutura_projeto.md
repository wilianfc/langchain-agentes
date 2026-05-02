# Decisões de Estrutura e Organização - Projeto LangChain

## Data: 2026-04-10

### Decisão: Estrutura Modular do Projeto  
**Escolha:** Notebook educacional com progressão incremental

**Organização implementada:**

#### Estrutura do Notebook
1. **Parte 1:** Agente básico com LangGraph
2. **Parte 2:** RAG + memória de médio prazo
3. **Parte 3:** Skills customizadas para o agente  
4. **Parte 4:** Tools para consulta externa/internet
5. **Parte 5:** Confiabilidade e avaliação de resposta
6. **Parte 6:** MCP para PostgreSQL
7. **Parte 7:** Pipeline ML + RAG + agente para perfis (K-Means, Digital Twins, Personas)
8. **Parte 8:** Arquitetura assíncrona de produção AWS (API Gateway + SQS + Lambda Worker)
9. **Parte 9:** GraphRAG com Amazon Neptune (grafo de conhecimento OpenCypher + replicação Neptune→OpenSearch)
10. **MemPalace:** Integração de memória de longo prazo para decisões do projeto

#### Scripts de Ingestão e Seed
- `indexar_documento.py` - Ingestão no pipeline GraphRAG (chunk → entidades Neptune → OpenSearch BM25)
- `indexar_twins_graph.py` - Indexa clientes GRAPH-C* no OpenSearch (digital twins do seed Neptune)
- `popular_neptune.py` - Popula grafo Neptune com segmentos, produtos, personas e clientes
- `seed_neptune_lambda.py` - Versão Lambda do seed Neptune (executa dentro da VPC)

#### Infra e Lambda
- `infraestrutura/` - Terraform completo: API GW, Lambda (controller/worker/status), SQS, DynamoDB, OpenSearch, Neptune, VPC Endpoints
- `lambda_controller.py` / `lambda_worker.py` / `lambda_status.py` - Handlers das Lambdas

#### Testes
- `tests/test_confiabilidade.py` - Testes unitários para índice de confiabilidade do pipeline RAG (pytest, sem credenciais AWS)

#### Notebooks e Demo
- `langchain.ipynb` - Notebook principal didático (Partes 1–9)
- `demo_api.ipynb` - Notebook de demo da API assíncrona

#### Arquivos de Configuração
- `.vscode/tasks.json` - Tasks para MemPalace
- `.vscode/keybindings.json` - Atalhos customizados
- `project-memory-simple.ps1` - Script CLI
- `claude-mcp-config.json` - Configuração Claude MCP

#### Documentação
- `README.md` - Documentação principal (Partes 1–9)
- `MIGRATION_ASYNC.md` - Guia de migração para arquitetura assíncrona
- `MEMPALACE_INTEGRATION.md` - Guia de integração MemPalace
- `SETUP_COMPLETO.md` - Instruções de setup MemPalace
- `decisoes_projeto/` - Decisões arquivadas (01–07)

**Motivação:**
Estrutura didática que serve tanto para aprendizado quanto uso prático. Permite evolução incremental dos conceitos.

**Padrão de desenvolvimento:**
- Cada parte é independente mas se integra com as anteriores
- Exemplos práticos em cada seção
- Documentação inline extensa

**Status:** ✅ Estrutura completa e documentada