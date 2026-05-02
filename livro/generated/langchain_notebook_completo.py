# Arquivo gerado automaticamente a partir de langchain.ipynb
# Conteudo completo dos blocos de codigo do notebook

# ===== cell_003 =====
# Instala todas as dependências necessárias para o notebook
!pip install -q \
    langgraph \
    langchain \
    langchain-anthropic \
    langchain-community \
    langchain-text-splitters \
    langchain-mcp-adapters \
    faiss-cpu \
    sentence-transformers \
    psycopg2-binary \
    mcp \
    python-dotenv \
    duckduckgo-search \
    wikipedia \
    httpx \
    deepeval \
    scikit-learn

# Opcional (produção): pip install langchain-tavily
print("✅ Dependências instaladas com sucesso!")

# ===== cell_005 =====
import os
import warnings
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("Configure ANTHROPIC_API_KEY no arquivo .env")

print(f"✅ Chave API configurada: {ANTHROPIC_API_KEY[:20]}...")

# ─── Suprime o aviso de migração do LangGraph 1.0 ────────────────────────────
# create_react_agent (langgraph.prebuilt) é a API correta para agentes stateful
# com checkpointer e prompt. A função langchain.agents.create_agent tem assinatura
# incompatível (não suporta checkpointer, prompt como string, state_modifier, etc.)
# O aviso será removido quando o LangGraph unificar a API em V2.0.
warnings.filterwarnings("ignore", message=".*create_react_agent.*")

print("✅ Warning de migração LangGraph 1.0 suprimido")

# ===== cell_007 =====
from plantuml_helper import show_plantuml

show_plantuml("""
@startuml
skinparam backgroundColor #FFFFFF
skinparam activity {
  StartColor #2E7D32
  EndColor #C62828
  BackgroundColor #E3F2FD
  BorderColor #1565C0
  FontSize 13
}

start
:Usuario envia pergunta;
:Agente LangGraph interpreta contexto;

if (Precisa chamar ferramenta?) then (sim)
  :Seleciona tool adequada;
  :Executa tool;
  :Recebe resultado da tool;
  :Atualiza raciocinio;
else (nao)
  :Usa conhecimento do modelo;
endif

:Gera resposta final;
:Retorna resposta ao usuario;
stop
@enduml
""")

# ===== cell_008 =====
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

@tool
def calculadora(expressao: str) -> str:
    """Avalia uma expressão matemática. Ex: '2 + 2', '15 * 3.5', '100 / 4'."""
    try:
        allowed = set('0123456789+-*/().,% ')
        if not all(c in allowed for c in expressao):
            return "Expressão inválida"
        return str(eval(expressao))
    except Exception as e:
        return f"Erro: {e}"

@tool
def consultar_clima(cidade: str) -> str:
    """Consulta o clima atual de uma cidade brasileira."""
    clima_mock = {
        "São Paulo": "25°C, Nublado com chance de chuva",
        "Rio de Janeiro": "31°C, Ensolarado e úmido",
        "Brasília": "22°C, Parcialmente nublado e seco",
        "Curitiba": "15°C, Frio com vento sul",
        "Fortaleza": "33°C, Ensolarado e quente",
    }
    return clima_mock.get(cidade, f"Dados não disponíveis para '{cidade}'")

@tool
def converter_moeda(valor: float, de: str, para: str) -> str:
    """Converte entre moedas. Suporta: BRL, USD, EUR."""
    taxas = {"BRL": 1.0, "USD": 5.70, "EUR": 6.20}
    if de not in taxas or para not in taxas:
        return f"Moedas suportadas: {list(taxas.keys())}"
    resultado = valor * taxas[de] / taxas[para]
    return f"{valor:.2f} {de} = {resultado:.2f} {para}"

tools = [calculadora, consultar_clima, converter_moeda]
memory = MemorySaver()
agente = create_react_agent(model, tools, checkpointer=memory)

print("✅ Agente criado com ferramentas:", [t.name for t in tools])

# ===== cell_009 =====
# ─── Configuração de thread (cada thread_id = uma conversa independente) ──────
config = {"configurable": {"thread_id": "conversa-demo-1"}}

def conversar(mensagem: str, config: dict = config):
    """Envia uma mensagem ao agente e retorna a resposta."""
    resultado = agente.invoke(
        {"messages": [{"role": "user", "content": mensagem}]},
        config=config
    )
    return resultado["messages"][-1].content

# ─── Teste 1: Consulta simples ────────────────────────────────────────────────
print("👤 Usuário: Qual é o clima em São Paulo e Curitiba?")
resposta = conversar("Qual é o clima em São Paulo e Curitiba?")
print(f"🤖 Agente: {resposta}\n")

# ─── Teste 2: Demonstrando memória de curto prazo ─────────────────────────────
# O agente lembra da conversa anterior (mesmo thread_id)
print("👤 Usuário: Com esse clima de SP, quanto eu gastaria em USD numa jaqueta de R$300?")
resposta = conversar("Com esse clima de SP, quanto eu gastaria em USD numa jaqueta de R$300?")
print(f"🤖 Agente: {resposta}\n")

# ─── Teste 3: Nova thread = nova conversa (sem memória da anterior) ───────────
config_nova = {"configurable": {"thread_id": "conversa-demo-2"}}
print("👤 Usuário (nova thread): Qual cidade eu perguntei antes?")
resposta = conversar("Qual cidade eu perguntei antes?", config_nova)
print(f"🤖 Agente (sem memória da thread anterior): {resposta}")

# ===== cell_011 =====
import asyncio

# ─── ainvoke: chamada assíncrona básica ───────────────────────────────────────
# Equivalente async de .invoke(). Libera o event loop enquanto o LLM processa.
# Use em: FastAPI, servidores web, qualquer contexto async.

config_ai = {"configurable": {"thread_id": "ainvoke-demo-1"}}

print("⏳ ainvoke: aguardando resposta completa do agente...\n")

resultado = await agente.ainvoke(
    {"messages": [{"role": "user", "content":
        "Qual é o clima em Fortaleza e quanto vale 50 USD em BRL?"}]},
    config=config_ai
)

print("🤖 Resposta completa:")
print(resultado["messages"][-1].content)

# ─── Comparação sync vs async ─────────────────────────────────────────────────
print("\n" + "-" * 55)
print("📌 sync  → agente.invoke()   — bloqueia a thread até terminar")
print("📌 async → await agente.ainvoke() — libera o event loop")

# ===== cell_012 =====
from langchain_core.messages import AIMessageChunk

# ─── astream: streaming token a token ────────────────────────────────────────
# No LangGraph 1.0+, astream() tem diferentes stream_mode:
#
#   stream_mode="values"   → estado completo após cada nó  (padrão)
#   stream_mode="updates"  → delta do estado por nó
#   stream_mode="messages" → (AIMessageChunk, metadata) token a token  ← use para streaming real
#
# stream_mode="messages" retorna tuplas (chunk, metadata) onde chunk é AIMessageChunk.

config_s = {"configurable": {"thread_id": "stream-demo-1"}}

print("📡 astream (stream_mode='messages'): exibindo tokens conforme são gerados\n")
print("🤖 Resposta: ", end="", flush=True)

tool_chamada = False
async for chunk, metadata in agente.astream(
    {"messages": [{"role": "user", "content":
        "Explique o que é o padrão ReAct em 3 tópicos curtos."}]},
    config=config_s,
    stream_mode="messages"       # ← chave para streaming real
):
    if isinstance(chunk, AIMessageChunk):
        # Conteúdo de texto gerado pelo LLM
        if chunk.content:
            print(chunk.content, end="", flush=True)
        # Tool call sendo construída (streaming parcial da chamada)
        if chunk.tool_call_chunks:
            if not tool_chamada:
                print(f"\n🔧 [tool call em progresso]", end="", flush=True)
                tool_chamada = True

print("\n")  # quebra de linha final

# ─── Comparação dos stream_mode disponíveis ───────────────────────────────────
print("─" * 55)
print("stream_mode='values'   → estado completo por nó (padrão)")
print("stream_mode='updates'  → dict {nó: delta_estado}")
print("stream_mode='messages' → (AIMessageChunk, meta) token a token  ✅ streaming real")

# ===== cell_014 =====
# ─── Instalação do MemPalace ─────────────────────────────────────────────────
# Instala MemPalace localmente (sem dependências cloud)
!pip install -q mempalace

print("✅ MemPalace instalado!")
print("📁 Memórias serão armazenadas em: ~/.mempalace/langchain_agent")

# ===== cell_015 =====
import subprocess
import json
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ─── Configuração do MemPalace ─────────────────────────────────────────────── 
PALACE_PATH = Path.home() / ".mempalace" / "langchain_agent"
PALACE_PATH.mkdir(parents=True, exist_ok=True)

print(f"📍 MemPalace configurado em: {PALACE_PATH}")

# ─── Ferramentas MemPalace para o Agente ───────────────────────────────────── 

