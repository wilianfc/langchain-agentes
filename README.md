# Agente com LangGraph: Do Básico ao MCP

Notebook didático cobrindo os principais conceitos de construção de agentes inteligentes com LangChain e LangGraph, do básico ao uso de MCP (Model Context Protocol) para integração com bancos de dados.

## Pré-requisitos

- Python 3.10+
- Chave de API da Anthropic (`ANTHROPIC_API_KEY`)
- Arquivo `.env` na raiz do projeto com `ANTHROPIC_API_KEY=sk-ant-...`

## Instalação

```bash
pip install langgraph langchain langchain-anthropic langchain-community \
    langchain-text-splitters langchain-mcp-adapters faiss-cpu sentence-transformers \
    psycopg2-binary mcp python-dotenv duckduckgo-search wikipedia httpx deepeval
```

---

## Estrutura do Notebook

### Parte 1 — Criando um Agente com LangGraph

O LangGraph estende o LangChain com um modelo de execução baseado em **grafos de estado**. Em vez de cadeias lineares, o agente pode iterar, ramificar e manter estado entre chamadas.

#### Componentes principais

| Componente | Papel |
|---|---|
| `ChatAnthropic` | Modelo de linguagem (LLM) |
| `@tool` | Decorador que transforma uma função Python em ferramenta utilizável pelo agente |
| `create_react_agent` | Cria o grafo ReAct: percebe → age → observa → repete |
| `MemorySaver` | Checkpointer que persiste o estado da conversa em memória |
| `thread_id` | Identificador de sessão; threads diferentes = conversas independentes |

#### Por que `langgraph.prebuilt.create_react_agent` e não `langchain.agents.create_agent`?

A mensagem de deprecação do LangGraph 1.0 sugere migrar para `langchain.agents.create_agent`, mas essa API tem assinatura incompatível: **não aceita `checkpointer`, `prompt` como string nem `state_modifier`**. A solução correta é manter `create_react_agent` e suprimir o aviso:

```python
import warnings
warnings.filterwarnings("ignore", message=".*create_react_agent.*")
from langgraph.prebuilt import create_react_agent
```

#### Exemplo mínimo

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

@tool
def calcular(expressao: str) -> str:
    """Avalia uma expressão matemática."""
    return str(eval(expressao))

agente = create_react_agent(model, [calcular], checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "sessao-1"}}
resultado = agente.invoke({"messages": [{"role": "user", "content": "Quanto é 2 + 2?"}]}, config=config)
```

---

### 1.3 — Chamadas Assíncronas e Streaming

Padrões assíncronos são essenciais para produção: evitam bloqueio de I/O e permitem streaming real de tokens.

| Padrão | Uso |
|---|---|
| `ainvoke` | Chamada assíncrona simples; retorna resposta completa |
| `astream(stream_mode="messages")` | Streaming token a token em tempo real |
| `astream_events(version="v2")` | Visibilidade de eventos internos (tool calls, chains) |
| `asyncio.gather` | Execução paralela de múltiplas perguntas |
| `@tool async def` | Ferramenta com I/O assíncrono (ex: HTTP, banco de dados) |

#### Ponto crítico: `stream_mode`

O parâmetro `stream_mode` do `astream` define o que é emitido:

- `"values"` (padrão) — emite o **estado completo** após cada nó terminar. Não há saída parcial durante a geração.
- `"messages"` — emite tuplas `(AIMessageChunk, metadata)` token a token. Necessário para streaming real.
- `"updates"` — emite apenas o **delta** do estado após cada nó.

```python
# Streaming token a token (correto)
async for chunk, metadata in agente.astream(
    {"messages": [{"role": "user", "content": pergunta}]},
    config=config,
    stream_mode="messages",   # <-- obrigatório para ver tokens
):
    if isinstance(chunk, AIMessageChunk) and chunk.content:
        print(chunk.content, end="", flush=True)
