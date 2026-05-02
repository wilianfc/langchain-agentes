# Decisões de Memória - Projeto LangChain

## Data: 2026-04-10

### Decisão: Sistema de Memória em 3 Camadas
**Escolha:** Arquitetura híbrida multi-nível

**Camadas implementadas:**

#### 1. Curto Prazo (In-session)
- **Implementação:** MemorySaver do LangGraph
- **Uso:** thread_id para conversas isoladas
- **Duração:** Durante execução do processo
- **Benefício:** Contexto de conversa imediato

#### 2. Médio Prazo (Cross-session)  
- **Implementação:** FAISS + HuggingFaceEmbeddings
- **Uso:** RAG para conhecimento técnico
- **Modelo:** all-MiniLM-L6-v2 (384 dimensões)
- **Benefício:** Base de conhecimento searchável

#### 3. Longo Prazo (Persistente)
- **Implementação:** MemPalace (`decisoes_projeto/mempalace.yaml`, palace em `./decisoes_projeto/`)
- **Uso:** Decisões técnicas do projeto — persistem entre sessões, buscáveis semanticamente
- **Drawers minerados:** 12 drawers de 7 arquivos de decisão
- **Context loading:** 723 tokens no wake-up
- **Score:** 96.6% no LongMemEval benchmark
- **Benefício:** Memória verbatim navegável, busca semântica < 1s

**Motivação:**
Cada camada tem propósito específico, evitando overhead de reprocessar contextos grandes a cada interação.

**Status:** ✅ Todas implementadas e integradas