@tool
def memoria_longo_prazo(consulta: str) -> str:
    """Busca em memórias persistentes de conversas e decisões anteriores.
    Use para: relembrar decisões passadas, contexto de projetos, preferências do usuário."""
    
    try:
        # Comando: mempalace search "consulta" --palace-path PALACE_PATH
        result = subprocess.run([
            "mempalace", "search", consulta, 
            "--palace-path", str(PALACE_PATH)
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            return f"🧠 Memórias encontradas:\n{result.stdout.strip()}"
        else:
            return f"🔍 Nenhuma memória encontrada para: '{consulta}'"
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"⚠️ MemPalace não disponível: {e}"

class SalvarMemoriaInput(BaseModel):
    conteudo: str = Field(description="Conteúdo importante para salvar")
    topico: str = Field(description="Tópico/categoria (ex: 'decisao_tecnica', 'preferencia_usuario')")
    
@tool
def salvar_memoria_importante(conteudo: str, topico: str) -> str:
    """Salva informação importante na memória de longo prazo.
    Use para: decisões importantes, descobertas, preferências do usuário."""
    
    try:
        # Comando: mempalace add-drawer --wing langchain_agent --room topico --content conteudo
        result = subprocess.run([
            "mempalace", "add-drawer",
            "--wing", "langchain_agent", 
            "--room", topico,
            "--content", conteudo,
            "--palace-path", str(PALACE_PATH)
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return f"✅ Memória salva em Wing: langchain_agent, Room: {topico}"
        else:
            return f"⚠️ Erro ao salvar: {result.stderr}"
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"⚠️ MemPalace não disponível: {e}"

@tool 
def carregar_contexto_essencial() -> str:
    """Carrega contexto essencial (~170 tokens) de sessões anteriores.
    Use no início de conversas para recuperar contexto importante."""
    
    try:
        # Comando: mempalace wake-up --palace-path PALACE_PATH
        result = subprocess.run([
            "mempalace", "wake-up",
            "--palace-path", str(PALACE_PATH)
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            return f"🌅 Contexto carregado:\n{result.stdout.strip()}"
        else:
            return "📝 Nenhum contexto essencial encontrado ainda. Construa memórias primeiro!"
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"⚠️ MemPalace não disponível: {e}"

print("🔧 Ferramentas MemPalace criadas:")
print("   • memoria_longo_prazo() - busca memórias persistentes")  
print("   • salvar_memoria_importante() - salva info relevante")
print("   • carregar_contexto_essencial() - recupera contexto de ~170 tokens")

# ===== cell_016 =====
# ─── Agente Híbrido: Sistema Atual + MemPalace ─────────────────────────────
# Combina: FAISS (médio prazo) + MemPalace (longo prazo) + ferramentas existentes

# Ferramentas existentes do projeto
ferramentas_existentes = [
    calculadora, consultar_clima, converter_moeda,
    buscar_conhecimento  # RAG com FAISS
]

# Novas ferramentas MemPalace  
ferramentas_mempalace = [
    memoria_longo_prazo,
    salvar_memoria_importante, 
    carregar_contexto_essencial
]

# Agente híbrido com ambas as capacidades de memória
todas_ferramentas_hibridas = ferramentas_existentes + ferramentas_mempalace
memory_hibrida = MemorySaver()  # Curto prazo (in-session)

agente_mempalace = create_react_agent(
    model, 
    todas_ferramentas_hibridas, 
    checkpointer=memory_hibrida
)

print(f"🧠 Agente híbrido criado com {len(todas_ferramentas_hibridas)} ferramentas:")
print("\n📍 Capacidades de Memória:")
print("   • Curto prazo: MemorySaver (thread_id)")
print("   • Médio prazo: FAISS RAG (buscar_conhecimento)")  
print("   • Longo prazo: MemPalace (memoria_longo_prazo)")
print("\n🔧 Ferramentas disponíveis:")
for tool in todas_ferramentas_hibridas:
    categoria = "MemPalace" if tool.name in [t.name for t in ferramentas_mempalace] else "Existente"
    print(f"   • {tool.name} ({categoria})")

# ===== cell_017 =====
# ─── Demo: Agente com Memória de Longo Prazo ────────────────────────────────

config_demo = {"configurable": {"thread_id": "mempalace-demo-1"}}

async def demo_memoria_longo_prazo():
    """Demonstra as capacidades do agente híbrido com MemPalace."""
    
    print("🚀 Demonstração: Agente + MemPalace")
    print("=" * 60)
    
    # 1. Carregamento de contexto essencial
    print("\n1️⃣ Carregando contexto de sessões anteriores...")
    resultado1 = agente_mempalace.invoke({
        "messages": [{"role": "user", "content": 
            "Carregue o contexto essencial de nossas conversas anteriores."}]
    }, config=config_demo)
    print(f"🤖 {resultado1['messages'][-1].content}")
    
    # 2. Salvando uma decisão importante
    print("\n2️⃣ Salvando decisão técnica importante...")
    resultado2 = agente_mempalace.invoke({
        "messages": [{"role": "user", "content": 
            "Salve esta decisão importante: 'Decidimos usar LangGraph + MemPalace para memória persistente porque combina RAG (médio prazo) com armazenamento verbatim (longo prazo), atingindo 96.6% no LongMemEval vs ~70% do FAISS puro. Decisão tomada em abril 2026.' Use o tópico 'arquitetura_ai'."}]
    }, config=config_demo)  
    print(f"🤖 {resultado2['messages'][-1].content}")
    
    # 3. Consultando memórias de conversas anteriores
    print("\n3️⃣ Buscando en memórias sobre decisões de arquitetura...")
    resultado3 = agente_mempalace.invoke({
        "messages": [{"role": "user", "content": 
            "Busque em memórias anteriores sobre 'decisões de arquitetura' ou 'LangGraph'."}]
    }, config=config_demo)
    print(f"🤖 {resultado3['messages'][-1].content}")
    
    # 4. Testando capacidade híbrida: RAG + MemPalace
    print("\n4️⃣ Pergunta que usa tanto RAG quanto memórias persistentes...")
    resultado4 = agente_mempalace.invoke({
        "messages": [{"role": "user", "content": 
            "Explique as diferenças entre MemorySaver e MemPalace, usando tanto a base de conhecimento técnica quanto decisões que já salvamos."}]
    }, config=config_demo)
    print(f"🤖 {resultado4['messages'][-1].content}")

print("📋 Execute: await demo_memoria_longo_prazo()")
print("🔍 Isso demonstrará as 3 camadas de memória trabalhando juntas:")

# ===== cell_019 =====
# ─── astream_events: visibilidade total do ciclo interno do agente ────────────
# Emite eventos granulares: tokens gerados, chamadas de tool, estados do grafo.
# Use para: observabilidade, debugging, progress bars, logs de auditoria.

print("🔬 astream_events: monitorando o ciclo interno do agente\n")
config_ev = {"configurable": {"thread_id": "events-demo-1"}}

tool_calls_log = []

async for event in agente.astream_events(
    {"messages": [{"role": "user", "content":
        "Qual é o clima em Brasília e converta 200 USD para EUR?"}]},
    config=config_ev,
    version="v2"   # versão recomendada — eventos mais detalhados
):
    kind  = event["event"]
    name  = event.get("name", "")

    if kind == "on_chat_model_stream":
        # Token gerado pelo LLM em tempo real
        token = event["data"]["chunk"].content
        if token:
            print(token, end="", flush=True)

    elif kind == "on_tool_start":
        # Agente decidiu chamar uma ferramenta
        print(f"\n\n🔧 [TOOL START] {name}")
        print(f"   → Input: {event['data'].get('input', {})}")
        tool_calls_log.append(name)

    elif kind == "on_tool_end":
        # Ferramenta retornou resultado
        output = event["data"].get("output", "")
        print(f"   ← Output: {output}")

    elif kind == "on_chain_start" and name == "LangGraph":
        print("📌 [GRAFO] Iniciando execução do agente")

    elif kind == "on_chain_end" and name == "LangGraph":
        print("\n\n📌 [GRAFO] Execução concluída")

print(f"\n📊 Ferramentas chamadas nesta execução: {tool_calls_log}")

# ===== cell_020 =====
import time

# ─── asyncio.gather: execução paralela de múltiplos agentes ──────────────────
# Envia N perguntas simultaneamente ao LLM sem esperar uma por uma.
# Ideal para pipelines de processamento em lote.

async def processar_pergunta(pergunta: str, thread_id: str) -> dict:
    """Wrapper async para invocar o agente com uma pergunta e medir o tempo."""
    config = {"configurable": {"thread_id": thread_id}}
    resultado = await agente.ainvoke(
        {"messages": [{"role": "user", "content": pergunta}]},
        config=config
    )
    return {"pergunta": pergunta, "resposta": resultado["messages"][-1].content}

perguntas = [
    ("Qual é o clima em São Paulo?",        "parallel-sp"),
    ("Qual é o clima em Rio de Janeiro?",   "parallel-rj"),
    ("Converta 500 EUR para BRL",           "parallel-eur"),
    ("Calcule 15% de 2800",                 "parallel-calc"),
]

# ─── Execução paralela ────────────────────────────────────────────────────────
print(f"🚀 gather: {len(perguntas)} perguntas em paralelo...\n")
t0 = time.perf_counter()

resultados = await asyncio.gather(*[
    processar_pergunta(p, tid) for p, tid in perguntas
])

elapsed = time.perf_counter() - t0
print(f"⏱️  Tempo total: {elapsed:.1f}s  |  Média por pergunta: {elapsed/len(perguntas):.1f}s\n")

for r in resultados:
    print(f"❓ {r['pergunta']}")
    print(f"🤖 {r['resposta'][:120]}\n")

# ─── Comparação: execução sequencial (comentada) ──────────────────────────────
# t0 = time.perf_counter()
# for p, tid in perguntas:
#     await processar_pergunta(p, tid)   # aguarda uma por uma
# print(f"Sequencial: {time.perf_counter() - t0:.1f}s")

# ===== cell_021 =====
import asyncio
import httpx

# ─── Async tools: ferramentas com I/O assíncrono ─────────────────────────────
# Use `async def` quando a tool faz I/O (HTTP, banco, arquivo).
# O LangGraph executa async tools corretamente sem bloquear o event loop.

@tool
async def buscar_cotacao_async(moeda: str) -> str:
    """Busca a cotação de uma moeda em relação ao BRL de forma assíncrona.
    Suporta: USD, EUR, GBP, ARS, BTC.
    """
    # Em produção: substitua por httpx.AsyncClient chamando uma API real de câmbio
    await asyncio.sleep(0.05)  # simula latência de rede sem bloquear o loop
    cotacoes = {"USD": "5.72", "EUR": "6.21", "GBP": "7.18", "ARS": "0.006", "BTC": "312450.00"}
    moeda = moeda.upper()
    if moeda not in cotacoes:
        return f"Moeda não suportada. Use: {list(cotacoes.keys())}"
    return f"1 {moeda} = R$ {cotacoes[moeda]}"


@tool
async def buscar_conteudo_url_async(url: str) -> str:
    """Busca o conteúdo de uma URL pública de forma assíncrona (primeiros 800 caracteres).
    Use para acessar APIs ou páginas sem bloquear outras operações paralelas.
    """
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.text[:800]
    except Exception as e:
        return f"Erro ao acessar URL: {e}"


# ─── Agente com async tools ───────────────────────────────────────────────────
agente_async_tools = create_agent(
    model,
    [buscar_cotacao_async, buscar_conteudo_url_async, calculadora],
    checkpointer=MemorySaver()
)

config_at = {"configurable": {"thread_id": "async-tools-1"}}
resultado = await agente_async_tools.ainvoke(
    {"messages": [{"role": "user", "content":
        "Qual é a cotação do USD e do EUR hoje? Calcule quanto 1500 EUR valem em reais."}]},
    config=config_at
)
print("🤖 Agente (async tools):", resultado["messages"][-1].content)

# ===== cell_023 =====
from plantuml_helper import show_plantuml

show_plantuml("""
@startuml
skinparam backgroundColor #FEFEFE
skinparam activity {
    StartColor #4CAF50
    EndColor #C62828
    BackgroundColor #E3F2FD
    BorderColor #1976D2
    FontSize 13
}
skinparam note {
    BackgroundColor #FFF9C4
    BorderColor #F57C00
}

start
:Pergunta do Usuario;
:Gera Embedding da pergunta;
note right
  Modelo: all-MiniLM-L6-v2
  Vetor: 384 dimensoes
end note

:Busca Semantica no Vector Store;
note right
  FAISS Index
  Top-K documentos
  Similaridade cosseno
end note

:Recupera documentos mais relevantes;
:Combina com Memoria de Curto Prazo;
note right
  MemorySaver
  Historico da sessao
  thread_id
end note

:LLM processa Prompt + Contexto + Historico;
:Gera resposta fundamentada;
stop
@enduml
""")

# ===== cell_024 =====
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ─── Base de conhecimento: documentos sobre LangChain/LangGraph ──────────────
documentos_raw = [
    Document(
        page_content="""
        LangGraph é um framework para construir agentes e sistemas multi-agente usando grafos de estado.
        Ele estende o LangChain com a capacidade de criar fluxos cíclicos (loops), essenciais para agentes
        que precisam raciocinar e agir em múltiplos passos. O LangGraph suporta checkpointing de estado,
        permitindo persistência entre interações. Ideal para: chatbots, agentes de pesquisa,
        sistemas de automação, e pipelines de dados complexos.
        """,
        metadata={"source": "langgraph_docs", "topico": "LangGraph"}
    ),
    Document(
        page_content="""
        LangChain é um framework open-source para desenvolver aplicações com modelos de linguagem.
        Fornece abstrações para: Chains (sequências de operações), Prompts (templates de instruções),
        Memory (gerenciamento de contexto), Tools (ferramentas externas), e Agents (agentes autônomos).
        Suporta múltiplos provedores de LLM: OpenAI, Anthropic, Google, Hugging Face, e outros.
        Versão atual: LangChain 0.3+ com separação em pacotes modulares.
        """,
        metadata={"source": "langchain_docs", "topico": "LangChain"}
    ),
    Document(
        page_content="""
        RAG (Retrieval-Augmented Generation) é uma técnica que combina recuperação de informações
        com geração de texto. Fluxo: 1) Indexar documentos como embeddings em vector store,
        2) Receber pergunta do usuário, 3) Buscar documentos relevantes por similaridade semântica,
        4) Injetar contexto recuperado no prompt do LLM, 5) Gerar resposta fundamentada nos documentos.
        Benefício: reduz alucinações e permite conhecimento atualizado além do treinamento do modelo.
        """,
        metadata={"source": "rag_docs", "topico": "RAG"}
    ),
    Document(
        page_content="""
        Embeddings são representações vetoriais de texto em espaço de alta dimensão.
        Textos semanticamente similares têm vetores próximos (alta similaridade cosseno).
        Modelos populares: OpenAI text-embedding-3-small, Sentence-BERT, all-MiniLM-L6-v2.
        all-MiniLM-L6-v2 é um modelo leve (22M parâmetros) e eficiente, ideal para uso local.
        FAISS (Facebook AI Similarity Search) é uma biblioteca eficiente para busca por similaridade
        em grandes conjuntos de vetores.
        """,
        metadata={"source": "embeddings_docs", "topico": "Embeddings"}
    ),
    Document(
        page_content="""
        MemorySaver no LangGraph é um checkpointer em memória que salva o estado do grafo.
        Cada conversa é identificada por um thread_id único. Permite retomar conversas do ponto
        onde pararam dentro da mesma sessão de Python. Para persistência entre sessões,
        use SqliteSaver ou PostgresSaver. A memória de curto prazo é limitada ao contexto
        da janela de contexto do LLM (tipicamente 32k-200k tokens).
        """,
        metadata={"source": "memory_docs", "topico": "Memória"}
    ),
    Document(
        page_content="""
        MCP (Model Context Protocol) é um protocolo aberto criado pela Anthropic para padronizar
        como aplicações fornecem contexto e ferramentas para modelos de IA. Funciona como
        um protocolo cliente-servidor onde: Servidores MCP expõem recursos (tools, prompts, resources)
        e Clientes MCP (agentes) consomem esses recursos. Permite criar ecossistema de integrações
        reutilizáveis. Suporta transporte via stdio (processo local) ou SSE (HTTP remoto).
        """,
        metadata={"source": "mcp_docs", "topico": "MCP"}
    ),
]

# ─── Divisão de documentos em chunks ─────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,    # Tamanho máximo de cada chunk em caracteres
    chunk_overlap=50,  # Sobreposição entre chunks (preserva contexto)
    length_function=len
)
chunks = text_splitter.split_documents(documentos_raw)

print(f"✅ {len(documentos_raw)} documentos → {len(chunks)} chunks após divisão")
print(f"\nExemplo de chunk:")
print(f"  Conteúdo: {chunks[0].page_content[:100]}...")
print(f"  Metadata: {chunks[0].metadata}")

# ===== cell_025 =====
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# ─── Modelo de embeddings (local, gratuito) ───────────────────────────────────
# all-MiniLM-L6-v2: modelo leve e eficiente para embeddings em português e inglês
# Download automático na primeira execução (~80MB)
print("⏳ Carregando modelo de embeddings (pode demorar na primeira vez)...")
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# ─── Vector Store: MEMÓRIA DE MÉDIO PRAZO ─────────────────────────────────────
# FAISS indexa os chunks como vetores para busca semântica eficiente
vector_store = FAISS.from_documents(chunks, embeddings)

# ─── Salvar/Carregar o índice (persistência) ──────────────────────────────────
vector_store.save_local("./faiss_index")
# Para recarregar em sessões futuras:
# vector_store = FAISS.load_local("./faiss_index", embeddings, allow_dangerous_deserialization=True)

print("✅ Vector store criado e salvo em ./faiss_index")
print(f"   Total de vetores indexados: {vector_store.index.ntotal}")

# ─── Testando busca semântica ─────────────────────────────────────────────────
print("\n📍 Teste de busca semântica:")
resultados = vector_store.similarity_search("como funciona a memória em agentes?", k=2)
for i, doc in enumerate(resultados, 1):
    print(f"\n  [{i}] Fonte: {doc.metadata.get('topico', 'N/A')}")
    print(f"      Trecho: {doc.page_content[:120].strip()}...")

# ===== cell_026 =====
from langchain_core.tools import tool

retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})

@tool
def buscar_conhecimento(consulta: str) -> str:
    """Busca informações na base de conhecimento sobre LangChain, LangGraph, RAG, Embeddings e MCP.
    Use para responder perguntas técnicas sobre esses temas.
    """
    docs = retriever.invoke(consulta)
    if not docs:
        return "Nenhuma informação encontrada sobre esse tema."
    return "\n\n".join([
        f"[Fonte: {doc.metadata.get('topico', 'geral')}]\n{doc.page_content.strip()}"
        for doc in docs
    ])

tools_rag = [calculadora, consultar_clima, converter_moeda, buscar_conhecimento]
memory_rag = MemorySaver()
agente_rag = create_react_agent(model, tools_rag, checkpointer=memory_rag)

print("✅ Agente RAG criado com ferramentas:", [t.name for t in tools_rag])

# ===== cell_027 =====
config_rag = {"configurable": {"thread_id": "rag-demo-1"}}

def conversar_rag(mensagem: str):
    resultado = agente_rag.invoke(
        {"messages": [{"role": "user", "content": mensagem}]},
        config=config_rag
    )
    return resultado["messages"][-1].content

# ─── Teste: RAG com busca na base de conhecimento ────────────────────────────
print("👤 Usuário: O que é o LangGraph e para que serve?")
resposta = conversar_rag("O que é o LangGraph e para que serve?")
print(f"🤖 Agente: {resposta}\n")
print("-" * 60)

# ─── Teste: Memória curto prazo + RAG (médio prazo) ──────────────────────────
print("\n👤 Usuário: Como funciona o RAG que você mencionou?")
resposta = conversar_rag("Como funciona o RAG que você mencionou?")
print(f"🤖 Agente: {resposta}")

# ===== cell_029 =====
from plantuml_helper import show_plantuml

show_plantuml("""
@startuml
skinparam backgroundColor #FFFFFF
skinparam activity {
  StartColor #2E7D32
  EndColor #C62828
  BackgroundColor #F3E5F5
  BorderColor #6A1B9A
  FontSize 13
}

start
:Desenvolvedor define função;
:Aplica decorator @tool;
:Escreve docstring clara;
:Define type hints/Pydantic;
:Tool e registrada no agente;

if (LLM precisa da tool?) then (sim)
  :LLM seleciona tool pela docstring;
  :Valida parametros pelo schema;
  :Executa tool;
  :Recebe retorno estruturado;
else (nao)
  :Continua sem tool;
endif

:Compõe resposta final;
stop
@enduml
""")

# ===== cell_030 =====
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field
from typing import Literal
import statistics
import json
from datetime import datetime

# ─── Skill 1: Simples (com @tool e type hints) ───────────────────────────────
@tool
def verificar_cnpj(cnpj: str) -> str:
    """Verifica se um CNPJ tem formato válido (apenas validação de formato, não consulta Receita).
    Aceita formatos: '12.345.678/0001-90' ou '12345678000190'.
    """
    # Remove formatação
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj_limpo) != 14:
        return f"❌ CNPJ inválido: deve ter 14 dígitos (recebido: {len(cnpj_limpo)})"
    if len(set(cnpj_limpo)) == 1:
        return "❌ CNPJ inválido: todos os dígitos iguais"
    # Formata
    formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
    return f"✅ CNPJ com formato válido: {formatado}"


# ─── Skill 2: Com Pydantic (validação rigorosa + documentação detalhada) ─────
class AnalisarDadosInput(BaseModel):
    dados: list[float] = Field(
        description="Lista de valores numéricos para análise",
        min_length=2  # Precisa de ao menos 2 valores
    )
    operacao: Literal["media", "mediana", "desvio_padrao", "minimo", "maximo", "resumo"] = Field(
        description="Operação estatística: 'media', 'mediana', 'desvio_padrao', 'minimo', 'maximo', 'resumo'"
    )

def _analisar_dados(dados: list[float], operacao: str) -> str:
    """Implementação interna da análise estatística."""
    ops = {
        "media": lambda d: f"Média: {statistics.mean(d):.4f}",
        "mediana": lambda d: f"Mediana: {statistics.median(d):.4f}",
        "desvio_padrao": lambda d: f"Desvio Padrão: {statistics.stdev(d):.4f}",
        "minimo": lambda d: f"Mínimo: {min(d):.4f}",
        "maximo": lambda d: f"Máximo: {max(d):.4f}",
        "resumo": lambda d: (
            f"N={len(d)} | Média={statistics.mean(d):.2f} | "
            f"Mediana={statistics.median(d):.2f} | "
            f"Std={statistics.stdev(d):.2f} | "
            f"Min={min(d):.2f} | Max={max(d):.2f}"
        )
    }
    return ops[operacao](dados)

skill_analise = StructuredTool.from_function(
    func=_analisar_dados,
    name="analisar_dados",
    description="Realiza análise estatística de uma lista de números. "
                "Use para calcular médias, medianas, desvios padrão e resumos estatísticos.",
    args_schema=AnalisarDadosInput,
    return_direct=False  # O agente processa o resultado antes de responder
)

print("✅ Skills criadas:", ["verificar_cnpj", "analisar_dados"])

# ===== cell_031 =====
class FormatarRelatorioInput(BaseModel):
    titulo: str = Field(description="Título do relatório")
    dados: dict = Field(description="Dicionário com dados a serem incluídos no relatório")
    formato: Literal["markdown", "json", "texto"] = Field(
        default="markdown", description="Formato de saída: 'markdown', 'json', ou 'texto'"
    )

def _formatar_relatorio(titulo: str, dados: dict, formato: str = "markdown") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if formato == "json":
        return json.dumps({"titulo": titulo, "timestamp": timestamp, "dados": dados},
                         ensure_ascii=False, indent=2)
    elif formato == "markdown":
        linhas = [f"# {titulo}", f"*Gerado em: {timestamp}*", "", "## Dados", ""]
        for chave, valor in dados.items():
            if isinstance(valor, list):
                linhas.append(f"**{chave}:**")
                linhas.extend([f"  - {item}" for item in valor])
            else:
                linhas.append(f"**{chave}:** {valor}")
        return "\n".join(linhas)
    else:
        linhas = [f"=== {titulo} ===", f"Data: {timestamp}", "-" * 40]
        for chave, valor in dados.items():
            linhas.append(f"{chave}: {valor}")
        return "\n".join(linhas)

skill_relatorio = StructuredTool.from_function(
    func=_formatar_relatorio,
    name="formatar_relatorio",
    description="Cria um relatório formatado. Útil para organizar e apresentar informações.",
    args_schema=FormatarRelatorioInput
)

todas_skills = [calculadora, consultar_clima, converter_moeda,
                buscar_conhecimento, verificar_cnpj, skill_analise, skill_relatorio]

memory_skills = MemorySaver()
agente_completo = create_react_agent(model, todas_skills, checkpointer=memory_skills)

print(f"✅ Agente completo com {len(todas_skills)} skills:")
for skill in todas_skills:
    print(f"   • {skill.name}")

# ===== cell_032 =====
config_skills = {"configurable": {"thread_id": "skills-demo-1"}}

def usar_agente(mensagem: str):
    resultado = agente_completo.invoke(
        {"messages": [{"role": "user", "content": mensagem}]},
        config=config_skills
    )
    return resultado["messages"][-1].content

# ─── Teste de skills encadeadas ───────────────────────────────────────────────
print("👤 Usuário: Analise esses dados de vendas e crie um relatório em markdown:")
print("   Vendas dos últimos 6 meses: [15000, 18500, 12300, 21000, 19800, 24500]")
pergunta = """Analise esses dados de vendas mensais e crie um relatório em markdown:
Vendas: [15000, 18500, 12300, 21000, 19800, 24500]
Inclua estatísticas (média, mediana, desvio padrão) e converta a média para USD."""

resposta = usar_agente(pergunta)
print(f"\n🤖 Agente:\n{resposta}")

# ===== cell_034 =====
from plantuml_helper import show_plantuml

show_plantuml("""
@startuml
skinparam backgroundColor #FFFFFF
skinparam activity {
  StartColor #2E7D32
  EndColor #C62828
  BackgroundColor #FFF3E0
  BorderColor #EF6C00
  FontSize 13
}

start
:Recebe pergunta do usuario;
:Agente classifica tipo de informacao;

if (Requer informacao atual?) then (sim)
  if (Conceito enciclopedico?) then (sim)
    :Consulta Wikipedia;
  else (nao)
    if (API estruturada disponivel?) then (sim)
      :Consulta API publica;
    else (nao)
      :Realiza busca web (DuckDuckGo/Tavily);
    endif
  endif
else (nao)
  if (Conhecimento interno da empresa?) then (sim)
    :Consulta RAG/Vector Store;
  else (nao)
    :Usa conhecimento do LLM;
  endif
endif

:Consolida contexto;
:Gera resposta com fontes;
stop
@enduml
""")

# ===== cell_035 =====
from langchain_community.tools import DuckDuckGoSearchRun, DuckDuckGoSearchResults
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun
from langchain_core.tools import tool
import httpx
import json

# ─── 1. DuckDuckGo: busca rápida (retorna string com resultado principal) ─────
busca_rapida = DuckDuckGoSearchRun(
    name="busca_rapida",
    description=(
        "Busca rápida na internet via DuckDuckGo. Retorna o trecho mais relevante. "
        "Use para perguntas factuais simples e diretas sobre eventos ou dados atuais."
    )
)

# ─── 2. DuckDuckGo: busca detalhada (retorna lista com título + URL + trecho) ─
busca_detalhada = DuckDuckGoSearchResults(
    name="busca_web",
    description=(
        "Busca na internet retornando múltiplos resultados com título, URL e trecho. "
        "Use quando precisar citar fontes, comparar informações ou verificar claims."
    ),
    num_results=4,
    output_format="list"
)

# ─── 3. Wikipedia em português ────────────────────────────────────────────────
wikipedia_pt = WikipediaQueryRun(
    name="wikipedia",
    description=(
        "Busca informações enciclopédicas na Wikipedia em português. "
        "Use para: conceitos técnicos, história, biografia, ciência, geografia. "
        "NÃO use para informações que mudam frequentemente (preços, notícias recentes)."
    ),
    api_wrapper=WikipediaAPIWrapper(
        lang="pt",
        top_k_results=2,
        doc_content_chars_max=1500
    )
)

# ─── 4. HTTP direto: consulta APIs públicas REST ──────────────────────────────
@tool
def consultar_api(url: str) -> str:
    """Faz GET request a uma URL de API pública (sem autenticação).
    Use para APIs abertas: cotações de câmbio, dados do IBGE, APIs do governo, etc.
    A URL deve estar completa e ser acessível publicamente.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 LangChain-Agent/1.0", "Accept": "application/json"}
        response = httpx.get(url, timeout=10, follow_redirects=True, headers=headers)
        response.raise_for_status()
        conteudo = response.text[:2500]
        try:
            dados = json.loads(conteudo)
            return json.dumps(dados, ensure_ascii=False, indent=2)[:2500]
        except json.JSONDecodeError:
            return conteudo
    except httpx.TimeoutException:
        return "❌ Timeout: URL demorou mais de 10s para responder"
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"❌ Erro: {str(e)}"

tools_web = [busca_rapida, busca_detalhada, wikipedia_pt, consultar_api]

print("✅ Ferramentas de busca web configuradas:")
for t in tools_web:
    print(f"   • {t.name}: {t.description[:70]}...")

# ─── Teste rápido de cada ferramenta ─────────────────────────────────────────
print("\n📍 Teste rápido:")
try:
    r = busca_rapida.invoke("taxa Selic Brasil 2025")
    print(f"   DuckDuckGo rápido: {r[:150]}...")
except Exception as e:
    print(f"   DuckDuckGo rápido: ⚠️ {e}")

try:
    r = wikipedia_pt.invoke("Inteligência artificial")
    print(f"   Wikipedia: {r[:150]}...")
except Exception as e:
    print(f"   Wikipedia: ⚠️ {e}")

# ===== cell_036 =====
memory_web = MemorySaver()
agente_web = create_react_agent(
    model,
    tools_web + [calculadora],
    checkpointer=memory_web,
    prompt=(
        "Você é um assistente que pesquisa informações na internet para responder perguntas.\n\n"
        "Diretrizes:\n"
        "- Use 'busca_web' para informações recentes (notícias, preços, eventos atuais)\n"
        "- Use 'wikipedia' para conceitos, história, ciência e fatos estabelecidos\n"
        "- Use 'consultar_api' para APIs públicas (ex: dados do governo, cotações abertas)\n"
        "- Sempre mencione a fonte das informações (URL ou nome da fonte)\n"
        "- Se os resultados estiverem desatualizados ou contraditórios, diga claramente"
    )
)

config_web = {"configurable": {"thread_id": "web-demo-1"}}

async def pesquisar(mensagem: str):
    resultado = await agente_web.ainvoke(
        {"messages": [{"role": "user", "content": mensagem}]},
        config=config_web
    )
    return resultado["messages"][-1].content

print("👤 Pergunta: Qual é a cotação atual do dólar americano em reais?\n")
resp = await pesquisar("Qual é a cotação atual do dólar americano em reais? Pesquise na internet.")
print(f"🤖 Agente:\n{resp}\n")

print("=" * 65)
print("\n👤 Pergunta: O que é a taxa Selic e quanto R$10.000 rendem em 12 meses?\n")
resp2 = await pesquisar(
    "O que é a taxa Selic? Busque o valor atual na web e calcule quanto R$10.000 rendem em 12 meses."
)
print(f"🤖 Agente:\n{resp2}\n")

print("=" * 65)
print("\n👤 Follow-up: E se eu investir o dobro?\n")
resp3 = await pesquisar("E se eu investir o dobro do valor que mencionei antes?")
print(f"🤖 Agente (memória ativa):\n{resp3}")

# ===== cell_037 =====
# ─── Comparativo de ferramentas de busca para produção ───────────────────────
print("""
┌────────────────────────────────────────────────────────────────────────┐
│          FERRAMENTAS DE BUSCA: COMPARATIVO                             │
├───────────────────┬──────────┬──────────┬─────────┬───────────────────┤
│  Ferramenta       │  Custo   │ API Key  │Qualidade│ Melhor para       │
├───────────────────┼──────────┼──────────┼─────────┼───────────────────┤
│  DuckDuckGo       │  Grátis  │  Não     │  Média  │ Dev / testes      │
│  Wikipedia        │  Grátis  │  Não     │  Alta*  │ Fatos históricos  │
│  Brave Search     │  Grátis* │  Sim     │  Alta   │ Dev / Prod        │
│  Tavily           │  Pago*   │  Sim     │  Alta   │ Produção (LLMs)   │
│  Bing Search API  │  Pago    │  Sim     │  Alta   │ Produção          │
│  Google Custom    │  Pago    │  Sim     │  Máxima │ Produção crítica  │
│  SerpAPI          │  Pago    │  Sim     │  Máxima │ Múltiplos motores │
└───────────────────┴──────────┴──────────┴─────────┴───────────────────┘
* Tavily tem tier gratuito (1000 req/mês) | * Wikipedia não tem dados recentes
""")

# ─── Como substituir DuckDuckGo por Tavily em produção ───────────────────────
print("Para usar Tavily (recomendado para produção):")
print("""
  pip install langchain-tavily

  from langchain_tavily import TavilySearch
  import os

  os.environ["TAVILY_API_KEY"] = "tvly-..."  # https://tavily.com

  tavily = TavilySearch(
      max_results=5,
      include_raw_content=True,   # Retorna conteúdo completo da página
      include_answer=True,        # Inclui resposta direta quando disponível
      search_depth="advanced"     # Busca mais profunda
  )

  # Uso idêntico ao DuckDuckGo:
  tools_web_prod = [tavily, wikipedia_pt, consultar_api]
  agente_prod = create_react_agent(model, tools_web_prod, checkpointer=MemorySaver())
""")

# ===== cell_039 =====
from plantuml_helper import show_plantuml

show_plantuml("""
@startuml
skinparam backgroundColor #FFFFFF
skinparam activity {
  StartColor #2E7D32
  EndColor #C62828
  BackgroundColor #E8F5E9
  BorderColor #2E7D32
  FontSize 13
}

start
:Pergunta do usuario;
:Agente gera resposta inicial;

fork
  :Saida estruturada (Pydantic);
  :Calcula score de confianca;
fork again
  :Forca citacao de fontes;
  :Anexa evidencias;
fork again
  :Auto-reflexao com segundo avaliador;
  :Refina se necessario;
fork again
  :Cross-referencia em fontes externas;
  :Confirma claims criticos;
end fork

:Consolida sinais de confiabilidade;
:Entrega resposta confiavel;
stop
@enduml
""")

# ===== cell_040 =====
from pydantic import BaseModel, Field
from typing import Optional, Literal
from langchain_anthropic import ChatAnthropic

# ─── Schema de resposta confiável ─────────────────────────────────────────────
class RespostaFundamentada(BaseModel):
    """Resposta estruturada com metadados de confiabilidade e rastreabilidade."""

    resposta: str = Field(
        description="Resposta clara, objetiva e fundamentada para o usuário"
    )
    confianca: float = Field(
        description="Nível de confiança de 0.0 (totalmente incerto) a 1.0 (certeza absoluta)",
        ge=0.0, le=1.0
    )
    nivel_confianca: Literal["baixo", "médio", "alto"] = Field(
        description="'baixo' (0.0-0.5), 'médio' (0.5-0.8), 'alto' (0.8-1.0)"
    )
    fontes: list[str] = Field(
        default_factory=list,
        description="URLs, nomes de publicações, ou 'conhecimento do modelo (pode estar desatualizado)'"
    )
    limitacoes: Optional[str] = Field(
        default=None,
        description="Limitações importantes, incertezas ou ressalvas sobre a resposta"
    )
    requer_verificacao_humana: bool = Field(
        description="True para tópicos críticos: saúde, direito, finanças, segurança"
    )

# ─── LLM configurado para saída estruturada ───────────────────────────────────
llm_confiavel = ChatAnthropic(model="claude-sonnet-4-6", temperature=0).with_structured_output(
    RespostaFundamentada
)

def responder_com_confianca(pergunta: str, contexto_web: str = "") -> RespostaFundamentada:
    """Gera resposta estruturada com score de confiança explícito."""

    contexto_extra = f"\n\nInformações encontradas na internet:\n{contexto_web}" if contexto_web else ""

    prompt = f"""Responda à pergunta de forma fundamentada e honesta.{contexto_extra}

Pergunta: {pergunta}

Avalie sua confiança de forma HONESTA e CALIBRADA:
- 1.0 = Fato científico/matemático verificável (ex: velocidade da luz)
- 0.8-0.9 = Informação consolidada e amplamente aceita
- 0.6-0.7 = Bem estabelecido, mas pode ter variações ou estar desatualizado
- 0.4-0.5 = Incerto, múltiplas versões, ou informação dinâmica
- 0.0-0.3 = Especulação, previsão ou informação não verificável"""

    return llm_confiavel.invoke(prompt)

# ─── Demonstração com perguntas de diferentes níveis de certeza ──────────────
exemplos = [
    ("Qual é a velocidade da luz no vácuo?", ""),
    ("Qual é a população atual do Brasil?", ""),
    ("Qual será a taxa Selic no próximo mês?", ""),
]

for pergunta, contexto in exemplos:
    resultado = responder_com_confianca(pergunta, contexto)
    icone = "🟢" if resultado.confianca >= 0.8 else "🟡" if resultado.confianca >= 0.5 else "🔴"
    print(f"{icone} [{resultado.nivel_confianca.upper()} {resultado.confianca:.0%}] {pergunta}")
    print(f"   → {resultado.resposta[:120]}...")
    if resultado.limitacoes:
        print(f"   ⚠️ {resultado.limitacoes}")
    if resultado.requer_verificacao_humana:
        print(f"   👨‍⚕️ Recomenda verificação com especialista")
    print(f"   📚 Fontes: {resultado.fontes}")
    print()

# ===== cell_041 =====
from langchain_core.messages import SystemMessage

# ─── Padrão 2: Citação obrigatória de fontes via system prompt ────────────────
SYSTEM_CITACAO = """Você é um assistente que fornece informações verificadas e fundamentadas.

REGRAS OBRIGATÓRIAS (sem exceção):
1. Cite SEMPRE a fonte de cada informação importante:
   - Busca na web → cite a URL exata
   - Wikipedia → cite "Wikipedia: [Título do artigo]"
   - Conhecimento do modelo → cite "Modelo (pode estar desatualizado)"
2. Se não tiver certeza: diga explicitamente "Não tenho certeza sobre isso"
3. Para tópicos médicos, jurídicos ou financeiros: recomende sempre um especialista
4. Diferencie fatos verificados de opiniões/estimativas

Formato obrigatório ao final de cada resposta:
📚 **Fontes consultadas:**
- [fonte 1]
- [fonte 2]
⚠️ **Ressalvas:** [se houver, ou 'Nenhuma']"""

# Agente com citação obrigatória + busca web
memory_citacao = MemorySaver()
agente_citacao = create_agent(
    model,
    [busca_detalhada, busca_rapida, wikipedia_pt],
    checkpointer=memory_citacao,
    prompt=SYSTEM_CITACAO
)

async def consultar_com_citacao(pergunta: str):
    config = {"configurable": {"thread_id": "citacao-1"}}
    resultado = await agente_citacao.ainvoke(
        {"messages": [{"role": "user", "content": pergunta}]},
        config=config
    )
    return resultado["messages"][-1].content

# ─── Testes ──────────────────────────────────────────────────────────────────
print("👤 Pergunta 1: Benefícios do exercício físico para saúde mental\n")
resp1 = await consultar_com_citacao(
    "Quais são os principais benefícios do exercício físico para a saúde mental?"
)
print(f"🤖 Agente:\n{resp1}\n")

print("=" * 65)
print("\n👤 Pergunta 2: Posso tomar paracetamol com ibuprofeno?\n")
resp2 = await consultar_com_citacao("Posso tomar paracetamol e ibuprofeno juntos?")
print(f"🤖 Agente:\n{resp2}")

# ===== cell_042 =====
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from langchain_core.output_parsers import JsonOutputParser

# ─── Estado compartilhado pelo grafo ─────────────────────────────────────────
class EstadoVerificacao(TypedDict):
    pergunta: str
    contexto_web: str
    resposta_inicial: str
    avaliacao: dict        # {score_confianca, problemas_encontrados, recomendacao, justificativa}
    resposta_final: str
    confianca_final: float
    fontes: list

# ─── Nó 1: Busca informações na web ──────────────────────────────────────────
def buscar_web(state: EstadoVerificacao) -> dict:
    """Usa DuckDuckGo para enriquecer a resposta com dados atuais."""
    try:
        resultados = busca_detalhada.invoke(state["pergunta"])
        return {
            "contexto_web": str(resultados)[:2500],
            "fontes": ["DuckDuckGo Search"]
        }
    except Exception as e:
        return {"contexto_web": f"Busca indisponível: {e}", "fontes": []}

# ─── Nó 2: Gera resposta inicial com base na busca ────────────────────────────
def gerar_resposta(state: EstadoVerificacao) -> dict:
    """Gera resposta inicial fundamentada nas fontes da web."""
    prompt = f"""Responda à pergunta abaixo usando as informações encontradas na internet.
Cite as fontes (URLs) quando disponíveis.

Pergunta: {state['pergunta']}

Resultados da busca:
{state['contexto_web'] or 'Nenhum resultado de busca disponível.'}"""

    resposta = model.invoke(prompt)
    return {"resposta_inicial": resposta.content}

# ─── Nó 3: Auto-avaliação crítica da resposta ────────────────────────────────
def avaliar_resposta(state: EstadoVerificacao) -> dict:
    """Verifica criticamente a resposta: confiança, fontes, consistência."""
    prompt = f"""Você é um verificador de fatos rigoroso. Analise criticamente esta resposta.

Pergunta original: {state['pergunta']}
Resposta gerada: {state['resposta_inicial']}
Fontes consultadas (resumo): {state['contexto_web'][:600]}

Responda APENAS com JSON válido (sem markdown, sem explicação extra):
{{
  "score_confianca": 0.0,
  "problemas_encontrados": "descreva problemas ou escreva 'nenhum'",
  "afirmacoes_sem_fonte": ["lista de claims sem evidência"],
  "recomendacao": "manter | refinar | descartar",
  "justificativa": "motivo objetivo"
}}

Critérios de score:
- 0.9-1.0: fato verificável e amplamente confirmado
- 0.7-0.9: bem fundamentado, poucas incertezas
- 0.5-0.7: parcialmente verificado, possível desatualização
- 0.3-0.5: incerto, múltiplas versões conflitantes
- 0.0-0.3: especulação, não verificável"""

    try:
        chain = model | JsonOutputParser()
        avaliacao = chain.invoke(prompt)
    except Exception:
        avaliacao = {
            "score_confianca": 0.5,
            "problemas_encontrados": "avaliação automática indisponível",
            "afirmacoes_sem_fonte": [],
            "recomendacao": "manter",
            "justificativa": "falha no parser"
        }
    return {"avaliacao": avaliacao}

# ─── Nó 4: Refina ou mantém a resposta ───────────────────────────────────────
def refinar_ou_manter(state: EstadoVerificacao) -> dict:
    """Decide se refina a resposta com base na avaliação."""
    avaliacao = state["avaliacao"]
    score = float(avaliacao.get("score_confianca", 0.5))
    recomendacao = avaliacao.get("recomendacao", "manter")

    if recomendacao in ("manter", "descartar") or score >= 0.80:
        resposta_final = state["resposta_inicial"]
        if score < 0.70:
            aviso = f"\n\n⚠️ *Confiabilidade moderada ({score:.0%}) — recomenda-se verificação adicional.*"
            resposta_final += aviso
        if recomendacao == "descartar":
            resposta_final = (
                f"⚠️ Não foi possível fornecer uma resposta confiável para esta pergunta "
                f"({score:.0%} de confiança).\n\n"
                f"Motivo: {avaliacao.get('justificativa', '')}\n\n"
                f"Sugestão de resposta original (não verificada):\n{state['resposta_inicial']}"
            )
    else:
        # Refina com base nos problemas encontrados
        problemas = avaliacao.get("problemas_encontrados", "")
        prompt = f"""Refine a resposta abaixo corrigindo os problemas identificados.

Pergunta: {state['pergunta']}
Resposta original: {state['resposta_inicial']}
Problemas identificados: {problemas}
Claims sem fonte: {avaliacao.get('afirmacoes_sem_fonte', [])}

Forneça uma resposta mais precisa, com ressalvas onde necessário e fontes claras."""

        resp = model.invoke(prompt)
        resposta_final = resp.content + f"\n\n📝 *Resposta refinada automaticamente (confiança original: {score:.0%}).*"

    return {"resposta_final": resposta_final, "confianca_final": score}

# ─── Monta o grafo de verificação ────────────────────────────────────────────
workflow_verificacao = StateGraph(EstadoVerificacao)
workflow_verificacao.add_node("buscar", buscar_web)
workflow_verificacao.add_node("gerar", gerar_resposta)
workflow_verificacao.add_node("avaliar", avaliar_resposta)
workflow_verificacao.add_node("refinar", refinar_ou_manter)

workflow_verificacao.set_entry_point("buscar")
workflow_verificacao.add_edge("buscar", "gerar")
workflow_verificacao.add_edge("gerar", "avaliar")
workflow_verificacao.add_edge("avaliar", "refinar")
workflow_verificacao.add_edge("refinar", END)

agente_verificador = workflow_verificacao.compile()

print("✅ Pipeline de auto-verificação criado (StateGraph):")
print("   buscar_web → gerar_resposta → avaliar_resposta → refinar_ou_manter")

# ===== cell_043 =====
# ─── Teste completo do pipeline de verificação ────────────────────────────────
import asyncio

perguntas_teste = [
    "Qual é a capital do Brasil e quantos habitantes ela tem?",
    "Qual será o preço do Bitcoin amanhã?",
    "O que é fotossíntese?",
]

async def executar_testes():
    for pergunta in perguntas_teste:
        print(f"\n{'='*65}")
        print(f"❓ Pergunta: {pergunta}")
        print("-" * 65)

        estado_inicial = {
            "pergunta": pergunta,
            "contexto_web": "",
            "resposta_inicial": "",
            "avaliacao": {},
            "resposta_final": "",
            "confianca_final": 0.0,
            "fontes": [],
        }

        resultado = await agente_verificador.ainvoke(estado_inicial)

        nivel = "🟢 ALTO" if resultado["confianca_final"] >= 0.8 else \
                "🟡 MÉDIO" if resultado["confianca_final"] >= 0.5 else "🔴 BAIXO"
        recom = resultado["avaliacao"].get("recomendacao", "N/A").upper()
        problemas = resultado["avaliacao"].get("problemas_encontrados", "")

        print(f"📊 Confiança: {resultado['confianca_final']:.0%}  {nivel}")
        print(f"🔍 Avaliação: {recom}")
        if problemas and problemas != "nenhum":
            print(f"⚠️  Problemas: {problemas}")
        print(f"\n🤖 Resposta:\n{resultado['resposta_final']}")

await executar_testes()

# ===== cell_045 =====
# ─── 5.4 Avaliação de Grounding: quanto da resposta vem de RAG/Tools vs LLM ──
from pydantic import BaseModel, Field
from typing import List, Literal, Tuple
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage

# ── Modelos Pydantic ──────────────────────────────────────────────────────────
class AfirmacaoAvaliada(BaseModel):
    texto: str = Field(description="A afirmação feita na resposta")
    origem: Literal["rag", "tool", "modelo"] = Field(
        description=(
            "'rag'=contexto recuperado, "
            "'tool'=resultado de ferramenta externa, "
            "'modelo'=apenas conhecimento interno do LLM"
        )
    )
    evidencia: str = Field(
        description="Trecho que suporta a afirmação, ou 'sem evidência externa'"
    )

class RelatorioGrounding(BaseModel):
    afirmacoes: List[AfirmacaoAvaliada]
    pct_rag: float = Field(description="% da resposta baseada em RAG (0-100)")
    pct_tool: float = Field(description="% baseada em tools/skills externas (0-100)")
    pct_modelo: float = Field(description="% baseada apenas no LLM (0-100)")
    nivel_confianca: Literal["alta", "media", "baixa"] = Field(
        description="alta=+70% grounded, media=30-70%, baixa=-30%"
    )
    justificativa: str = Field(description="Explicação breve do score")

# ── Extrai evidências do histórico de mensagens do agente ─────────────────────
def extrair_evidencias(mensagens) -> Tuple[str, str, str]:
    """Separa chunks RAG, resultados de tools e a resposta final do agente."""
    rag_chunks, tool_results, resposta = [], [], ""
    for msg in mensagens:
        if isinstance(msg, ToolMessage):
            nome = getattr(msg, "name", "") or ""
            if any(k in nome.lower() for k in ["rag", "conhecimento", "retriev"]):
                rag_chunks.append(msg.content)
            else:
                tool_results.append(f"[{nome}]: {msg.content}")
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            resposta = msg.content if isinstance(msg.content, str) else str(msg.content)
    return "\n---\n".join(rag_chunks), "\n".join(tool_results), resposta

# ── Avaliador de grounding ────────────────────────────────────────────────────
def avaliar_grounding(
    pergunta: str,
    resposta: str,
    contexto_rag: str = "",
    resultados_tools: str = "",
) -> RelatorioGrounding:
    avaliador = ChatAnthropic(
        model="claude-sonnet-4-6", temperature=0
    ).with_structured_output(RelatorioGrounding)

    return avaliador.invoke(
        f"""Analise a resposta e classifique cada afirmação quanto à sua origem.

PERGUNTA: {pergunta}
RESPOSTA: {resposta}
CONTEXTO RAG: {contexto_rag or "Nenhum"}
RESULTADOS DE TOOLS: {resultados_tools or "Nenhum"}

Classifique cada afirmação como:
- "rag"    → suportada pelo contexto RAG
- "tool"   → suportada por resultado de tool/busca externa
- "modelo" → apenas conhecimento interno do LLM, sem evidência externa

Calcule os percentuais e o nível de confiança."""
    )

# ── Exemplo 1: Resposta com RAG + tool (alta confiança) ──────────────────────
print("=" * 60)
print("EXEMPLO 1 — Resposta com RAG + tool")
print("=" * 60)

historico_rag_tool = [
    ToolMessage(
        content="LangGraph é uma biblioteca para agentes stateful com grafos. Suporta checkpointers e streaming.",
        name="buscar_conhecimento",
        tool_call_id="t1",
    ),
    ToolMessage(
        content="USD/BRL: 5.72 (fonte: API de câmbio em tempo real)",
        name="buscar_cotacao_async",
        tool_call_id="t2",
    ),
    AIMessage(
        content=(
            "LangGraph é uma biblioteca Python para agentes com estado persistente. "
            "Quanto ao dólar, a cotação atual é R$ 5,72."
        )
    ),
]

pergunta1 = "O que é LangGraph e qual a cotação do dólar hoje?"
ctx_rag, ctx_tools, resposta1 = extrair_evidencias(historico_rag_tool)
r1 = avaliar_grounding(pergunta1, resposta1, ctx_rag, ctx_tools)

print(f"🔵 RAG-grounded:  {r1.pct_rag:5.1f}%")
print(f"🟠 Tool-grounded: {r1.pct_tool:5.1f}%")
print(f"🔴 Modelo (LLM):  {r1.pct_modelo:5.1f}%")
print(f"✅ Confiança:     {r1.nivel_confianca.upper()}")
print(f"💬 {r1.justificativa}")
print("\nAfirmações:")
for af in r1.afirmacoes:
    icone = {"rag": "🔵", "tool": "🟠", "modelo": "🔴"}.get(af.origem, "⚪")
    print(f"  {icone} [{af.origem}] {af.texto}")

# ── Exemplo 2: Resposta apenas com conhecimento do modelo (baixa confiança) ───
print("\n" + "=" * 60)
print("EXEMPLO 2 — Resposta sem RAG nem tools")
print("=" * 60)

historico_sem_fontes = [
    AIMessage(
        content=(
            "LangGraph foi lançado em 2023 pela equipe do LangChain. "
            "Estima-se que tenha mais de 10 mil usuários no mundo."
        )
    ),
]

pergunta2 = "Quando o LangGraph foi lançado?"
_, _, resposta2 = extrair_evidencias(historico_sem_fontes)
r2 = avaliar_grounding(pergunta2, resposta2)

print(f"🔵 RAG-grounded:  {r2.pct_rag:5.1f}%")
print(f"🟠 Tool-grounded: {r2.pct_tool:5.1f}%")
print(f"🔴 Modelo (LLM):  {r2.pct_modelo:5.1f}%")
print(f"⚠️  Confiança:     {r2.nivel_confianca.upper()}")
print(f"💬 {r2.justificativa}")

# ===== cell_047 =====
# ─── 5.5 DeepEval — Framework de avaliação para RAG e LLMs ──────────────────
# Instale se necessário: pip install deepeval
import os
from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRecallMetric,
)
from deepeval.test_case import LLMTestCase
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_anthropic import ChatAnthropic

# ── Adaptador: usa Claude como modelo avaliador interno do DeepEval ──────────
class AnthropicEvaluator(DeepEvalBaseLLM):
    """Substitui o avaliador padrão (GPT-4) por Claude."""

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

claude_eval = AnthropicEvaluator()

# ── Contexto RAG recuperado (simula o que o retriever retornaria) ─────────────
contexto_recuperado = [
    "LangGraph permite criar agentes stateful com grafos direcionados.",
    "Vantagens: memória persistente via checkpointers, streaming nativo e loops.",
    "Integração com LangChain; suporta paralelismo entre nós.",
]

# ── Caso 1: resposta fiel ao contexto ────────────────────────────────────────
caso_fiel = LLMTestCase(
    input="Quais são as vantagens do LangGraph?",
    actual_output=(
        "LangGraph oferece memória persistente, streaming de tokens e controle "
        "fino sobre fluxos de trabalho, com integração nativa ao LangChain."
    ),
    expected_output="Memória persistente, streaming e controle de fluxo.",
    retrieval_context=contexto_recuperado,
)

# ── Caso 2: resposta com alucinação (não suportada pelo contexto) ─────────────
caso_alucinacao = LLMTestCase(
    input="Quais são as vantagens do LangGraph?",
    actual_output=(
        "LangGraph foi criado em 2019 pela Google e possui 50 mil estrelas no GitHub."
    ),
    expected_output="Memória persistente, streaming e controle de fluxo.",
    retrieval_context=contexto_recuperado,
)

# ── Métricas ──────────────────────────────────────────────────────────────────
#  AnswerRelevancy  — a resposta responde de fato à pergunta?
#  Faithfulness     — cada afirmação é suportada pelo contexto RAG?
#  ContextualRecall — o contexto cobre o que era esperado na resposta?
metricas = [
    AnswerRelevancyMetric(threshold=0.7, model=claude_eval, verbose_mode=False),
    FaithfulnessMetric(threshold=0.7, model=claude_eval, verbose_mode=False),
    ContextualRecallMetric(threshold=0.7, model=claude_eval, verbose_mode=False),
]

# ── Avaliação individual (sem enviar para Confident AI) ───────────────────────
print("🔍 Avaliando com DeepEval (modelo: Claude)\n")
for label, caso in [("✅ Resposta fiel", caso_fiel), ("⚠️  Com alucinação", caso_alucinacao)]:
    print(f"{label}: \"{caso.actual_output[:70]}...\"")
    for metrica in metricas:
        metrica.measure(caso)
        status = "✅" if metrica.success else "❌"
        print(f"  {status} {metrica.__class__.__name__:<25} score={metrica.score:.2f}  threshold={metrica.threshold}")
        if not metrica.success:
            print(f"     💬 {metrica.reason}")
    print()

# ── Avaliação em lote (gera relatório consolidado) ────────────────────────────
print("─" * 60)
print("📋 Avaliação em lote:")
evaluate([caso_fiel, caso_alucinacao], metricas)

# ===== cell_049 =====
from plantuml_helper import show_plantuml

show_plantuml("""
@startuml
skinparam backgroundColor #FFFFFF
skinparam activity {
  StartColor #2E7D32
  EndColor #C62828
  BackgroundColor #E1F5FE
  BorderColor #0277BD
  FontSize 13
}

start
:Agente recebe pergunta que requer dados externos;
:Cliente MCP solicita ferramentas ao servidor;
:Servidor MCP expõe tools disponiveis;

if (Tool SQL selecionada?) then (sim)
  :Servidor executa query no PostgreSQL;
  :Recebe resultados do banco;
  :Retorna JSON ao cliente MCP;
else (nao)
  :Executa outra tool de metadados;
endif

:Cliente MCP retorna contexto ao agente;
:Agente responde ao usuario com base nos dados;
stop
@enduml
""")

# ===== cell_050 =====
# Instala dependências específicas do MCP
!pip install -q mcp langchain-mcp-adapters psycopg2-binary
print("✅ Dependências MCP instaladas")

# ===== cell_051 =====
# ─── Criando o Servidor MCP PostgreSQL ───────────────────────────────────────
# Este código será salvo como um arquivo Python separado que atua como servidor MCP

mcp_server_code = '''
"""
Servidor MCP para PostgreSQL
==============================
Expõe ferramentas para consulta ao banco via protocolo MCP.
Execute: python mcp_postgres_server.py
"""
import asyncio
import os
import json
import psycopg2
import psycopg2.extras
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Configuração do banco (via variável de ambiente)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:senha@localhost:5432/meu_banco"
)

# Cria a instância do servidor MCP
server = Server("postgres-mcp-server")


def get_connection():
    """Retorna uma conexão com o banco PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


# ─── Define as ferramentas disponíveis ───────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Retorna a lista de ferramentas disponíveis neste servidor MCP."""
    return [
        types.Tool(
            name="executar_query",
            description="Executa uma query SELECT no banco PostgreSQL e retorna os resultados."
                        " APENAS queries SELECT são permitidas por segurança.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Query SQL SELECT para executar"
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de linhas a retornar (default: 100)",
                        "default": 100
                    }
                },
                "required": ["sql"]
            }
        ),
        types.Tool(
            name="listar_tabelas",
            description="Lista todas as tabelas disponíveis no schema público do banco de dados.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="descrever_tabela",
            description="Retorna a estrutura de uma tabela: colunas, tipos de dados e constraints.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabela": {
                        "type": "string",
                        "description": "Nome da tabela a ser descrita"
                    }
                },
                "required": ["tabela"]
            }
        ),
        types.Tool(
            name="contar_registros",
            description="Conta o número de registros em uma tabela, com filtro opcional.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabela": {
                        "type": "string",
                        "description": "Nome da tabela"
                    },
                    "where": {
                        "type": "string",
                        "description": "Cláusula WHERE opcional (sem a palavra WHERE)"
                    }
                },
                "required": ["tabela"]
            }
        ),
    ]


