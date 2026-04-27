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
7. **Parte 7:** Pipeline ML + RAG + agente para perfis
8. **MemPalace:** Integração de memória de longo prazo

#### Arquivos de Configuração
- `.vscode/tasks.json` - Tasks para MemPalace
- `.vscode/keybindings.json` - Atalhos customizados
- `project-memory-simple.ps1` - Script CLI
- `claude-mcp-config.json` - Configuração Claude MCP

#### Documentação
- `MEMPALACE_INTEGRATION.md` - Guia de integração
- `SETUP_COMPLETO.md` - Instruções de uso
- `decisoes_projeto/` - Decisões arquivadas

**Motivação:**
Estrutura didática que serve tanto para aprendizado quanto uso prático. Permite evolução incremental dos conceitos.

**Padrão de desenvolvimento:**
- Cada parte é independente mas se integra com as anteriores
- Exemplos práticos em cada seção
- Documentação inline extensa

**Status:** ✅ Estrutura completa e documentada