```

#### Ferramentas assíncronas

```python
@tool
async def buscar_conteudo_url(url: str) -> str:
    """Busca o conteúdo de uma URL de forma assíncrona."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        return resp.text[:2000]
```

---

### Parte 2 — RAG com Memória de Curto e Médio Prazo

#### Tipos de memória

| Tipo | Implementação | Duração |
|---|---|---|
| Curto prazo | `MemorySaver` com `thread_id` | Enquanto o processo estiver ativo |
| Médio prazo | FAISS + embeddings (vetor semântico) | Persistível em disco |
| Longo prazo | Banco de dados externo (PostgreSQL, etc.) | Permanente |

#### Pipeline RAG

```
Documentos
    │
    ▼
RecursiveCharacterTextSplitter  ← divide em chunks menores
    │
    ▼
HuggingFaceEmbeddings           ← gera vetores semânticos (all-MiniLM-L6-v2)
    │
    ▼
FAISS Vector Store              ← índice de busca por similaridade
    │
    ▼
retriever.as_retriever()        ← interface de recuperação
    │
    ▼
@tool buscar_conhecimento()     ← expõe o retriever como ferramenta do agente
```

#### Import correto do text splitter

```python
# Correto (pacote separado desde LangChain 0.2)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Incorreto (deprecated)
from langchain.text_splitter import RecursiveCharacterTextSplitter
```

---

### Parte 3 — Skills para o Agente

Skills são ferramentas com lógica de negócio encapsulada. A diferença para tools simples é o uso de **schemas Pydantic** para validação dos parâmetros.

```python
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

class FormatarRelatorioInput(BaseModel):
    titulo: str = Field(description="Título do relatório")
    dados: list = Field(description="Lista de dados a formatar")
    formato: str = Field(default="tabela", description="'tabela' ou 'lista'")

def formatar_relatorio(titulo: str, dados: list, formato: str = "tabela") -> str:
    ...

skill_relatorio = StructuredTool.from_function(
    func=formatar_relatorio,
    name="formatar_relatorio",
    description="Formata dados em relatório estruturado",
    args_schema=FormatarRelatorioInput,
)
```

---

### Parte 4 — Tools para Consulta na Internet

#### Ferramentas disponíveis

| Tool | Fonte | Uso recomendado |
|---|---|---|
| `DuckDuckGoSearchRun` | DuckDuckGo | Busca rápida, texto resumido |
| `DuckDuckGoSearchResults` | DuckDuckGo | Resultados com URL e snippet |
| `WikipediaQueryRun` | Wikipedia | Artigos estruturados e confiáveis |
| `httpx` customizado | Qualquer URL | Quando precisa de conteúdo específico |

```python
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

busca_web = DuckDuckGoSearchRun()
wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(lang="pt", top_k_results=2))
```

Para criar um agente de busca com memória de conversa:

```python
agente_web = create_react_agent(
    model,
    [busca_web, wikipedia, calculadora],
    checkpointer=MemorySaver(),
    prompt="Você é um assistente que pesquisa informações na internet..."
)
```

---

### Parte 5 — Confiabilidade da Resposta

LLMs podem alucinar. Esta seção apresenta três padrões para mitigar o problema.

#### Padrão 1 — Score de confiança com saída estruturada

Usa `with_structured_output(PydanticModel)` para forçar o modelo a emitir uma avaliação de confiança junto com a resposta:

```python
class RespostaComConfianca(BaseModel):
    resposta: str
    nivel_confianca: Literal["alto", "medio", "baixo"]
    justificativa: str
    requer_verificacao: bool

chain = model.with_structured_output(RespostaComConfianca)
```

#### Padrão 2 — Citação obrigatória de fontes

O agente é instruído via `SystemMessage` a sempre citar a ferramenta que originou cada afirmação. Respostas sem citação são rejeitadas pelo `SystemPrompt`.

#### Padrão 3 — Pipeline de auto-verificação com StateGraph

Grafo com 4 nós que implementa um loop de refinamento:

```
buscar_web → gerar_resposta → avaliar_resposta → refinar_ou_manter
                  ▲                   │
                  └───────────────────┘  (se score < threshold)
```

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(EstadoVerificacao)
graph.add_node("buscar_web", buscar_web)
graph.add_node("gerar_resposta", gerar_resposta)
graph.add_node("avaliar_resposta", avaliar_resposta)
graph.add_node("refinar_ou_manter", refinar_ou_manter)

graph.add_conditional_edges(
    "avaliar_resposta",
    decidir_refinamento,    # retorna "refinar" ou "finalizar"
    {"refinar": "gerar_resposta", "finalizar": END},
)
```

---

### 5.4 — Avaliação de Grounding: RAG vs Tools vs Modelo

Identificar **de onde vem cada afirmação** da resposta permite:
- Detectar alucinações (afirmações sem fonte externa)
- Medir o aproveitamento real do RAG e das tools
- Definir automaticamente se a resposta precisa de revisão humana

#### Como funciona

```
Resposta do agente
       │
       ▼
 Avaliador LLM ──► Classifica cada afirmação
       │                  ├── rag   (suportada pelo contexto recuperado)
       │                  ├── tool  (suportada por resultado de ferramenta)
       │                  └── modelo (apenas conhecimento interno do LLM)
       ▼
 RelatorioGrounding
   ├── pct_rag    → % da resposta com base em RAG
   ├── pct_tool   → % com base em tools externas
   ├── pct_modelo → % apenas do LLM (risco de alucinação)
   └── nivel_confianca → alta / media / baixa
```

#### Extração automática das evidências

A função `extrair_evidencias` percorre o `messages` retornado pelo agente e separa automaticamente:
- `ToolMessage` com nome contendo `"conhecimento"` ou `"retriev"` → contexto RAG
- Demais `ToolMessage` → resultados de ferramentas externas
- `AIMessage` sem `tool_calls` → resposta final

```python
def extrair_evidencias(mensagens):
    for msg in mensagens:
        if isinstance(msg, ToolMessage):
            if "conhecimento" in msg.name.lower():
                rag_chunks.append(msg.content)
            else:
                tool_results.append(f"[{msg.name}]: {msg.content}")
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            resposta = msg.content
```

---

### 5.5 — Avaliação com DeepEval

**DeepEval** é um framework de testes para LLMs (similar ao pytest) que avalia qualidade de respostas com métricas padronizadas.

#### Métricas principais

| Métrica | O que mede | Dados necessários |
|---|---|---|
| `AnswerRelevancy` | A resposta responde à pergunta? | `input`, `actual_output` |
| `Faithfulness` | Cada afirmação é suportada pelo contexto RAG? | + `retrieval_context` |
| `ContextualRecall` | O contexto cobre o que era esperado? | + `expected_output` |
| `ContextualPrecision` | O contexto recuperado é relevante? | + `expected_output` |
| `Hallucination` | Há afirmações não suportadas por nenhuma fonte? | + `context` |

#### Adaptador para usar Claude como avaliador

Por padrão o DeepEval usa GPT-4. Para substituir por Claude:

```python
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_anthropic import ChatAnthropic

class AnthropicEvaluator(DeepEvalBaseLLM):
    def __init__(self):
        self._model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

    def load_model(self):
        return self._model

    def generate(self, prompt: str, schema=None) -> str:
        return self._model.invoke(prompt).content

    async def a_generate(self, prompt: str, schema=None) -> str:
        resp = await self._model.ainvoke(prompt)
        return resp.content

    def get_model_name(self) -> str:
        return "claude-sonnet-4-6"
```

#### Fluxo de avaliação

```python
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

caso = LLMTestCase(
    input="Quais são as vantagens do LangGraph?",
    actual_output="LangGraph oferece memória persistente e streaming...",
    expected_output="Memória persistente, streaming e controle de fluxo.",
    retrieval_context=["LangGraph suporta checkpointers...", "Streaming nativo..."],
)

metricas = [
    FaithfulnessMetric(threshold=0.7, model=AnthropicEvaluator()),
    AnswerRelevancyMetric(threshold=0.7, model=AnthropicEvaluator()),
]

evaluate([caso], metricas)
```

---

### Parte 6 — MCP para Banco de Dados PostgreSQL

**MCP (Model Context Protocol)** é um protocolo aberto que padroniza a comunicação entre LLMs e sistemas externos (bancos de dados, APIs, sistemas de arquivos). Funciona como um "USB para IA": qualquer servidor MCP pode ser conectado a qualquer cliente MCP.

#### Arquitetura

```
Agente (LangGraph)
       │
       │  MultiServerMCPClient
       │         │
       ├── Server 1: PostgreSQL (stdio)
       ├── Server 2: Filesystem (npx)
       └── Server 3: Web Search (SSE)
```

#### Criando um servidor MCP

```python
import mcp
from mcp.server.stdio import stdio_server

server = mcp.Server("meu-servidor")

@server.tool()
async def listar_tabelas() -> str:
    """Lista as tabelas do banco de dados."""
    # consulta ao PostgreSQL
    ...

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())
```

#### Conectando o agente ao servidor MCP

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

# langchain-mcp-adapters >= 0.1.0: usar await client.get_tools(), não context manager
client = MultiServerMCPClient({
    "postgres": {
        "command": "python",
        "args": ["mcp_server.py"],
        "transport": "stdio",
        "env": dict(os.environ),
    }
})
mcp_tools = await client.get_tools()

agente = create_react_agent(model, mcp_tools, checkpointer=MemorySaver())
```

#### Workaround: `fileno()` no Jupyter

Ao rodar no Jupyter, o `sys.stderr` é um stream virtual sem file descriptor real. O MCP precisa de um fd válido ao criar o subprocesso stdio. Solução:

```python
import sys, io, os

try:
    sys.stderr.fileno()
except io.UnsupportedOperation:
    _devnull = open(os.devnull, "w")
    sys.stderr.fileno = _devnull.fileno
    sys.stdout.fileno = _devnull.fileno
```

---

## Problemas Conhecidos e Soluções

### `LangGraphDeprecatedSinceV10` ao usar `create_react_agent`

**Causa**: LangGraph 1.0 marcou `create_react_agent` de `langgraph.prebuilt` como deprecated e sugere migrar para `langchain.agents.create_agent`.

**Problema**: `langchain.agents.create_agent` tem API incompatível — não aceita `checkpointer`, `prompt` como string nem `state_modifier`. Usar como drop-in replacement causa `TypeError`.

**Solução correta**: manter `langgraph.prebuilt.create_react_agent` e suprimir o aviso:

```python
import warnings
warnings.filterwarnings("ignore", message=".*create_react_agent.*")
from langgraph.prebuilt import create_react_agent
```

---

### `astream` não produz output

**Causa**: `stream_mode` padrão é `"values"`, que emite o estado completo após cada nó — sem saída parcial durante a geração.

**Solução**: usar `stream_mode="messages"` e iterar sobre tuplas `(chunk, metadata)`:

```python
async for chunk, metadata in agente.astream(
    {"messages": [...]}, config=config, stream_mode="messages"
):
    if isinstance(chunk, AIMessageChunk) and chunk.content:
        print(chunk.content, end="", flush=True)
```

---

### `from langchain.text_splitter import ...` deprecated

```python
# Correto
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Requer: pip install langchain-text-splitters
```

---

### `NotImplementedError: MultiServerMCPClient cannot be used as a context manager`

Mudança de API na versão 0.1.0 do `langchain-mcp-adapters`:

```python
# Antes (quebrava em >= 0.1.0)
async with MultiServerMCPClient(config) as client:
    tools = client.get_tools()

# Depois
client = MultiServerMCPClient(config)
tools = await client.get_tools()   # get_tools() agora é assíncrono
```

---

### `UnsupportedOperation: fileno` ao iniciar servidor MCP no Jupyter

Ver seção "Workaround: `fileno()` no Jupyter" acima.

---

## Parte 7 — Pipeline ML + RAG + Agente para Perfis de Clientes

Integra segmentação K-Means com agentes LangGraph especializados por perfil, e adiciona o conceito de **digital twin** para simular o comportamento individual de cada cliente.

### 7.1 Pipeline de Machine Learning

```
Dados de clientes (features financeiras)
        │
        ▼
StandardScaler → K-Means (N clusters)
        │
        ▼
Perfis estatísticos por cluster
  ├── nomeação automática do segmento (regras sobre as médias)
  ├── FAISS/OpenSearch RAG por cluster (perfil + produtos + estratégia)
  └── Agente LangGraph por segmento (prompt especializado + RAG + tools)
```

**Features de clustering:** `idade`, `renda_mensal`, `saldo_medio`, `transacoes_mes`, `score_credito`, `num_produtos`

**Segmentos típicos:**

| Segmento | Critério | Foco do agente |
|---|---|---|
| Premium Conservador | Alta renda + score > 700 | Investimentos sofisticados, atendimento exclusivo |
| Jovem Digital | Idade < 35 + digital > 65% | App, cashback, crédito ágil, linguagem leve |
| Alto Risco | Inadimplência > 18% | Renegociação, educação financeira, microcrédito |
| Massa Estável | Perfil médio estável | Fidelização, produtos simples, cross-sell gradual |

### 7.2 Fábrica de agentes por cluster

O problema de closure em loop Python é resolvido com uma **função fábrica** que isola o escopo de cada retriever:

```python
def _criar_agente_cluster(cluster_id, segmento, retriever, model):
    # Cada chamada cria um escopo isolado para o retriever
    def _buscar(consulta: str) -> str:
        return "\n\n".join(d.page_content for d in retriever.invoke(consulta))

    buscar_perfil = StructuredTool.from_function(func=_buscar, ...)
    return create_react_agent(model, [buscar_perfil, calcular], prompt=PROMPTS[segmento])
```

### 7.3 Roteamento em tempo real

```python
def classificar_cliente(dados: dict) -> int:
    X = scaler.transform([[dados["idade"], dados["renda_mensal"], ...]])
    return int(kmeans.predict(X)[0])

def consultar_agente(cliente_id, dados, pergunta):
    cluster_id = classificar_cliente(dados)
    agente = agentes_clientes[cluster_id]["agente"]
    return agente.invoke({"messages": [{"role": "user", "content": pergunta}]})
```

---

## Parte 7.4 — Digital Twins: Agentes que Replicam Clientes Individuais

### Conceito

Um **digital twin** é um agente que simula o comportamento de um cliente específico com base nos seus dados reais, respondendo em primeira pessoa.

| | Agente de Segmento | Digital Twin |
|---|---|---|
| Escopo | Grupo de clientes | Cliente individual |
| Dependência | K-Means obrigatório | Dados brutos, **sem clustering** |
| Perspectiva | 3ª pessoa — gerencial | 1ª pessoa — o próprio cliente |
| Prompt | Perfil médio do cluster | Derivado dos dados brutos (renda, score, canal) |
| RAG | Documentos do segmento | Documento individual filtrado por `cliente_id` |
| Uso | Triagem, recomendação | Simulação de comportamento |

> **Separação de responsabilidades:** o twin representa o *indivíduo*, não o grupo.
> Pode ser criado antes ou sem o pipeline de clusterização.

### Casos de uso

- **Teste de oferta antes do envio**: "Como este cliente reagiria a este cartão?"
- **Personalização de comunicação**: ajustar tom e canal por perfil real
- **Análise de cenários**: "Como ele responderia a uma alta de juros de 2 p.p.?"
- **Predição de churn**: simular o cliente após mudanças de produto
- **Validação de copy de marketing**: testar textos com o twin antes do A/B real

### Arquitetura do twin

```
Dados brutos do cliente (CSV / banco de dados)
        │
        ├─► Document individual ──► RAG próprio (FAISS local / OpenSearch filtrado por cliente_id)
        │
        └─► System prompt ────────► "Você É o cliente X. Responda em 1ª pessoa."
                  │                   Perfil comportamental inferido dos dados brutos:
                  │                   renda > 10k + score > 700 → Premium
                  │                   idade < 35 + digital       → Jovem Digital
                  │                   score < 450                → Recuperação
                  │                   demais                     → Massa Estável
                  ▼
        Digital Twin Agent
          tools: meus_dados_individuais | calcular

(RAG de segmento removido: o twin não depende de rótulo derivado de K-Means)
```

### Sistema prompt do twin

O perfil comportamental é **inferido dos dados brutos**, sem depender de nenhum rótulo de cluster:

```python
def _prompt_twin(row: pd.Series) -> str:
    # Derivação do perfil a partir dos features numéricos:
    if renda > 10_000 and score > 700:
        perfil_desc = "Tenho alta renda e excelente crédito. Valorizo produtos sofisticados."
    elif idade < 35 and digital:
        perfil_desc = "Sou jovem e digital. Priorizo praticidade e cashback."
    elif score < 450:
        perfil_desc = "Estou regularizando minha situação. Busco soluções acessíveis."
    else:
        perfil_desc = "Valorizo segurança e custo-benefício."
    return (
        f"Você é o gêmeo digital do cliente {row['cliente_id']}. "
        f"Simule como este cliente pensaria com base no perfil real:\n"
        f"  Renda: R$ {row['renda_mensal']:,.0f} | Score: {row['score_credito']:.0f}\n"
        f"Perfil comportamental: {perfil_desc}\n"
        f"REGRAS: responda em 1ª pessoa, seja coerente com a situação financeira."
    )
```

### Estratégia de indexação em produção (OpenSearch)

Em vez de criar um índice por cliente (inviável para milhões de registros), usa-se um **índice único** com filtragem por metadado:

```python
# Indexação: todos os clientes no mesmo índice
OpenSearchVectorSearch.from_documents(
    docs,                          # cada doc tem metadata.cliente_id
    embeddings,
    index_name="clientes-digital-twins",
    ...
)

# Recuperação: filtra pelo cliente específico
vs.as_retriever(
    search_kwargs={
        "k": 3,
        "pre_filter": {"term": {"metadata.cliente_id": cliente_id}},
    }
)
```

### Instanciação sob demanda no Lambda

Twins não são pré-carregados (número de clientes pode ser na casa dos milhões). A função `criar_twin_sob_demanda` instancia o agente por requisição. Para uso intensivo, implemente cache LRU ou ElastiCache:

```python
if modo == "twin":
    resultado = pipeline.responder_como_twin(cliente_id, dados, pergunta)
else:
    resultado = pipeline.responder(cliente_id, dados, pergunta)
```

---

## Parte 7.5 — Personas: Arquétipos Nomeados de Segmento

### Conceito

Uma **persona** é um personagem fictício mas estatisticamente representativo do cliente típico de um cluster. Diferente do twin (indivíduo real) e do agente de segmento (3ª pessoa gerencial), a persona fala em 1ª pessoa como um membro arquetípico do grupo.

| | Segmento | Persona | Twin |
|---|---|---|---|
| Representa | Grupo | Arquétipo do grupo | Indivíduo real |
| Voz | 3ª pessoa | **1ª pessoa** | **1ª pessoa** |
| Base | Perfil médio do cluster | Perfil médio + nome fictício | Dados brutos individuais |
| Requer clustering | Sim | Sim | **Não** |
| RAG | Índice do cluster | Índice do cluster (reutilizado) | Índice filtrado por `cliente_id` |
| Uso | Análise gerencial, triagem | Pesquisa UX, design de produto, copy | Simulação de indivíduo específico |

### Arquétipos disponíveis

| Segmento | Persona | Perfil |
|---|---|---|
| Premium Conservador | Carlos, gerente, 52a | Patrimônio consolidado, prioriza segurança e longo prazo |
| Jovem Digital | Júlia, freelancer, 26a | Digital-first, cashback, aprovação rápida pelo app |
| Alto Risco | Roberto, autônomo, 43a | Recuperação financeira, precisa de orientação concreta |
| Massa Estável | Ana, funcionária pública, 38a | Estabilidade, proteção familiar, sem surpresas |

### Quando usar cada modo

```
Pergunta: "Como este cliente reagiria ao nosso novo cartão?"
                    │
         ┌──────────┼──────────┬─────────────────┐
         ▼          ▼          ▼                  ▼
     segmento   persona     persona           twin
  (3ª pessoa,  cluster 0   cluster 1...N   (1ª pessoa,
  visão        (Carlos)    (Júlia, etc.)   indivíduo real,
  gerencial)   1ª pessoa   1ª pessoa       sem clustering)
```

### Lambda — modo persona

```json
// Por cluster_id direto:
{ "cluster_id": 2, "pergunta": "O que você acha deste produto?", "modo": "persona" }

// Por dados_cliente (classifica automaticamente):
{ "dados_cliente": { "idade": 45, "renda_mensal": 5500, ... }, "pergunta": "...", "modo": "persona" }
```

Resposta:
```json
{ "cluster_id": 2, "segmento": "Massa Estável", "persona_nome": "Ana", "modo": "persona", "resposta": "..." }
```

---

## aws_pipeline_clientes.py — Guia de Produção

### Fluxo completo

```
SageMaker Processing Job (--mode pipeline)
  │
  ├── 1. Digital twins → OpenSearch (clientes-digital-twins)
  │       dados brutos individuais, independente de clustering
  │
  ├── 2. K-Means → estatísticas por cluster (sem nomear segmentos)
  │
  ├── 3. Athena/Glue Catalog → nomes e metadados de segmentos
  │       cluster_id → segmento_nome, persona_*, prompt_segmento, produtos
  │       (definidos e mantidos pelo time de dados, não pelo código)
  │
  ├── 4. Merge estatísticas + Athena → perfis enriquecidos
  │       fallback: heurística local se ATHENA_DATABASE não configurado
  │
  ├── 5. RAG por segmento → OpenSearch (clientes-segmento-{N})
  │       usa nomes e prompts vindos do Athena
  │
  └── 6. KMeans + Scaler + perfis enriquecidos → S3 (modelo_clustering.pkl)
              ↓
Lambda (lambda_handler) — sem dependência de Athena em runtime
  ├── Cold start: carrega perfis enriquecidos do S3 + conecta OpenSearch
  ├── modo=segmento → PipelineInference.responder()
  ├── modo=persona  → PipelineInference.responder_como_persona()
  └── modo=twin     → PipelineInference.responder_como_twin()
              ↓
Resposta JSON
  segmento: { cliente_id, cluster_id, segmento, modo, resposta }
  persona:  { cluster_id, segmento, persona_nome, modo, resposta }
  twin:     { cliente_id, modo, resposta }
```

### Tabela do Glue Catalog — segmentos

O Glue Data Catalog registra a localização e schema da tabela. O Athena executa queries SQL sobre os dados em S3 (Parquet/ORC). A tabela é criada e mantida pelo time de dados, normalmente por um Glue ETL Job ou job de análise exploratória.

```sql
-- DDL de referência (criar via Glue Crawler ou manualmente)
CREATE EXTERNAL TABLE banco_clientes.segmentos_clientes (
    cluster_id        INT,
    segmento_nome     VARCHAR(100),   -- obrigatório
    persona_nome      VARCHAR(80),    -- opcional: nome do arquétipo
    persona_ocupacao  VARCHAR(200),   -- opcional: ocupação/descrição
    persona_canal     VARCHAR(200),   -- opcional: canal preferencial
    persona_contexto  VARCHAR(500),   -- opcional: backstory
    prompt_segmento   VARCHAR(2000),  -- opcional: system prompt do agente
    produtos          VARCHAR(2000)   -- opcional: produtos recomendados
)
STORED AS PARQUET
LOCATION 's3://meu-bucket/segmentos/'
TBLPROPERTIES ('parquet.compression'='SNAPPY');

-- Exemplo de dados
INSERT INTO segmentos_clientes VALUES
  (0, 'Empreendedor Emergente', 'Marcos', 'dono de pequeno negócio, 39 anos', ...),
  (1, 'Aposentado Conservador', 'Dona Maria', 'aposentada, 67 anos', ...),
  (2, 'Jovem Conectado', 'Luiza', 'universitária, 22 anos', ...),
  (3, 'Família em Crescimento', 'Pedro', 'pai de família, 34 anos', ...);
```

> **Por que Athena e não hardcode?** Os nomes de segmento devem refletir a realidade do negócio, não regras `if/elif` no código. Com Athena/Glue, o time de dados pode renomear segmentos, ajustar personas e atualizar prompts sem nenhum deploy de código — basta atualizar a tabela e reprocessar o pipeline.

### Boas práticas AWS implementadas

| Prática | Implementação |
|---|---|
| Clientes AWS fora do handler | `_s3_client`, `_sm_client`, `_athena_client`, `_boto_session` no módulo |
| Nomes de segmento via Glue Catalog | `carregar_segmentos_athena()` — sem vocabulário hardcoded |
| Credenciais via IAM Role | `boto3.session.Session().get_credentials()` |
| Segredos via Secrets Manager | `get_anthropic_key()` — nunca env var em texto claro |
| Verificação de ownership S3 | `ExpectedBucketOwner` em todas as chamadas S3 |
| Autenticação OpenSearch via IAM | `AWS4Auth` com SigV4 (managed: `es`, serverless: `aoss`) |
| Singleton no Lambda | `_pipeline_instance` reutilizado entre invocações (warm start) |
| numpy reproducível | `np.random.default_rng(42)` em vez de `np.random.seed` |

---

## Referências

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangChain Docs](https://python.langchain.com/)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [DeepEval Docs](https://docs.confident-ai.com/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/)