# ─── Implementa a execução de cada ferramenta ─────────────────────────────────
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Executa a ferramenta solicitada com os argumentos fornecidos."""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if name == "executar_query":
            sql = arguments["sql"].strip()
            limite = arguments.get("limite", 100)

            # Segurança: apenas SELECT
            if not sql.upper().startswith("SELECT"):
                return [types.TextContent(
                    type="text",
                    text="⚠️ Apenas queries SELECT são permitidas por segurança."
                )]

            cur.execute(sql)
            rows = cur.fetchmany(limite)
            resultado = [dict(row) for row in rows]
            return [types.TextContent(
                type="text",
                text=json.dumps(resultado, ensure_ascii=False, default=str, indent=2)
            )]

        elif name == "listar_tabelas":
            cur.execute("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_name = t.table_name) as num_colunas
                FROM information_schema.tables t
                WHERE table_schema = \'public\'
                ORDER BY table_name
            """)
            tabelas = [dict(row) for row in cur.fetchall()]
            return [types.TextContent(
                type="text",
                text=json.dumps(tabelas, ensure_ascii=False, indent=2)
            )]

        elif name == "descrever_tabela":
            tabela = arguments["tabela"]
            cur.execute("""
                SELECT 
                    column_name as coluna,
                    data_type as tipo,
                    character_maximum_length as tamanho_max,
                    is_nullable as permite_nulo,
                    column_default as valor_padrao
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = \'public\'
                ORDER BY ordinal_position
            """, (tabela,))
            colunas = [dict(row) for row in cur.fetchall()]
            if not colunas:
                return [types.TextContent(type="text", text=f"Tabela \'{tabela}\' não encontrada.")]
            return [types.TextContent(
                type="text",
                text=json.dumps({"tabela": tabela, "colunas": colunas}, 
                               ensure_ascii=False, default=str, indent=2)
            )]

        elif name == "contar_registros":
            tabela = arguments["tabela"]
            where = arguments.get("where", "")
            sql = f"SELECT COUNT(*) as total FROM {tabela}"
            if where:
                sql += f" WHERE {where}"
            cur.execute(sql)
            total = cur.fetchone()["total"]
            return [types.TextContent(
                type="text",
                text=f"Total de registros em \'{tabela}\'{\' (com filtro)\' if where else \'\': {total}"
            )]

        conn.close()

    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Erro: {str(e)}")]


