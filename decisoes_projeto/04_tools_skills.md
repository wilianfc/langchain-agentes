# Decisões de Tools e Skills - Projeto LangChain  

## Data: 2026-04-10

### Decisão: Ferramentas Customizadas do Agente
**Escolha:** Conjunto específico de tools usando decorador @tool

**Tools implementadas:**

#### Core Tools
1. **calculadora** - Avaliação de expressões matemáticas
2. **consultar_clima** - API weather (demonstração)  
3. **converter_moeda** - Conversão de moedas (demonstração)
4. **buscar_conhecimento** - RAG sobre base técnica

#### MemPalace Tools
5. **memoria_longo_prazo** - Busca em decisões persistentes
6. **salvar_memoria_importante** - Persiste informações relevantes
7. **carregar_contexto_essencial** - Context loading (~170 tokens)

**Padrão de implementação:**
```python
@tool
def nome_ferramenta(param: str) -> str:
    """Docstring clara descrevendo uso e propósito."""
    # implementação
    return resultado
```

**Motivação:**
- Funcionalidades específicas e testáveis
- Documentação automática via docstrings
- Integração nativa com LangGraph ReAct

**Status:** ✅ 7 tools implementadas e testadas