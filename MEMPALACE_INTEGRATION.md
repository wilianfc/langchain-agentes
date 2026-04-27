# 🧠 MemPalace - Integração com VS Code e Claude

Este projeto agora possui **3 formas** de integrar o MemPalace para manter histórico de decisões:

## 🚀 Setup Inicial Rápido

### 1. Instalar MemPalace:
```powershell
pip install mempalace
```

### 2. Inicializar:
```powershell
# Via script
.\project-memory.ps1 init

# Via VS Code (Ctrl+Alt+I)
# ou Command Palette: "Tasks: Run Task" > "MemPalace: Inicializar Palace"
```

## 📋 Métodos de Uso

### 🖥️ **Método 1: VS Code Tasks + Atalhos**

| Atalho | Ação | Descrição |
|--------|------|-----------|
| `Ctrl+Alt+D` | Salvar Decisão | Salva decisão técnica importante |
| `Ctrl+Alt+S` | Buscar Decisões | Busca em decisões anteriores |
| `Ctrl+Alt+C` | Carregar Contexto | Carrega ~170 tokens essenciais |
| `Ctrl+Alt+P` | Salvar Problema | Salva problema e solução encontrada |
| `Ctrl+Alt+I` | Inicializar | Testa/configura MemPalace |

**Alternativa:** Command Palette (`Ctrl+Shift+P`) > "Tasks: Run Task" > escolher tarefa

### 💻 **Método 2: Script PowerShell**

```powershell
# Salvar decisão técnica
.\project-memory.ps1 save

# Buscar decisões anteriores  
.\project-memory.ps1 search

# Carregar contexto do projeto
.\project-memory.ps1 context

# Salvar problema resolvido
.\project-memory.ps1 problem

# Ver ajuda completa
.\project-memory.ps1 help
```

### 🤖 **Método 3: Claude MCP (Automático)**

1. **Configure:** Copie conteúdo de `claude-mcp-config.json` para configuração do Claude
2. **Use direto no Claude:**
   - "Salve esta decisão: Escolhemos PostgreSQL para dados estruturados"
   - "Busque decisões sobre 'autenticação'"
   - "Carregue o contexto essencial do projeto"

## 📂 Estrutura de Memórias

```
%USERPROFILE%/.mempalace/vscode_decisions/
└── wings/
    └── langchain_project/           # Nome do projeto atual
        └── rooms/
            ├── decisoes_tecnicas/   # Decisões de arquitetura 
            ├── problemas_resolvidos/# Bugs e soluções
            ├── tech/               # Decisões técnicas gerais
            ├── user/               # Decisões focadas no usuário
            ├── business/           # Decisões de negócio
            └── config/             # Configurações importantes
```

## 🔄 Fluxo de Trabalho Recomendado

### **🌅 Início do dia/projeto:**
- `Ctrl+Alt+C` - Carregue contexto essencial
- Relembre decisões principais tomadas

### **💡 Durante desenvolvimento:**
- `Ctrl+Alt+D` - Salve decisões importantes conforme toma
- `Ctrl+Alt+P` - Documente problemas e soluções

### **🔍 Antes de mudanças grandes:**
- `Ctrl+Alt+S` - Busque decisões relacionadas
- Evite retrabalho e inconsistências

### **📝 Code reviews/handoffs:**
- Use contexto carregado para explicar escolhas
- Decisões ficam documentadas e rastreáveis

## 🎯 Exemplos de Uso

### **Salvar Decisões:**
```
Decisão: "Escolhemos LangGraph em vez de LangChain Agent porque precisamos de ciclos ReAct e state checkpointing para conversas longas"
Categoria: tech

Decisão: "API rate limit definido como 100req/min para evitar abuse mas permitir uso normal"  
Categoria: business
```

### **Buscar Decisões:**
```
Busca: "database"
Resultado: Encontradas 3 decisões sobre escolha PostgreSQL, schema design, etc.

Busca: "autenticacao"  
Resultado: Decisão sobre JWT vs sessions, configuração OAuth, etc.
```

### **Problema Resolvido:**
```
Problema: "LangGraph estava dando erro 'thread_id não encontrado'"
Solução: "Precisa inicializar MemorySaver antes de usar thread_id. Adicionado checkpoint no create_react_agent"
```

## 🔧 Troubleshooting

### **MemPalace não funciona:**
```powershell
# Verificar instalação
python -c "import mempalace; print('OK')"

# Reinstalar se necessário
pip uninstall mempalace
pip install mempalace
```

### **Tasks do VS Code não aparecem:**
- Recarregue VS Code (`Ctrl+Shift+P` > "Developer: Reload Window")
- Verifique se está no workspace correto (pasta com `.vscode/`)

### **Claude MCP não funciona:**
- Verifique caminho do arquivo de config do Claude
- Reinicie Claude Desktop após editar config
- Teste com `python -m mempalace.mcp_server` no terminal

## 📊 Benefícios vs. Situação Anterior

| Aspecto | Antes | Agora |
|---------|-------|-------|
| **Decisões** | Perdidas entre sessões | **Persistem e são navegáveis** |
| **Context** | Reprocessar tudo sempre | **~170 tokens essenciais** |
| **Problemas** | Resolvidos e esquecidos | **Documentados para reuso** |
| **Handoffs** | Sem contexto | **Histórico completo** |
| **Consistência** | Decisões contraditórias | **Base única de verdade** |

---

🎯 **Resultado:** Agente e desenvolvedores que "lembram" decisões ao longo do tempo, evitando retrabalho e mantendo consistência no projeto.