# ─── Ponto de entrada do servidor ─────────────────────────────────────────────
async def main():
    print(f"🚀 Servidor MCP PostgreSQL iniciado", flush=True)
    print(f"   Banco: {DATABASE_URL.split(\'@\')[-1] if \'@\' in DATABASE_URL else DATABASE_URL}", flush=True)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
'''

# Salva o arquivo do servidor MCP
with open("mcp_postgres_server.py", "w", encoding="utf-8") as f:
    f.write(mcp_server_code)

print("✅ Servidor MCP salvo em: mcp_postgres_server.py")
print("\n📋 Para testar manualmente:")
print("   DATABASE_URL=postgresql://user:senha@localhost:5432/banco python mcp_postgres_server.py")

# ===== cell_052 =====
# ─── Simulação do banco para testes (sem precisar de PostgreSQL real) ─────────
# Este código cria um servidor MCP mock para demonstração

mcp_mock_code = '''
"""
Servidor MCP Mock (para testes sem PostgreSQL)
Simula um banco de dados com dados de exemplo.
"""
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

server = Server("postgres-mock-server")

# Dados simulados
MOCK_DATA = {
    "clientes": [
        {"id": 1, "nome": "Ana Silva", "email": "ana@exemplo.com", "cidade": "São Paulo", "saldo": 15000.00},
        {"id": 2, "nome": "Bruno Costa", "email": "bruno@exemplo.com", "cidade": "Rio de Janeiro", "saldo": 8500.50},
        {"id": 3, "nome": "Carla Mendes", "email": "carla@exemplo.com", "cidade": "Curitiba", "saldo": 22000.00},
        {"id": 4, "nome": "Diego Santos", "email": "diego@exemplo.com", "cidade": "São Paulo", "saldo": 5200.75},
    ],
    "produtos": [
        {"id": 1, "nome": "Notebook Pro", "categoria": "Eletrônicos", "preco": 4500.00, "estoque": 15},
        {"id": 2, "nome": "Smartphone X", "categoria": "Eletrônicos", "preco": 2800.00, "estoque": 42},
        {"id": 3, "nome": "Mesa Gamer", "categoria": "Móveis", "preco": 1200.00, "estoque": 8},
        {"id": 4, "nome": "Cadeira Ergonômica", "categoria": "Móveis", "preco": 950.00, "estoque": 20},
    ],
    "pedidos": [
        {"id": 1, "cliente_id": 1, "produto_id": 2, "quantidade": 1, "total": 2800.00, "status": "entregue"},
        {"id": 2, "cliente_id": 2, "produto_id": 1, "quantidade": 1, "total": 4500.00, "status": "processando"},
        {"id": 3, "cliente_id": 1, "produto_id": 4, "quantidade": 2, "total": 1900.00, "status": "entregue"},
        {"id": 4, "cliente_id": 3, "produto_id": 3, "quantidade": 1, "total": 1200.00, "status": "enviado"},
    ]
}

