# Decisões de Modelo e API - Projeto LangChain

## Data: 2026-04-10

### Decisão: Modelo de Language Model  
**Escolha:** Claude Sonnet 4.6 (Anthropic)

**Motivação:**
- Excelente capacidade de reasoning
- Suporte nativo a tool calling
- Tokens de contexto extensos
- Menor propensão a alucinações  
- Boa performance custo-benefício

**Configuração:**
```python
model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
```

**Alternativas consideradas:**
- GPT-4 (custo mais alto)
- Claude Haiku (menos capaz para reasoning complexo)
- Modelos locais (performance inferior)

**Status:** ✅ Implementado e configurado