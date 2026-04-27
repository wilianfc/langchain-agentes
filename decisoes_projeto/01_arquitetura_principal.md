# Decisões de Arquitetura - Projeto LangChain

## Data: 2026-04-10

### Decisão: Framework Principal
**Escolha:** LangGraph + LangChain para construção de agentes AI

**Motivação:**
- LangGraph permite ciclos ReAct (Reasoning + Acting)
- Suporte nativo a state checkpointing
- Integração perfeita com LangChain para tools
- Streaming de tokens e execução assíncrona
- Memória persistente via checkpointers

**Alternativas consideradas:** 
- LangChain Agent puro (limitações nos ciclos)
- Custom implementation (muito trabalho)

**Status:** ✅ Implementado e funcionando