SCHEMAS = {
    "clientes": [
        {"coluna": "id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "nome", "tipo": "varchar", "permite_nulo": "NO"},
        {"coluna": "email", "tipo": "varchar", "permite_nulo": "NO"},
        {"coluna": "cidade", "tipo": "varchar", "permite_nulo": "YES"},
        {"coluna": "saldo", "tipo": "numeric", "permite_nulo": "YES"},
    ],
    "produtos": [
        {"coluna": "id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "nome", "tipo": "varchar", "permite_nulo": "NO"},
        {"coluna": "categoria", "tipo": "varchar", "permite_nulo": "YES"},
        {"coluna": "preco", "tipo": "numeric", "permite_nulo": "NO"},
        {"coluna": "estoque", "tipo": "integer", "permite_nulo": "YES"},
    ],
    "pedidos": [
        {"coluna": "id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "cliente_id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "produto_id", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "quantidade", "tipo": "integer", "permite_nulo": "NO"},
        {"coluna": "total", "tipo": "numeric", "permite_nulo": "NO"},
        {"coluna": "status", "tipo": "varchar", "permite_nulo": "YES"},
    ]
}

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="executar_query",
            description="Executa uma query no banco mock (suporta filtros simples por coluna=valor)",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabela": {"type": "string", "description": "Nome da tabela"},
                    "filtro": {"type": "object", "description": "Filtros chave:valor (opcional)"}
                },
                "required": ["tabela"]
            }
        ),
        types.Tool(
            name="listar_tabelas",
            description="Lista todas as tabelas disponíveis no banco mock.",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="descrever_tabela",
            description="Retorna o schema de uma tabela.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabela": {"type": "string", "description": "Nome da tabela"}
                },
                "required": ["tabela"]
            }
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "listar_tabelas":
        tabelas = [{"table_name": t, "num_colunas": len(c)} for t, c in SCHEMAS.items()]
        return [types.TextContent(type="text", text=json.dumps(tabelas, ensure_ascii=False, indent=2))]

    elif name == "descrever_tabela":
        tabela = arguments["tabela"]
        schema = SCHEMAS.get(tabela)
        if not schema:
            return [types.TextContent(type="text", text=f"Tabela \'{tabela}\' não encontrada. Tabelas: {list(SCHEMAS.keys())}")]
        return [types.TextContent(
            type="text",
            text=json.dumps({"tabela": tabela, "colunas": schema}, ensure_ascii=False, indent=2)
        )]

    elif name == "executar_query":
        tabela = arguments["tabela"]
        filtro = arguments.get("filtro", {})
        dados = MOCK_DATA.get(tabela, [])
        if filtro:
            dados = [row for row in dados 
                    if all(str(row.get(k)) == str(v) for k, v in filtro.items())]
        return [types.TextContent(
            type="text",
            text=json.dumps(dados, ensure_ascii=False, default=str, indent=2)
        )]

    return [types.TextContent(type="text", text=f"Ferramenta desconhecida: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
'''

with open("mcp_mock_server.py", "w", encoding="utf-8") as f:
    f.write(mcp_mock_code)

print("✅ Servidor MCP Mock criado: mcp_mock_server.py")
print("   Contém tabelas simuladas: clientes, produtos, pedidos")

# ===== cell_053 =====
import asyncio
import io
import os
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic

# Workaround: Jupyter substitui sys.stderr por stream virtual sem fileno() real.
# O MCP precisa de um fd válido ao criar o subprocesso stdio.
try:
    sys.stderr.fileno()
except io.UnsupportedOperation:
    _devnull = open(os.devnull, "w")
    sys.stderr.fileno = _devnull.fileno
    sys.stdout.fileno = _devnull.fileno

# Servidor mock (sem PostgreSQL):
server_config = {
    "postgres_mock": {
        "command": "python",
        "args": ["mcp_mock_server.py"],
        "transport": "stdio",
        "env": dict(os.environ)
    }
}

# Para usar o servidor real com PostgreSQL, substitua server_config por:
# server_config = {
#     "postgres": {
#         "command": "python",
#         "args": ["mcp_postgres_server.py"],
#         "transport": "stdio",
#         "env": {**dict(os.environ), "DATABASE_URL": os.environ.get("DATABASE_URL", "")}
#     }
# }

async def criar_e_usar_agente_mcp():
    client = MultiServerMCPClient(server_config)
    mcp_tools = await client.get_tools()
    print(f"🔧 Ferramentas MCP disponíveis: {[t.name for t in mcp_tools]}")

    model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    agente_mcp = create_react_agent(model, mcp_tools, checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "mcp-demo-1"}}

    for pergunta in [
        "Quais tabelas existem no banco de dados?",
        "Liste os clientes de São Paulo e me diga o saldo médio deles",
        "E os pedidos desses clientes que mencionei? Quais produtos eles compraram?",
    ]:
        print("\n" + "=" * 60)
        print(f"👤 {pergunta}")
        resultado = await agente_mcp.ainvoke(
            {"messages": [{"role": "user", "content": pergunta}]},
            config=config
        )
        print(f"🤖 {resultado['messages'][-1].content}")

await criar_e_usar_agente_mcp()
# Em script Python normal: asyncio.run(criar_e_usar_agente_mcp())

# ===== cell_054 =====
# ─── Exemplo avançado: Agente com múltiplos servidores MCP ───────────────────
async def agente_multi_mcp():
    """Demonstra conexão a múltiplos servidores MCP simultaneamente."""

    config_multi = {
        "database": {
            "command": "python",
            "args": ["mcp_mock_server.py"],
            "transport": "stdio",
            "env": dict(os.environ)
        },
        # Outros servidores MCP podem ser adicionados aqui:
        # "filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]},
        # "web_search": {"url": "http://localhost:8000/mcp", "transport": "sse"}
    }

    # langchain-mcp-adapters >= 0.1.0: não usar como context manager
    client = MultiServerMCPClient(config_multi)
    all_tools = await client.get_tools()
    print(f"🔧 Total de ferramentas de todos os servidores: {len(all_tools)}")
    for tool in all_tools:
        print(f"   • {tool.name}: {tool.description[:60]}...")

    # Combina ferramentas MCP com skills locais
    skills_locais = [calculadora, skill_analise, buscar_conhecimento]
    todas_ferramentas = all_tools + skills_locais

    model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    agente_final = create_react_agent(model, todas_ferramentas, checkpointer=MemorySaver())

    print(f"\n✅ Agente com {len(todas_ferramentas)} ferramentas (MCP + locais)")

    config = {"configurable": {"thread_id": "multi-mcp-1"}}
    resultado = await agente_final.ainvoke(
        {"messages": [{"role": "user", "content": (
            "Preciso de um relatório:\n"
            "1) Liste os produtos em estoque com preço acima de R$1000\n"
            "2) Calcule o valor total em estoque desses produtos\n"
            "3) Me explique o que é RAG (busque na base de conhecimento)"
        )}]},
        config=config
    )
    print(f"\n🤖 Relatório:\n{resultado['messages'][-1].content}")

await agente_multi_mcp()

# ===== cell_056 =====
# ─── 7.1 Pipeline ML: geração de dados, clustering e perfis ──────────────────
# Em PRODUÇÃO os nomes dos segmentos, prompts e personas vêm do
# Athena/Glue Data Catalog — não de regras hard-coded.
# Aqui simulamos o Athena com um DataFrame local para fins didáticos.
import warnings
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", message=".*create_react_agent.*")

np.random.seed(42)
N = 600

# Dados sintéticos de clientes de banco
df_clientes = pd.DataFrame({
    "cliente_id":     [f"C{i:05d}" for i in range(N)],
    "idade":          np.random.randint(18, 75, N),
    "renda_mensal":   np.random.exponential(5000, N).clip(800, 50_000),
    "saldo_medio":    np.random.exponential(12_000, N).clip(0, 200_000),
    "transacoes_mes": np.random.poisson(18, N),
    "score_credito":  np.random.normal(650, 120, N).clip(300, 1_000),
    "num_produtos":   np.random.randint(1, 8, N),
    "inadimplente":   np.random.choice([0, 1], N, p=[0.87, 0.13]),
    "canal_digital":  np.random.choice([0, 1], N, p=[0.35, 0.65]),
})

# ── Normalização e clustering K-Means ─────────────────────────────────────────
FEATURES = ["idade", "renda_mensal", "saldo_medio", "transacoes_mes",
            "score_credito", "num_produtos"]

scaler_clientes = StandardScaler()
X = scaler_clientes.fit_transform(df_clientes[FEATURES])

kmeans_clientes = KMeans(n_clusters=4, random_state=42, n_init=10)
df_clientes["cluster"] = kmeans_clientes.fit_predict(X)

# ── Perfis estatísticos por cluster (sem nome ainda) ──────────────────────────
# O K-Means retorna clusters 0-3 sem semântica de negócio.
# Os NOMES vêm do Athena/Glue — ver _enriquecer_perfis_nb() abaixo.
perfis_clientes = (
    df_clientes.groupby("cluster")
    .agg(
        n=("cluster", "size"),
        idade_media=("idade", "mean"),
        renda_media=("renda_mensal", "mean"),
        saldo_medio_=("saldo_medio", "mean"),
        score_medio=("score_credito", "mean"),
        produtos_medio=("num_produtos", "mean"),
        inadimplencia=("inadimplente", "mean"),
        digital=("canal_digital", "mean"),
    )
    .round(1)
)

# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK: heurística para nomear segmentos (usado quando Athena indisponível)
# Em produção este bloco raramente é acionado — só em caso de falha do Athena.
# ─────────────────────────────────────────────────────────────────────────────
def nomear_segmento(row: pd.Series) -> str:
    """Fallback: nomeia o cluster a partir das suas estatísticas."""
    if row["renda_media"] > 10_000 and row["score_medio"] > 700:
        return "Premium Conservador"
    elif row["idade_media"] < 35 and row["digital"] > 0.65:
        return "Jovem Digital"
    elif row["inadimplencia"] > 0.18:
        return "Alto Risco"
    return "Massa Estável"

# ── Fallback: prompts, produtos e personas por segmento ───────────────────────
# Estes dicts são usados APENAS como fallback quando o Athena não fornece o valor.
# Em produção, os dados vêm da tabela: {ATHENA_DATABASE}.{ATHENA_TABLE_SEGMENTOS}
PROMPTS_SEGMENTO_FB = {
    "Premium Conservador": (
        "Você é um gerente de relacionamento exclusivo do banco para clientes Premium. "
        "Esses clientes têm alta renda, excelente histórico de crédito e preferem "
        "produtos de investimento de baixo risco e atendimento personalizado. "
        "Seja formal, preciso e ofereça soluções sofisticadas com dados concretos."
    ),
    "Jovem Digital": (
        "Você atende clientes jovens e altamente digitais do banco. "
        "Eles preferem comunicação direta e descomplicada, produtos via app, "
        "cashback e aprovação de crédito instantânea. "
        "Use linguagem leve e destaque praticidade e benefícios digitais."
    ),
    "Alto Risco": (
        "Você atende clientes com histórico de inadimplência. "
        "Foque em renegociação de dívidas, educação financeira e produtos de "
        "baixo limite inicial. Seja empático, não faça julgamentos e apresente "
        "caminhos concretos de regularização financeira."
    ),
    "Massa Estável": (
        "Você atende o público geral e estável do banco. "
        "Esses clientes valorizam segurança, previsibilidade e bom custo-benefício. "
        "Foque em fidelização, cross-sell gradual e proteção patrimonial simples."
    ),
}

PRODUTOS_POR_SEGMENTO_FB = {
    "Premium Conservador": (
        "Tesouro Direto IPCA+ e fundos de renda fixa de longo prazo. "
        "Previdência privada PGBL com benefício fiscal. "
        "Cartão Platinum com sala VIP e seguro viagem. "
        "Consultoria de investimentos com gerente dedicado. "
        "Seguro de vida com cobertura ampla."
    ),
    "Jovem Digital": (
        "Cartão de crédito com cashback de 2% sem anuidade. "
        "Conta digital com rendimento automático de 100% do CDI. "
        "Crédito pessoal com aprovação em minutos pelo app. "
        "Investimentos a partir de R$ 1 via plataforma digital. "
        "Portabilidade de salário com bônus de boas-vindas."
    ),
    "Alto Risco": (
        "Programa de renegociação de dívidas com até 90% de desconto nos juros. "
        "Cartão pré-pago sem consulta ao SPC/Serasa. "
        "Microcrédito inicial de R$ 500 com limite crescente. "
        "Curso gratuito de educação financeira no app. "
        "Débito automático de contas para evitar novas inadimplências."
    ),
    "Massa Estável": (
        "Conta corrente com pacote de tarifas simplificado. "
        "Cartão de crédito com limite adequado ao perfil de renda. "
        "Seguro residencial com cobertura básica e parcelas acessíveis. "
        "Consórcio de imóveis e veículos sem juros. "
        "Previdência privada VGBL com aporte mínimo."
    ),
}

PERSONAS_SEGMENTO_FB = {
    "Premium Conservador": {
        "nome": "Carlos",
        "ocupacao": "gerente de empresa, 52 anos",
        "canal": "prefiro o atendimento exclusivo com meu gerente de relacionamento",
        "contexto": (
            "Planejei minha aposentadoria com cuidado e tenho patrimônio consolidado. "
            "Priorizo segurança e rentabilidade real acima da inflação."
        ),
    },
    "Jovem Digital": {
        "nome": "Júlia",
        "ocupacao": "designer freelancer, 26 anos",
        "canal": "faço tudo pelo app — nunca fui a uma agência",
        "contexto": (
            "Gosto de produtos sem burocracia. "
            "Cashback e aprovação instantânea são diferenciais importantes para mim."
        ),
    },
    "Alto Risco": {
        "nome": "Roberto",
        "ocupacao": "motorista autônomo, 43 anos",
        "canal": "uso o app para o dia a dia mas prefiro a agência para assuntos sérios",
        "contexto": (
            "Passei por um período difícil e acumulei dívidas. "
            "Preciso de orientação concreta para regularizar minha situação."
        ),
    },
    "Massa Estável": {
        "nome": "Ana",
        "ocupacao": "funcionária pública há 12 anos, 38 anos",
        "canal": "uso o internet banking mas prefiro a agência para assuntos importantes",
        "contexto": (
            "Valorizo estabilidade e produtos sem surpresas. "
            "Penso no futuro da minha família e em proteger o que já conquistei."
        ),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PRODUÇÃO: carregar_segmentos_athena()
#   SELECT cluster_id, segmento_nome, prompt_segmento, produtos,
#          persona_nome, persona_ocupacao, persona_canal, persona_contexto
#   FROM {ATHENA_DATABASE}.{ATHENA_TABLE_SEGMENTOS}
#   ORDER BY cluster_id
#
# NOTEBOOK: simulamos com um DataFrame local. Analistas de negócio
# preenchem esta tabela no Glue — podem renomear ou criar novos segmentos
# sem nenhuma alteração no código Python.
# ─────────────────────────────────────────────────────────────────────────────

# Etapa 1: nomes provisórios via heurística (apenas para construir o mock)
_perfis_temp = perfis_clientes.copy()
_perfis_temp["segmento"] = _perfis_temp.apply(nomear_segmento, axis=1)

# Etapa 2: DataFrame que simula a tabela no Athena/Glue Catalog
seg_df_athena = pd.DataFrame([
    {
        "cluster_id":      int(cid),
        "segmento_nome":   row["segmento"],
        "prompt_segmento": PROMPTS_SEGMENTO_FB.get(row["segmento"], ""),
        "produtos":        PRODUTOS_POR_SEGMENTO_FB.get(row["segmento"], ""),
        "persona_nome":     PERSONAS_SEGMENTO_FB.get(row["segmento"], {}).get("nome", ""),
        "persona_ocupacao": PERSONAS_SEGMENTO_FB.get(row["segmento"], {}).get("ocupacao", ""),
        "persona_canal":    PERSONAS_SEGMENTO_FB.get(row["segmento"], {}).get("canal", ""),
        "persona_contexto": PERSONAS_SEGMENTO_FB.get(row["segmento"], {}).get("contexto", ""),
    }
    for cid, row in _perfis_temp.iterrows()
])

print("Tabela Athena/Glue simulada (em producao: carregar_segmentos_athena()):")
print(seg_df_athena[["cluster_id", "segmento_nome", "persona_nome"]].to_string(index=False))
print()

# ── _enriquecer_perfis_nb: mescla estatísticas K-Means + metadados do Athena ──
def _enriquecer_perfis_nb(perfis: pd.DataFrame, seg_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Enriquece o DataFrame de perfis com metadados do Athena/Glue.

    Fluxo de prioridade para cada atributo:
      1. Athena/Glue Catalog  <- fonte de verdade (producao)
      2. Heuristica local     <- fallback quando Athena nao disponivel

    Em producao: seg_df = carregar_segmentos_athena()
    No notebook:  seg_df = seg_df_athena (simulado)
    """
    perfis = perfis.copy()
    seg_idx = (
        seg_df.set_index("cluster_id")
        if seg_df is not None and not seg_df.empty
        else None
    )

    for cid in perfis.index:
        athena = (
            seg_idx.loc[cid]
            if seg_idx is not None and cid in seg_idx.index
            else pd.Series(dtype=object)
        )

        # ── Nome do segmento ───────────────────────────────────────────────────
        segmento = str(athena.get("segmento_nome", "")).strip()
        if not segmento:
            segmento = nomear_segmento(perfis.loc[cid])   # fallback heuristico
        perfis.loc[cid, "segmento"] = segmento

        # ── Prompt do agente de segmento ──────────────────────────────────────
        prompt = str(athena.get("prompt_segmento", "")).strip()
        perfis.loc[cid, "prompt_segmento"] = prompt or PROMPTS_SEGMENTO_FB.get(segmento, "")

        # ── Produtos recomendados ─────────────────────────────────────────────
        produtos = str(athena.get("produtos", "")).strip()
        perfis.loc[cid, "produtos"] = produtos or PRODUTOS_POR_SEGMENTO_FB.get(segmento, "")

        # ── Persona (arquétipo do cluster) ────────────────────────────────────
        p_fb = PERSONAS_SEGMENTO_FB.get(segmento, {})
        for col, key in [
            ("persona_nome",     "nome"),
            ("persona_ocupacao", "ocupacao"),
            ("persona_canal",    "canal"),
            ("persona_contexto", "contexto"),
        ]:
            val = str(athena.get(col, "")).strip()
            perfis.loc[cid, col] = val or p_fb.get(key, "")

    return perfis


# ── Enriquecer perfis ──────────────────────────────────────────────────────────
# Em producao:
#   seg_df = carregar_segmentos_athena()
#   perfis_clientes = _enriquecer_perfis_nb(perfis_clientes, seg_df)
#
# No notebook (Athena simulado):
perfis_clientes = _enriquecer_perfis_nb(perfis_clientes, seg_df_athena)

# ── Exibe resumo ───────────────────────────────────────────────────────────────
print("SEGMENTOS IDENTIFICADOS PELO K-MEANS")
print("(nomes, prompts e personas carregados do Athena/Glue Catalog)")
print("=" * 75)
print(
    perfis_clientes[
        ["segmento", "n", "idade_media", "renda_media",
         "saldo_medio_", "score_medio", "inadimplencia"]
    ]
    .rename(columns={
        "segmento": "Segmento", "n": "Clientes",
        "idade_media": "Idade", "renda_media": "Renda (R$)",
        "saldo_medio_": "Saldo (R$)", "score_medio": "Score",
        "inadimplencia": "Inadimp.%",
    })
    .to_string()
)

print("\nDistribuicao:")
for cid, row in perfis_clientes.iterrows():
    bar = "#" * int(row["n"] / 10)
    print(f"  Cluster {cid} | {row['segmento']:<22} | {int(row['n']):>3} clientes {bar}")

# ===== cell_058 =====
# ─── 7.1b Big Five: inferência e enriquecimento dos perfis ───────────────────
# Em produção: scores Big5 calculados pelo job SageMaker e salvos no Glue Catalog.
# No notebook: inferência direta das features financeiras como proxy.

OCEAN_TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]


def inferir_big5_cluster(perfil: pd.Series) -> dict:
    """
    Infere Big Five a partir do perfil ESTATÍSTICO do cluster.
    Usado para PERSONAS (arquétipos do grupo).

    Mapeamento:
      openness          ← canal_digital + variedade de produtos
      conscientiousness ← score_credito + ausencia_inadimplencia
      extraversion      ← canal_digital + produtos_medio
      agreeableness     ← (1 - inadimplencia) + score parcial
      neuroticism       ← inadimplencia + score baixo
    """
    digital = float(perfil["digital"])
    score   = float(perfil["score_medio"])
    inadimp = float(perfil["inadimplencia"])
    prod    = min(float(perfil["produtos_medio"]) / 8, 1.0)

    return {
        "openness":          round(min(digital * 0.6 + prod * 0.4,               1.0), 2),
        "conscientiousness": round(min(score / 1000 * 0.7 + (1 - inadimp) * 0.3, 1.0), 2),
        "extraversion":      round(min(digital * 0.5 + prod * 0.5,               1.0), 2),
        "agreeableness":     round(min((1 - inadimp) * 0.6 + score / 2000 * 0.4, 1.0), 2),
        "neuroticism":       round(min(inadimp * 0.6 + max(0, (500 - score) / 500) * 0.4, 1.0), 2),
    }


def inferir_big5_cliente(row: pd.Series) -> dict:
    """
    Infere Big Five a partir dos dados BRUTOS de um cliente individual.
    Usado para DIGITAL TWINS (sem dependência de clustering).
    """
    digital = float(row["canal_digital"])
    score   = float(row["score_credito"])
    inadimp = float(row["inadimplente"])
    txn     = min(float(row["transacoes_mes"]) / 30, 1.0)
    prod    = min(float(row["num_produtos"]) / 8, 1.0)

    return {
        "openness":          round(min(digital * 0.6 + txn * 0.4,                 1.0), 2),
        "conscientiousness": round(min(score / 1000 * 0.7 + (1 - inadimp) * 0.3,  1.0), 2),
        "extraversion":      round(min(digital * 0.4 + txn * 0.4 + prod * 0.2,    1.0), 2),
        "agreeableness":     round(min((1 - inadimp) * 0.6 + score / 2000 * 0.4,  1.0), 2),
        "neuroticism":       round(min(inadimp * 0.6 + max(0, (500 - score) / 500) * 0.4, 1.0), 2),
    }


def big5_para_estilo(big5: dict) -> str:
    """
    Converte scores OCEAN em descrição de estilo comportamental para incluir nos prompts.
    Apenas traços com score >0.65 ou <0.35 são mencionados (polarizados).
    """
    partes = []

    if big5["openness"] > 0.65:
        partes.append("aberto a produtos inovadores e novidades financeiras")
    elif big5["openness"] < 0.35:
        partes.append("prefere soluções tradicionais e conhecidas, evita o desconhecido")

    if big5["conscientiousness"] > 0.65:
        partes.append("organizado, analisa todos os detalhes antes de decidir")
    elif big5["conscientiousness"] < 0.35:
        partes.append("toma decisões rápidas e prefere processos simples e ágeis")

    if big5["extraversion"] > 0.65:
        partes.append("engajado e proativo nos canais do banco")
    elif big5["extraversion"] < 0.35:
        partes.append("reservado, prefere autoatendimento e pouca interação")

    if big5["agreeableness"] > 0.65:
        partes.append("cooperativo e receptivo a propostas e acordos")

    if big5["neuroticism"] > 0.5:
        partes.append("ansioso com incertezas financeiras, valoriza garantias e previsibilidade")
    elif big5["neuroticism"] < 0.2:
        partes.append("emocionalmente estável, tolerante a riscos calculados")

    return "; ".join(partes) if partes else "perfil equilibrado sem traços dominantes"


# ── Adiciona colunas Big Five a perfis_clientes ────────────────────────────────
for cid, row in perfis_clientes.iterrows():
    b5 = inferir_big5_cluster(row)
    for trait, val in b5.items():
        perfis_clientes.loc[cid, f"big5_{trait}"] = val

# ── Exibe perfis com Big Five ──────────────────────────────────────────────────
b5_cols = [f"big5_{t}" for t in OCEAN_TRAITS]
print("PERFIS ENRIQUECIDOS COM BIG FIVE (OCEAN)")
print("=" * 70)
print(perfis_clientes[["segmento"] + b5_cols].to_string())
print()
print("Estilos comportamentais derivados:")
print("-" * 70)
for cid, row in perfis_clientes.iterrows():
    b5 = {t: float(row[f"big5_{t}"]) for t in OCEAN_TRAITS}
    estilo = big5_para_estilo(b5)
    print(f"  Cluster {cid} | {row['segmento']:<22}: {estilo}")

# ===== cell_059 =====
# ─── 7.2 RAG por segmento + agente especializado ─────────────────────────────
# Prompts e produtos são lidos de perfis_clientes["prompt_segmento"] e
# perfis_clientes["produtos"] — valores que vieram do Athena/Glue na célula 7.1.
# Não há dicionários hard-coded aqui: qualquer nome de segmento do Glue funciona.
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# ── Documentos de conhecimento gerados a partir dos perfis enriquecidos ───────
def _gerar_docs_cluster(cluster_id: int, perfil: pd.Series) -> list[Document]:
    """
    Cria 3 documentos por cluster.
    Todo o conteúdo textual (prompt, produtos) vem de perfil — populado
    com dados do Athena/Glue Catalog na etapa anterior (célula 7.1).
    Nenhum dicionário local é consultado aqui.
    """
    segmento     = str(perfil["segmento"])
    renda        = float(perfil["renda_media"])
    score        = float(perfil["score_medio"])
    n_clientes   = int(perfil["n"])
    inadimp      = float(perfil["inadimplencia"])
    produtos_txt = str(perfil.get("produtos", ""))

    return [
        Document(
            page_content=(
                f"PERFIL DO SEGMENTO: {segmento}\n"
                f"- Clientes: {n_clientes}\n"
                f"- Renda média: R$ {renda:,.0f}/mês\n"
                f"- Score médio: {score:.0f}\n"
                f"- Inadimplência: {inadimp:.1%}\n"
                f"- Idade média: {float(perfil['idade_media']):.0f} anos\n"
                f"- Canal digital: {float(perfil['digital']):.0%}"
            ),
            metadata={"cluster_id": cluster_id, "tipo": "perfil", "segmento": segmento},
        ),
        Document(
            page_content=f"PRODUTOS RECOMENDADOS PARA O SEGMENTO {segmento}:\n{produtos_txt}",
            metadata={"cluster_id": cluster_id, "tipo": "produtos", "segmento": segmento},
        ),
        Document(
            page_content=(
                f"ESTRATÉGIA DE ATENDIMENTO — {segmento}\n"
                f"Score {score:.0f}: "
                f"{'excelente crédito — ofereça produtos premium' if score > 750 else 'bom crédito — cross-sell gradual' if score > 600 else 'crédito limitado — foco em recuperação'}.\n"
                f"Renda R$ {renda:,.0f}: "
                f"{'alta — produtos de investimento e proteção' if renda > 10_000 else 'média — produtos acessíveis' if renda > 3_000 else 'baixa — microcrédito e educação financeira'}."
            ),
            metadata={"cluster_id": cluster_id, "tipo": "estrategia", "segmento": segmento},
        ),
    ]


# ── Ferramenta: consultar regulamentos do banco ───────────────────────────────
@tool
def consultar_regulamentos(produto: str) -> str:
    """Consulta regras e limitações regulatórias para um produto bancário."""
    regulamentos = {
        "investimento": "CVM regula fundos. Clientes PF: limite de R$ 1M sem declaração de IR. Prazo mínimo: 30 dias.",
        "cartao":       "Banco Central: taxa máxima de rotativo 8% a.m. Limite mínimo: 20% da renda.",
        "credito":      "CDC: taxa máxima de 12% a.a. para crédito consignado. Prazo máximo: 84 meses.",
        "previdencia":  "SUSEP regula. PGBL: deduz até 12% da renda bruta no IR. VGBL: sem dedução.",
        "renegociacao": "Lei 14.181/2021 (Superendividamento): banco deve oferecer renegociação em 60 dias.",
    }
    for k, v in regulamentos.items():
        if k.lower() in produto.lower():
            return v
    return f"Consulte o gerente para detalhes regulatórios sobre '{produto}'."


# ── Embeddings e splitter ─────────────────────────────────────────────────────
embeddings   = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
splitter     = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
checkpointer = MemorySaver()


# ── Cria um agente por cluster ────────────────────────────────────────────────
def _criar_agente_cluster(cluster_id: int, perfil: pd.Series) -> dict:
    """
    Cria agente RAG especializado para um cluster.

    O prompt do sistema é lido de perfil['prompt_segmento'], que foi
    carregado do Athena/Glue Catalog — não de um dicionário hard-coded.
    Qualquer nome ou prompt definido pelos analistas no Glue é respeitado.
    """
    segmento       = str(perfil["segmento"])
    prompt_sistema = str(perfil.get("prompt_segmento", ""))

    docs     = _gerar_docs_cluster(cluster_id, perfil)
    chunks   = splitter.split_documents(docs)
    vs       = FAISS.from_documents(chunks, embeddings)
    retriever = vs.as_retriever(search_kwargs={"k": 3})

    @tool
    def buscar_perfil_segmento(query: str) -> str:
        """Busca informações sobre o perfil e produtos do segmento no knowledge base."""
        docs_ret = retriever.invoke(query)
        return "\n---\n".join(d.page_content for d in docs_ret)

    agente = create_react_agent(
        model=ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0),
        tools=[buscar_perfil_segmento, consultar_regulamentos],
        checkpointer=checkpointer,
        prompt=prompt_sistema,
    )
    return {"segmento": segmento, "agente": agente, "vector_store": vs}


# ── Instancia agentes para todos os clusters ──────────────────────────────────
print("Criando agentes por segmento...")
print("(prompts e produtos lidos do Athena/Glue via perfis_clientes)\n")

agentes_clientes = {}
for cluster_id, perfil in perfis_clientes.iterrows():
    agentes_clientes[cluster_id] = _criar_agente_cluster(cluster_id, perfil)
    print(f"  ok Cluster {cluster_id}: {perfil['segmento']}")

print(f"\nAgentes prontos: {list(agentes_clientes.keys())}")

# ===== cell_060 =====
# ─── 7.3 Demo: roteamento e consulta ao agente correto ───────────────────────
def classificar_cliente(dados: dict) -> int:
    """Classifica um novo cliente no segmento correto usando o modelo treinado."""
    X = scaler_clientes.transform([[
        dados["idade"],
        dados["renda_mensal"],
        dados["saldo_medio"],
        dados["transacoes_mes"],
        dados["score_credito"],
        dados["num_produtos"],
    ]])
    return int(kmeans_clientes.predict(X)[0])

def consultar_agente(cliente_id: str, dados: dict, pergunta: str) -> dict:
    """Roteia o cliente ao agente do segmento e retorna a resposta."""
    cluster_id = classificar_cliente(dados)
    info = agentes_clientes[cluster_id]
    config = {"configurable": {"thread_id": f"cliente-{cliente_id}"}}
    resultado = info["agente"].invoke(
        {"messages": [{"role": "user", "content": pergunta}]},
        config=config,
    )
    return {
        "cliente_id": cliente_id,
        "cluster_id": cluster_id,
        "segmento": info["segmento"],
        "resposta": resultado["messages"][-1].content,
    }

# ── Clientes de teste ─────────────────────────────────────────────────────────
clientes_teste = [
    {
        "id": "C001",
        "dados": {"idade": 54, "renda_mensal": 22000, "saldo_medio": 95000,
                  "transacoes_mes": 10, "score_credito": 840, "num_produtos": 6},
        "label": "Cliente rico, conservador",
    },
    {
        "id": "C002",
        "dados": {"idade": 23, "renda_mensal": 2500, "saldo_medio": 800,
                  "transacoes_mes": 40, "score_credito": 580, "num_produtos": 2},
        "label": "Jovem digital, baixo saldo",
    },
    {
        "id": "C003",
        "dados": {"idade": 41, "renda_mensal": 3100, "saldo_medio": 300,
                  "transacoes_mes": 6, "score_credito": 360, "num_produtos": 1},
        "label": "Inadimplente, perfil de risco",
    },
    {
        "id": "C004",
        "dados": {"idade": 45, "renda_mensal": 5500, "saldo_medio": 12000,
                  "transacoes_mes": 18, "score_credito": 680, "num_produtos": 3},
        "label": "Massa estável, produto típico",
    },
]

pergunta = "Quais produtos você recomenda para melhorar minha situação financeira?"

for c in clientes_teste:
    r = consultar_agente(c["id"], c["dados"], pergunta)
    print(f"\n{'='*65}")
    print(f"Cliente {r['cliente_id']} ({c['label']})")
    print(f"Segmento: {r['segmento']}  |  Cluster: {r['cluster_id']}")
    print(f"{'='*65}")
    print(r["resposta"])

# ===== cell_062 =====
# ─── 7.4 Digital Twins de Clientes ───────────────────────────────────────────
# O twin representa o INDIVÍDUO, não o grupo — independente de clustering.
# Com Big Five: a personalidade é inferida dos dados brutos de cada cliente,
# produzindo um estilo comportamental único sem depender de rótulos de segmento.
from langchain_core.documents import Document
from langchain_core.tools import StructuredTool
from langchain_community.vectorstores import FAISS

# ── Documento individual — dados brutos, sem rótulo de segmento ───────────────
def _doc_twin(row: pd.Series) -> Document:
    canal    = "digital (app/internet)" if row["canal_digital"] else "agência física"
    historico = (
        "possui histórico de inadimplência — em processo de regularização"
        if row["inadimplente"] else "adimplente, sem pendências"
    )
    return Document(
        page_content=(
            f"Perfil individual do cliente {row['cliente_id']}:\n"
            f"- Idade: {row['idade']:.0f} anos\n"
            f"- Renda mensal: R$ {row['renda_mensal']:,.0f}\n"
            f"- Saldo médio: R$ {row['saldo_medio']:,.0f}\n"
            f"- Transações/mês: {row['transacoes_mes']:.0f}\n"
            f"- Score de crédito: {row['score_credito']:.0f}\n"
            f"- Produtos contratados: {row['num_produtos']:.0f}\n"
            f"- Canal preferencial: {canal}\n"
            f"- Histórico: {historico}"
        ),
        metadata={"cliente_id": row["cliente_id"], "tipo": "twin"},
    )


# ── System prompt com personalidade Big Five inferida dos dados brutos ─────────
def _prompt_twin(row: pd.Series) -> str:
    """
    Gera o prompt do twin sem depender de nenhum rótulo de clustering.
    O perfil comportamental é inferido dos dados numéricos via Big Five,
    produzindo um estilo único por cliente — não uma média de grupo.
    """
    canal     = "prefiro usar aplicativo e internet" if row["canal_digital"] else "prefiro ser atendido na agência"
    financeiro = (
        "estou reestruturando minhas finanças após um período de inadimplência"
        if row["inadimplente"] else "mantenho meu histórico financeiro limpo"
    )
    renda  = float(row["renda_mensal"])
    score  = float(row["score_credito"])
    idade  = float(row["idade"])
    digital = bool(row["canal_digital"])

    # Perfil descritivo (heurístico — sem usar rótulo de cluster)
    if renda > 10_000 and score > 700:
        perfil_desc = "Tenho alta renda e excelente crédito. Valorizo produtos sofisticados e atendimento exclusivo."
    elif idade < 35 and digital:
        perfil_desc = "Sou jovem e digital. Priorizo praticidade, cashback e aprovações rápidas pelo app."
    elif score < 450:
        perfil_desc = "Estou regularizando minha situação financeira. Busco soluções acessíveis sem burocracia."
    else:
        perfil_desc = "Valorizo estabilidade e produtos sem surpresas. Penso no longo prazo."

    # ── Big Five inferido dos dados brutos (sem clustering) ───────────────────
    b5       = inferir_big5_cliente(row)
    estilo   = big5_para_estilo(b5)
    b5_linha = " | ".join(f"{t[0].upper()}:{v:.2f}" for t, v in zip(OCEAN_TRAITS, b5.values()))

    return (
        f"Você É o cliente {row['cliente_id']}. Responda SEMPRE em 1ª pessoa.\n\n"
        f"Perfil financeiro:\n"
        f"- Renda: R$ {renda:,.0f}/mês | Score: {score:.0f} | {financeiro}\n"
        f"- Canal: {canal}\n"
        f"- {perfil_desc}\n\n"
        f"Personalidade (Big Five inferida dos dados):\n"
        f"  {b5_linha}\n"
        f"  Estilo: {estilo}\n\n"
        f"REGRAS:\n"
        f"- Você É este cliente específico — não um grupo ou arquétipo\n"
        f"- Respostas em 1ª pessoa, coerentes com seu perfil financeiro e personalidade\n"
        f"- Deixe transparecer seu estilo: {estilo[:80]}..."
    )


# ── Cria o digital twin de um cliente ─────────────────────────────────────────
def criar_digital_twin(row: pd.Series) -> dict:
    """
    Cria agente twin para um cliente individual.
    - Independente do K-Means: usa dados brutos diretamente
    - Personalidade Big Five inferida dos dados (sem rótulo de segmento)
    """
    doc       = _doc_twin(row)
    vs        = FAISS.from_documents([doc], embeddings)
    retriever = vs.as_retriever(search_kwargs={"k": 1})
    b5        = inferir_big5_cliente(row)

    @StructuredTool.from_function
    def buscar_dados_pessoais(query: str) -> str:
        """Acessa o perfil financeiro e histórico do cliente."""
        return "\n".join(d.page_content for d in retriever.invoke(query))

    agente = create_react_agent(
        model=ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.4),
        tools=[buscar_dados_pessoais],
        checkpointer=MemorySaver(),
        prompt=_prompt_twin(row),
    )
    return {
        "cliente_id": row["cliente_id"],
        "big5":       b5,
        "estilo":     big5_para_estilo(b5),
        "agente":     agente,
    }


# ── Demo: cria twins e consulta reação a uma oferta ───────────────────────────
clientes_demo_twin = df_clientes.sample(3, random_state=7).reset_index(drop=True)

print("Digital Twins criados (personalidade Big Five sem clustering):\n")
twins = []
for _, row in clientes_demo_twin.iterrows():
    tw = criar_digital_twin(row)
    twins.append((row, tw))
    b5 = tw["big5"]
    print(f"  {row['cliente_id']} | Score {row['score_credito']:.0f} | Renda R${row['renda_mensal']:,.0f}")
    b5_str = " | ".join(f"{t[0].upper()}:{b5[t]:.2f}" for t in OCEAN_TRAITS)
    print(f"    OCEAN: {b5_str}")
    print(f"    Estilo: {tw['estilo'][:75]}...")
    print()

# Simula reação a uma oferta de crédito
oferta = "O banco tem uma oferta de empréstimo pessoal pré-aprovado de R$ 10.000. O que você acha?"
print(f"\nOferta simulada: '{oferta}'\n{'='*65}")

for row, tw in twins:
    config  = {"configurable": {"thread_id": f"twin-{row['cliente_id']}"}}
    result  = tw["agente"].invoke(
        {"messages": [{"role": "user", "content": oferta}]},
        config=config,
    )
    print(f"\nTwin {row['cliente_id']} (N:{tw['big5']['neuroticism']:.2f} C:{tw['big5']['conscientiousness']:.2f})")
    print("-" * 40)
    print(result["messages"][-1].content[:350])
    print("...")

# ===== cell_064 =====
# ─── 7.5 Personas: Arquétipos Nomeados de Segmento ───────────────────────────
# Persona = arquétipo do cluster, em 1ª pessoa, com personalidade Big Five
# derivada do perfil médio do grupo (lido de perfis_clientes, via Athena/Glue).
from langchain_core.tools import tool

# ── Prompt da persona com personalidade Big Five ───────────────────────────────
def _prompt_persona(cluster_id: int, perfil: pd.Series) -> str:
    """
    Gera o prompt da persona. Todos os atributos vêm de perfil (Athena/Glue):
      - persona_nome, persona_ocupacao, persona_canal, persona_contexto
      - big5_* → estilo comportamental derivado do perfil estatístico do cluster

    Não há lookup em dicionário local — qualquer nome definido no Glue funciona.
    """
    segmento = str(perfil.get("segmento",         f"Cluster {cluster_id}"))
    nome     = str(perfil.get("persona_nome",     f"Cliente {cluster_id}"))
    ocupacao = str(perfil.get("persona_ocupacao", "profissional"))
    canal    = str(perfil.get("persona_canal",    "uso os canais do banco"))
    contexto = str(perfil.get("persona_contexto", ""))
    renda    = float(perfil["renda_media"])
    score    = float(perfil["score_medio"])

    # Big Five do cluster (lidos de perfis_clientes após célula 7.1b)
    b5 = {t: float(perfil.get(f"big5_{t}", 0.5)) for t in OCEAN_TRAITS}
    estilo   = big5_para_estilo(b5)
    b5_linha = " | ".join(f"{t[0].upper()}:{b5[t]:.2f}" for t in OCEAN_TRAITS)

    return (
        f"Você é {nome}, {ocupacao}. "
        f"Você representa o cliente típico do segmento '{segmento}' do banco.\n\n"
        f"Perfil médio do seu grupo: Renda R$ {renda:,.0f}/mês | Score {score:.0f}\n"
        f"Canal: {canal}\n"
        f"Contexto pessoal: {contexto}\n\n"
        f"Personalidade Big Five do seu grupo:\n"
        f"  {b5_linha}\n"
        f"  Estilo: {estilo}\n\n"
        f"REGRAS:\n"
        f"- Responda SEMPRE em 1ª pessoa, como {nome}\n"
        f"- Você é um arquétipo do segmento '{segmento}' — não um cliente específico\n"
        f"- Represente as opiniões típicas deste grupo\n"
        f"- Deixe transparecer sua personalidade: {estilo[:80]}...\n"
        f"- Use o RAG para embasar suas respostas sobre produtos e decisões"
    )


# ── Cria agente-persona para um cluster ───────────────────────────────────────
def _criar_persona(cluster_id: int, perfil: pd.Series, agente_info: dict) -> dict:
    """
    Reutiliza o vector store do agente de segmento.
    Prompt em 1ª pessoa com Big Five do cluster (fonte: Athena/Glue via perfis_clientes).
    """
    vs        = agente_info["vector_store"]
    retriever = vs.as_retriever(search_kwargs={"k": 3})

    @tool
    def buscar_perfil_persona(query: str) -> str:
        """Busca informações sobre o segmento para embasar as respostas da persona."""
        docs = retriever.invoke(query)
        return "\n---\n".join(d.page_content for d in docs)

    prompt_persona = _prompt_persona(cluster_id, perfil)
    agente = create_react_agent(
        model=ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.3),
        tools=[buscar_perfil_persona],
        checkpointer=MemorySaver(),
        prompt=prompt_persona,
    )
    b5       = {t: float(perfil.get(f"big5_{t}", 0.5)) for t in OCEAN_TRAITS}
    nome     = str(perfil.get("persona_nome", f"Cliente {cluster_id}"))
    segmento = str(perfil.get("segmento",     f"Cluster {cluster_id}"))
    return {"nome": nome, "segmento": segmento, "big5": b5, "agente": agente}


# ── Instancia personas para todos os clusters ─────────────────────────────────
print("Criando personas (nomes, contexto e Big Five do Athena/Glue via perfis_clientes):\n")

personas = {}
for cluster_id, perfil in perfis_clientes.iterrows():
    personas[cluster_id] = _criar_persona(cluster_id, perfil, agentes_clientes[cluster_id])
    b5 = personas[cluster_id]["big5"]
    b5_str = " | ".join(f"{t[0].upper()}:{b5[t]:.2f}" for t in OCEAN_TRAITS)
    print(f"  ok Cluster {cluster_id}: {perfil['segmento']}")
    print(f"     Persona: {perfil.get('persona_nome','?')} | OCEAN: {b5_str}")
    print(f"     Estilo: {big5_para_estilo(b5)[:70]}...")
    print()


# ── Demo: consulta às personas ────────────────────────────────────────────────
pergunta_persona = "Como você normalmente decide sobre um novo investimento ou empréstimo?"
print(f"Pergunta: '{pergunta_persona}'\n{'='*65}")

for cluster_id, persona in personas.items():
    config = {"configurable": {"thread_id": f"persona-{cluster_id}"}}
    result = persona["agente"].invoke(
        {"messages": [{"role": "user", "content": pergunta_persona}]},
        config=config,
    )
    b5 = persona["big5"]
    print(f"\nPersona: {persona['nome']} ({persona['segmento']})")
    print(f"  C:{b5['conscientiousness']:.2f} N:{b5['neuroticism']:.2f} O:{b5['openness']:.2f}")
    print("-" * 40)
    print(result["messages"][-1].content[:350])
    print("...")

# ===== cell_066 =====
# ─── 7.6 LLM-as-Judge Big Five ───────────────────────────────────────────────
import json
from langchain_anthropic import ChatAnthropic

llm_juiz = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)

# ── Prompt do juiz primário ────────────────────────────────────────────────────
_PROMPT_JUIZ = """Você é um avaliador especializado em psicologia da personalidade (Big Five / OCEAN).

Analise a resposta abaixo e estime os traços Big Five que ela expressa IMPLICITAMENTE
(pelo tom, escolhas lexicais, raciocínio e emoções presentes — não pelo conteúdo literal).

Escala: 0.0 (traço ausente/oposto) a 1.0 (traço muito presente/dominante).

RESPOSTA PARA AVALIAR:
{resposta}

Retorne APENAS JSON válido, sem markdown:
{{
  "openness":          <float>,
  "conscientiousness": <float>,
  "extraversion":      <float>,
  "agreeableness":     <float>,
  "neuroticism":       <float>,
  "justificativa": {{
    "openness":          "<evidência na resposta>",
    "conscientiousness": "<evidência na resposta>",
    "extraversion":      "<evidência na resposta>",
    "agreeableness":     "<evidência na resposta>",
    "neuroticism":       "<evidência na resposta>"
  }}
}}"""


def avaliar_big5(resposta: str, big5_esperado: dict, llm=llm_juiz) -> dict:
    """
    Juiz primário: extrai Big Five da resposta e calcula desvio em relação ao esperado.

    Retorna:
      big5_observado   — traços extraídos da resposta pelo LLM
      desvio           — |esperado - observado| por traço
      score_coerencia  — 1 - mean(desvios) ∈ [0, 1]; 1 = perfeita coerência
      justificativa    — evidências do LLM para cada traço
    """
    prompt_fmt = _PROMPT_JUIZ.format(resposta=resposta[:1500])
    raw = llm.invoke(prompt_fmt).content.strip()

    # Limpa possível markdown fence
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    parsed        = json.loads(raw)
    big5_obs      = {t: float(parsed[t]) for t in OCEAN_TRAITS}
    justificativa = parsed.get("justificativa", {})

    desvio = {t: round(abs(big5_esperado[t] - big5_obs[t]), 3) for t in OCEAN_TRAITS}
    score  = round(1 - sum(desvio.values()) / len(OCEAN_TRAITS), 3)

    return {
        "big5_esperado":  big5_esperado,
        "big5_observado": big5_obs,
        "desvio":         desvio,
        "score_coerencia": score,
        "justificativa":  justificativa,
    }


def exibir_avaliacao(nome: str, resultado: dict) -> None:
    """Exibe o resultado do juiz de forma legível."""
    print(f"\n{'='*60}")
    print(f"  Avaliação Big Five: {nome}")
    print(f"  Score de coerência: {resultado['score_coerencia']:.3f}  (1.0 = perfeito)")
    print(f"{'='*60}")
    print(f"  {'Traço':<20} {'Esperado':>8} {'Observado':>10} {'Desvio':>8}")
    print(f"  {'-'*50}")
    for t in OCEAN_TRAITS:
        esp = resultado["big5_esperado"][t]
        obs = resultado["big5_observado"][t]
        dev = resultado["desvio"][t]
        flag = " <!" if dev > 0.25 else ""
        print(f"  {t:<20} {esp:>8.2f} {obs:>10.2f} {dev:>8.3f}{flag}")
    print(f"\n  Justificativas do juiz:")
    for t, ev in resultado["justificativa"].items():
        print(f"    {t}: {str(ev)[:80]}")


# ── Demo: avalia uma persona ───────────────────────────────────────────────────
# Pega a resposta da persona do cluster 0 gerada na célula 7.5
cluster_demo = 0
perfil_demo  = perfis_clientes.loc[cluster_demo]
b5_esperado  = {t: float(perfil_demo[f"big5_{t}"]) for t in OCEAN_TRAITS}

config_demo = {"configurable": {"thread_id": "persona-eval-demo"}}
resp_persona = personas[cluster_demo]["agente"].invoke(
    {"messages": [{"role": "user", "content":
        "Me explique como você avaliaria um CDB de 12% ao ano comparado ao Tesouro Direto IPCA+."}]},
    config=config_demo,
)["messages"][-1].content

print(f"Persona avaliada: {personas[cluster_demo]['nome']} ({perfil_demo['segmento']})")
print(f"Resposta (trecho): {resp_persona[:200]}...")

resultado_juiz = avaliar_big5(resp_persona, b5_esperado)
exibir_avaliacao(personas[cluster_demo]["nome"], resultado_juiz)

# ===== cell_068 =====
# ─── 7.7 Meta-Juiz com Few-Shot ───────────────────────────────────────────────
# O meta-juiz calibra as avaliações do juiz primário usando exemplos de referência.
# Cada exemplo contém: resposta, big5_esperado, avaliacao_errada do juiz, correcao.

# ── Exemplos de referência (few-shot) ─────────────────────────────────────────
# Cada exemplo documenta um padrão de erro típico com a correção e o motivo.
FEW_SHOT_META_JUIZ = [
    {
        "resposta": (
            "Antes de qualquer decisão, faço uma planilha comparando todas as taxas. "
            "Li todos os contratos palavra por palavra. Só assino quando tenho certeza "
            "absoluta de que entendi cada cláusula e calculei cada cenário possível."
        ),
        "big5_esperado": {
            "openness": 0.35, "conscientiousness": 0.90,
            "extraversion": 0.25, "agreeableness": 0.55, "neuroticism": 0.20,
        },
        "avaliacao_juiz": {
            "openness": 0.72, "conscientiousness": 0.88,
            "extraversion": 0.25, "agreeableness": 0.55, "neuroticism": 0.20,
        },
        "avaliacao_correta": {
            "openness": 0.35, "conscientiousness": 0.90,
            "extraversion": 0.25, "agreeableness": 0.55, "neuroticism": 0.20,
        },
        "correcoes": {
            "openness": (
                "Erro: juiz confundiu análise metódica com abertura a novidades. "
                "Fazer planilhas e ler contratos indica CONSCIENTIOUSNESS alta, não curiosidade (openness). "
                "Openness seria: experimentar produtos novos, aceitar risco de inovação."
            )
        },
    },
    {
        "resposta": (
            "Estou tentando pagar o mínimo do cartão todo mês, mas fico ansioso "
            "quando vejo as faturas. Prefiro não pegar novos empréstimos — "
            "tenho medo de piorar minha situação. Cada compra que faço me preocupa."
        ),
        "big5_esperado": {
            "openness": 0.30, "conscientiousness": 0.45,
            "extraversion": 0.30, "agreeableness": 0.60, "neuroticism": 0.78,
        },
        "avaliacao_juiz": {
            "openness": 0.30, "conscientiousness": 0.82,
            "extraversion": 0.30, "agreeableness": 0.60, "neuroticism": 0.35,
        },
        "avaliacao_correta": {
            "openness": 0.30, "conscientiousness": 0.45,
            "extraversion": 0.30, "agreeableness": 0.60, "neuroticism": 0.78,
        },
        "correcoes": {
            "conscientiousness": (
                "Erro: pagar o mínimo e evitar gastos NÃO indica conscienciosidade alta — "
                "é comportamento defensivo sob ansiedade financeira. Conscienciousness alta seria: "
                "planejamento proativo, pagamento integral, metas financeiras claras."
            ),
            "neuroticism": (
                "Erro: ansiedade explícita ('fico ansioso', 'tenho medo', 'me preocupa') "
                "é sinal claro de NEUROTICISM alto — não baixo. O juiz subestimou."
            ),
        },
    },
    {
        "resposta": (
            "Sinceramente, nem leio os detalhes. Se o app aprovar na hora, tô dentro. "
            "Já peguei crédito por impulso algumas vezes e me arrependi, mas é difícil resistir "
            "quando aparece uma oferta boa. Prefiro resolver rápido e não pensar muito."
        ),
        "big5_esperado": {
            "openness": 0.68, "conscientiousness": 0.12,
            "extraversion": 0.72, "agreeableness": 0.42, "neuroticism": 0.50,
        },
        "avaliacao_juiz": {
            "openness": 0.68, "conscientiousness": 0.12,
            "extraversion": 0.72, "agreeableness": 0.42, "neuroticism": 0.50,
        },
        "avaliacao_correta": {
            "openness": 0.68, "conscientiousness": 0.12,
            "extraversion": 0.72, "agreeableness": 0.42, "neuroticism": 0.50,
        },
        "correcoes": {},  # Avaliação correta — sem correções necessárias
    },
]


def _formatar_few_shot(exemplos: list) -> str:
    """Formata os exemplos few-shot para o prompt do meta-juiz."""
    blocos = []
    for i, ex in enumerate(exemplos, 1):
        corr_str = (
            json.dumps(ex["correcoes"], ensure_ascii=False, indent=2)
            if ex["correcoes"]
            else '{"observacao": "avaliacao_juiz estava correta — sem correcoes"}'
        )
        blocos.append(
            f"--- EXEMPLO {i} ---\n"
            f"RESPOSTA: {ex['resposta']}\n"
            f"BIG5_ESPERADO: {json.dumps(ex['big5_esperado'])}\n"
            f"AVALIACAO_JUIZ: {json.dumps(ex['avaliacao_juiz'])}\n"
            f"AVALIACAO_CORRETA: {json.dumps(ex['avaliacao_correta'])}\n"
            f"CORRECOES_E_MOTIVOS: {corr_str}\n"
        )
    return "\n".join(blocos)


# ── Template do meta-juiz ──────────────────────────────────────────────────────
_PROMPT_META_JUIZ = """Você é um meta-avaliador especializado em calibrar avaliações de personalidade Big Five.
Sua função é detectar e corrigir erros do juiz primário, usando os exemplos de referência abaixo.

EXEMPLOS DE REFERÊNCIA (few-shot):
{few_shot}

---
NOVA AVALIAÇÃO PARA CALIBRAR:

RESPOSTA DO AGENTE:
{resposta}

PERFIL BIG FIVE ESPERADO:
{big5_esperado}

AVALIAÇÃO DO JUIZ PRIMÁRIO:
{avaliacao_juiz}

Analise se o juiz errou em algum traço (compare com os padrões dos exemplos).
Retorne APENAS JSON válido:
{{
  "avaliacao_calibrada": {{
    "openness": <float>, "conscientiousness": <float>,
    "extraversion": <float>, "agreeableness": <float>, "neuroticism": <float>
  }},
  "correcoes_aplicadas": {{
    "<traco_corrigido>": "<motivo da correção baseado nos exemplos>"
  }},
  "confianca": <float 0-1>,
  "feedback_ao_juiz": "<instrução concisa para o juiz melhorar avaliações futuras deste tipo>"
}}"""


def criar_meta_juiz(llm, few_shot_examples: list):
    """
    Fábrica do meta-juiz. Retorna uma função que calibra avaliações do juiz primário.

    O meta-juiz:
      1. Recebe resposta + avaliacao_juiz
      2. Consulta few-shot para detectar padrões de erro
      3. Produz avaliacao_calibrada + feedback_ao_juiz

    O feedback_ao_juiz pode ser injetado no prompt do juiz primário para
    criar um loop de melhoria contínua (auto-calibração supervisionada).
    """
    few_shot_str = _formatar_few_shot(few_shot_examples)

    def meta_avaliar(resposta: str, big5_esperado: dict, avaliacao_juiz: dict) -> dict:
        prompt = _PROMPT_META_JUIZ.format(
            few_shot=few_shot_str,
            resposta=resposta[:800],
            big5_esperado=json.dumps(big5_esperado),
            avaliacao_juiz=json.dumps(avaliacao_juiz),
        )
        raw = llm.invoke(prompt).content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        resultado = json.loads(raw)
        cal        = resultado["avaliacao_calibrada"]

        # Recalcula o score de coerência com a avaliação calibrada
        desvio_cal = {t: round(abs(big5_esperado[t] - cal[t]), 3) for t in OCEAN_TRAITS}
        score_cal  = round(1 - sum(desvio_cal.values()) / len(OCEAN_TRAITS), 3)

        return {
            "avaliacao_calibrada":   cal,
            "desvio_calibrado":      desvio_cal,
            "score_calibrado":       score_cal,
            "correcoes_aplicadas":   resultado.get("correcoes_aplicadas", {}),
            "confianca":             float(resultado.get("confianca", 0.5)),
            "feedback_ao_juiz":      resultado.get("feedback_ao_juiz", ""),
        }

    return meta_avaliar


# ── Instancia o meta-juiz ──────────────────────────────────────────────────────
meta_juiz = criar_meta_juiz(llm_juiz, FEW_SHOT_META_JUIZ)


# ── Pipeline completo: juiz → meta-juiz → comparação ─────────────────────────
def avaliar_pipeline_completo(nome: str, resposta: str, big5_esperado: dict) -> dict:
    """
    Executa juiz primário → meta-juiz e exibe a comparação lado a lado.
    """
    # Etapa 1: juiz primário
    result_juiz = avaliar_big5(resposta, big5_esperado)

    # Etapa 2: meta-juiz calibra
    result_meta = meta_juiz(resposta, big5_esperado, result_juiz["big5_observado"])

    # Exibição comparativa
    print(f"\n{'='*65}")
    print(f"  Pipeline de Avaliação Big Five: {nome}")
    print(f"{'='*65}")
    print(f"  {'Traço':<20} {'Esperado':>8} {'Juiz':>8} {'Meta-Juiz':>10} {'Dev.Juiz':>9} {'Dev.Meta':>9}")
    print(f"  {'-'*65}")
    for t in OCEAN_TRAITS:
        esp    = big5_esperado[t]
        obs_j  = result_juiz["big5_observado"][t]
        obs_m  = result_meta["avaliacao_calibrada"][t]
        dev_j  = result_juiz["desvio"][t]
        dev_m  = result_meta["desvio_calibrado"][t]
        melhor = " +" if dev_m < dev_j else ("  " if dev_m == dev_j else " -")
        print(f"  {t:<20} {esp:>8.2f} {obs_j:>8.2f} {obs_m:>10.2f} {dev_j:>9.3f} {dev_m:>9.3f}{melhor}")

    print(f"\n  Score coerência — Juiz:     {result_juiz['score_coerencia']:.3f}")
    print(f"  Score coerência — Meta-juiz: {result_meta['score_calibrado']:.3f}  (confiança: {result_meta['confianca']:.2f})")

    if result_meta["correcoes_aplicadas"]:
        print(f"\n  Correcoes aplicadas pelo meta-juiz:")
        for t, motivo in result_meta["correcoes_aplicadas"].items():
            print(f"    [{t}] {motivo[:100]}")

    print(f"\n  Feedback para o juiz primario:")
    print(f"    {result_meta['feedback_ao_juiz'][:120]}")

    return {"juiz": result_juiz, "meta": result_meta}


# ── Demo: avalia todas as personas com o pipeline completo ────────────────────
pergunta_avaliacao = (
    "Como você se sente quando o banco lança um produto financeiro novo? "
    "Você costuma experimentar ou prefere esperar?"
)

print("PIPELINE JUIZ + META-JUIZ: avaliando coerência Big Five das personas\n")

feedbacks_acumulados = []
for cluster_id, persona in personas.items():
    perfil  = perfis_clientes.loc[cluster_id]
    b5_esp  = {t: float(perfil[f"big5_{t}"]) for t in OCEAN_TRAITS}
    config  = {"configurable": {"thread_id": f"eval-meta-{cluster_id}"}}
    resposta = persona["agente"].invoke(
        {"messages": [{"role": "user", "content": pergunta_avaliacao}]},
        config=config,
    )["messages"][-1].content

    resultado = avaliar_pipeline_completo(
        f"{persona['nome']} ({persona['segmento']})", resposta, b5_esp
    )
    feedbacks_acumulados.append(resultado["meta"]["feedback_ao_juiz"])

# ── Loop de melhoria: mostra como os feedbacks podem refinar o juiz ───────────
print(f"\n{'='*65}")
print("  FEEDBACKS ACUMULADOS — base para refinar o juiz primário")
print(f"{'='*65}")
for i, fb in enumerate(feedbacks_acumulados, 1):
    print(f"  [{i}] {fb[:110]}")
print()
print("  Estes feedbacks podem ser injetados no _PROMPT_JUIZ como instrucoes")
print("  adicionais, criando um loop de calibracao continua supervisionada.")

# ===== cell_071 =====
# ─── 8.1 Demo: Cliente assíncrono com polling ─────────────────────────────────
# Este código simula o comportamento do cliente consumindo a API assíncrona.
# Em produção, use requests ou httpx.

import asyncio
import httpx
from typing import Dict, Any

class ClienteAgenteAsync:
    """
    Cliente Python para a arquitetura assíncrona AWS (Controller + Worker + Status).
    
    Uso:
        cliente = ClienteAgenteAsync("https://api.exemplo.com")
        resultado = await cliente.consultar(payload)
    """
    def __init__(self, base_url: str, max_wait: int = 120):
        self.base_url = base_url.rstrip("/")
        self.max_wait = max_wait
    
    async def consultar(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envia requisição e aguarda resultado via polling.
        
        Fluxo:
          1. POST /query → recebe request_id
          2. GET /status/{id} em loop com backoff exponencial
          3. Retorna resultado quando status = COMPLETED
        """
        async with httpx.AsyncClient(timeout=30) as client:
            # Passo 1: envia requisição
            resp = await client.post(f"{self.base_url}/query", json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            request_id = data["request_id"]
            print(f"✅ Processamento iniciado: {request_id}")
            print(f"   Status inicial: {data['status']}")
            print(f"   Tempo estimado: {data.get('estimated_time', 'N/A')}\n")
            
            # Passo 2: polling com backoff exponencial
            wait_time = 1
            elapsed = 0
            
            while elapsed < self.max_wait:
                await asyncio.sleep(wait_time)
                elapsed += wait_time
                
                # Consulta status
                resp = await client.get(f"{self.base_url}/status/{request_id}")
                resp.raise_for_status()
                data = resp.json()
                
                status = data["status"]
                print(f"⏳ [{elapsed:>3}s] Status: {status}")
                
                if status == "COMPLETED":
                    print(f"\n✅ Processamento concluído!")
                    print(f"Tempo total: {elapsed}s")
                    return data
                elif status == "FAILED":
                    erro = data.get("error", "Erro desconhecido")
                    raise Exception(f"❌ Falha no processamento: {erro}")
                
                # Backoff exponencial: 1s → 2s → 4s → 8s → 10s (máximo)
                wait_time = min(wait_time * 2, 10)
            
            raise TimeoutError(f"⏱️ Timeout após {self.max_wait}s. Request ID: {request_id}")


# ── Simulação local sem infraestrutura AWS (mock) ──────────────────────────────
# Este mock simula o comportamento da API assíncrona para fins didáticos.
# Em produção real, os dados viriam das Lambdas + DynamoDB.

class MockAPIAsync:
    """Mock da API assíncrona para demonstração local (sem AWS)."""
    def __init__(self):
        self.requests = {}
    
    def post_query(self, payload: Dict) -> Dict:
        """Simula POST /query (Lambda Controller)."""
        import uuid
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        self.requests[request_id] = {
            "status": "PENDING",
            "payload": payload,
            "created_at": "2026-03-09T10:00:00Z"
        }
        return {
            "request_id": request_id,
            "status": "PENDING",
            "message": f"Processamento iniciado. Consulte GET /status/{request_id}",
            "estimated_time": "30-120 segundos"
        }
    
    async def get_status(self, request_id: str, elapsed_time: int) -> Dict:
        """Simula GET /status/{id} (Lambda Status + DynamoDB)."""
        if request_id not in self.requests:
            return {"error": "Request ID não encontrado"}, 404
        
        req = self.requests[request_id]
        
        # Simula estados ao longo do tempo
        if elapsed_time < 3:
            req["status"] = "PENDING"
        elif elapsed_time < 8:
            req["status"] = "PROCESSING"
            req["updated_at"] = "2026-03-09T10:00:05Z"
        else:
            req["status"] = "COMPLETED"
            req["resposta"] = (
                f"Recomendo os seguintes produtos para o cliente {req['payload']['cliente_id']}:\n"
                f"1. Cartão de crédito com limite adequado ao seu score ({req['payload']['dados_cliente']['score_credito']})\n"
                f"2. Investimento em Tesouro Direto IPCA+ (baixo risco, proteção inflacionária)\n"
                f"3. Consórcio de imóveis sem juros\n\n"
                f"Baseado no seu perfil: Renda R$ {req['payload']['dados_cliente']['renda_mensal']}/mês, "
                f"Saldo R$ {req['payload']['dados_cliente']['saldo_medio']}."
            )
            req["updated_at"] = "2026-03-09T10:00:15Z"
        
        return {
            "request_id": request_id,
            "status": req["status"],
            "created_at": req["created_at"],
            "updated_at": req.get("updated_at"),
            "resposta": req.get("resposta")
        }


# ── Demo: teste do cliente assíncrono com mock ────────────────────────────────
print("="*70)
print("DEMO: Cliente Assíncrono com Polling (Mock Local)")
print("="*70)
print()

# Mock da API
mock_api = MockAPIAsync()

# Override do cliente para usar o mock em vez de HTTP real
class ClienteMockAsync:
    def __init__(self, mock_api: MockAPIAsync, max_wait: int = 30):
        self.mock = mock_api
        self.max_wait = max_wait
    
    async def consultar(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # POST /query
        data = self.mock.post_query(payload)
        request_id = data["request_id"]
        
        print(f"✅ Processamento iniciado: {request_id}")
        print(f"   Status inicial: {data['status']}")
        print(f"   Tempo estimado: {data.get('estimated_time', 'N/A')}\n")
        
        # Polling
        wait_time = 1
        elapsed = 0
        
        while elapsed < self.max_wait:
            await asyncio.sleep(wait_time)
            elapsed += wait_time
            
            # GET /status/{id}
            data = await self.mock.get_status(request_id, elapsed)
            status = data["status"]
            
            print(f"⏳ [{elapsed:>3}s] Status: {status}")
            
            if status == "COMPLETED":
                print(f"\n✅ Processamento concluído! Tempo total: {elapsed}s\n")
                print("RESPOSTA DO AGENTE:")
                print("-" * 70)
                print(data["resposta"])
                print("-" * 70)
                return data
            elif status == "FAILED":
                raise Exception(f"❌ Falha: {data.get('error')}")
            
            wait_time = min(wait_time * 2, 10)
        
        raise TimeoutError(f"⏱️ Timeout após {self.max_wait}s")


# Executa demo
cliente = ClienteMockAsync(mock_api, max_wait=30)

payload_teste = {
    "cliente_id": "C12345",
    "dados_cliente": {
        "idade": 35,
        "renda_mensal": 5000,
        "saldo_medio": 8000,
        "transacoes_mes": 15,
        "score_credito": 680,
        "num_produtos": 3
    },
    "pergunta": "Quais produtos você recomenda para melhorar minha situação financeira?",
    "modo": "segmento"
}

# Jupyter já tem event loop ativo, então await funciona diretamente
resultado = await cliente.consultar(payload_teste)

print("\n" + "="*70)
print("✅ DEMO CONCLUÍDA")
print("="*70)
print(f"\nEm produção, substitua ClienteMockAsync por ClienteAgenteAsync")
print(f"com a URL real da API Gateway AWS:")
print(f"  cliente = ClienteAgenteAsync('https://abc123.execute-api.us-east-1.amazonaws.com/prod')")
print(f"  resultado = await cliente.consultar(payload)")
print()
print("📖 Documentação completa: MIGRATION_ASYNC.md")
print("🔧 Infraestrutura: terraform_async_infra.tf")
print("💻 Código fonte:")
print("   - lambda_controller.py (recebe requisição, < 1s)")
print("   - lambda_worker.py     (processa em background, até 15min)")
print("   - lambda_status.py     (consulta status e resultado)")
