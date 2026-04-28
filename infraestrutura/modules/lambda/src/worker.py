"""
Worker Lambda — Pipeline RAG completo com OTel/Langfuse.

Modos:
  segmento — gerente fala sobre o cliente em 3ª pessoa (RAG: cluster index)
  persona  — arquétipo nomeado do cluster em 1ª pessoa (RAG: cluster index)
  twin     — digital twin do cliente em 1ª pessoa     (RAG: clientes-digital-twins)

Cold start: carrega slim PKL do S3 (numpy only, sem sklearn).
Warm start: reutiliza modelo em memória.
"""
from __future__ import annotations

import json
import logging
import os
import pickle
import traceback
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
from botocore.config import Config
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

import otel_config  # inicializa OTel + openlit antes de qualquer chamada Bedrock
otel_config.init()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Clientes AWS ───────────────────────────────────────────────────────────────
_config = Config(connect_timeout=5, read_timeout=30)
_dynamodb = boto3.resource("dynamodb", config=_config)
_sns = boto3.client("sns", config=_config)
_s3 = boto3.client("s3", config=_config)

# ── Variáveis de ambiente ──────────────────────────────────────────────────────
TABLE_NAME = os.environ["DYNAMODB_TABLE"]
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_PREFIX = os.environ.get("S3_PREFIX", "clientes-agente/")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
AWS_REGION = os.environ.get("AWS_REGION", "sa-east-1")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250514-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
NEPTUNE_ENDPOINT = os.environ.get("NEPTUNE_ENDPOINT", "")

FEATURES = ["idade", "renda_mensal", "saldo_medio", "transacoes_mes", "score_credito", "num_produtos"]

# ── Clientes inicializados no módulo (fora do handler — boas práticas Lambda) ──
_bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name=BEDROCK_REGION,
    config=Config(connect_timeout=5, read_timeout=120),
)

# ── Estado de cold start (PKL carregado do S3 na primeira invocação) ───────────
_model_data: Optional[Dict[str, Any]] = None


def _get_model() -> Dict[str, Any]:
    """Carrega slim PKL do S3 no cold start."""
    global _model_data
    if _model_data is not None:
        return _model_data

    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET não definido — não é possível carregar o modelo.")

    key = f"{S3_PREFIX}modelo_clustering_slim.pkl"
    log.info("Cold start: carregando modelo de s3://%s/%s", S3_BUCKET, key)
    extra = {"ExpectedBucketOwner": AWS_ACCOUNT_ID} if AWS_ACCOUNT_ID else {}
    obj = _s3.get_object(Bucket=S3_BUCKET, Key=key, **extra)
    _model_data = pickle.loads(obj["Body"].read())
    log.info("Modelo carregado: %d clusters.", _model_data["n_clusters"])
    return _model_data



def _classificar(dados: Dict[str, float]) -> int:
    m = _get_model()
    features = m["features"]
    X = np.array([[dados[f] for f in features]], dtype=float)
    X = (X - m["scale_mean"]) / m["scale_std"]
    dist = np.linalg.norm(X - m["centroids"], axis=1)
    return int(np.argmin(dist))



def _os_client() -> OpenSearch:
    boto_session = boto3.session.Session()
    creds = boto_session.get_credentials().get_frozen_credentials()
    auth = AWS4Auth(creds.access_key, creds.secret_key, AWS_REGION, "es",
                    session_token=creds.token)
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def _rag_segmento(cluster_id: int, query: str, k: int = 3) -> str:
    if not OPENSEARCH_ENDPOINT:
        return ""
    try:
        client = _os_client()
        resp = client.search(
            index=f"clientes-segmento-{cluster_id}",
            body={"query": {"match": {"text": query}}, "size": k},
        )
        return _extrair_texto(resp)
    except Exception:
        log.warning("Erro no RAG de segmento (cluster %d): %s", cluster_id, traceback.format_exc())
        return ""


def _rag_graph_sync(cluster_id: int, query: str, k: int = 3) -> str:
    """
    Consulta o índice OpenSearch 'neptune-graph-sync' replicado do Neptune.
    Permite busca BM25 sobre o snapshot do grafo sem chamar Neptune diretamente,
    reduzindo latência e eliminando dependência de VPC no caminho crítico.
    """
    if not OPENSEARCH_ENDPOINT:
        return ""
    try:
        client = _os_client()
        resp = client.search(
            index="neptune-graph-sync",
            body={
                "query": {
                    "bool": {
                        "must": {"match": {"text": query}},
                        "filter": {"term": {"cluster_id": cluster_id}},
                    }
                },
                "size": k,
            },
        )
        return _extrair_texto(resp)
    except Exception:
        log.warning("Erro no RAG graph-sync (cluster %d): %s", cluster_id, traceback.format_exc())
        return ""


def _rag_twin(cliente_id: str, query: str, k: int = 3) -> str:
    if not OPENSEARCH_ENDPOINT:
        return ""
    try:
        client = _os_client()
        resp = client.search(
            index="clientes-digital-twins",
            body={
                "query": {
                    "bool": {
                        "must": {"match": {"text": query}},
                        "filter": {"term": {"metadata.cliente_id": cliente_id}},
                    }
                },
                "size": k,
            },
        )
        return _extrair_texto(resp)
    except Exception:
        log.warning("Erro no RAG de twin (cliente %s): %s", cliente_id, traceback.format_exc())
        return ""


def _extrair_texto(resp: Dict) -> str:
    hits = resp.get("hits", {}).get("hits", [])
    textos = [h.get("_source", {}).get("text", "") for h in hits]
    return "\n\n".join(t for t in textos if t)



def _neptune_client():
    """Retorna cliente HTTP simples para consultas Gremlin/OpenCypher via HTTPS."""
    import urllib.request
    import urllib.parse

    class _NeptuneClient:
        def __init__(self, endpoint: str):
            self._base = f"https://{endpoint}:8182"

        def query(self, cypher: str) -> List[Dict]:
            data = urllib.parse.urlencode({"query": cypher}).encode()
            req = urllib.request.Request(
                f"{self._base}/openCypher",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                import json as _json
                return _json.loads(r.read()).get("results", [])

    return _NeptuneClient(NEPTUNE_ENDPOINT)


def _rag_graph(cluster_id: int, cliente_id: str, modo: str) -> str:
    """
    Recuperação GraphRAG via OpenCypher no Neptune.
    Retorna contexto estruturado de relacionamentos do grafo de conhecimento:
      - Segmento → Produtos recomendados
      - Segmento → Persona arquétipo
      - Cliente → Clientes similares (k-NN via cluster)
    Complementa o RAG BM25 do OpenSearch com raciocínio multi-hop.
    """
    if not NEPTUNE_ENDPOINT:
        return ""
    try:
        client = _neptune_client()
        blocos: List[str] = []

        # Hop 1: produtos e estratégia do segmento
        q_seg = (
            f"MATCH (s:Segmento {{cluster_id: {cluster_id}}})-[:RECOMENDA]->(p:Produto) "
            "RETURN s.nome AS segmento, collect(p.nome) AS produtos"
        )
        for row in client.query(q_seg):
            seg = row.get("segmento", "")
            produtos = ", ".join(row.get("produtos", []))
            if produtos:
                blocos.append(f"Produtos recomendados para '{seg}': {produtos}.")

        # Hop 2: persona arquétipo do segmento
        q_persona = (
            f"MATCH (s:Segmento {{cluster_id: {cluster_id}}})-[:TEM_PERSONA]->(p:Persona) "
            "RETURN p.nome AS nome, p.ocupacao AS ocupacao, p.contexto AS contexto"
        )
        for row in client.query(q_persona):
            blocos.append(
                f"Persona arquétipo: {row.get('nome')} ({row.get('ocupacao')}). "
                f"{row.get('contexto', '')}"
            )

        # Hop 2 (twin): histórico financeiro de clientes similares no mesmo cluster
        if modo == "twin" and cliente_id:
            q_similar = (
                f"MATCH (c:Cliente {{id: '{cliente_id}'}})-[:SIMILAR_A]->(s:Cliente) "
                "RETURN s.id AS similar_id, s.score_credito AS score, "
                "s.renda_mensal AS renda LIMIT 3"
            )
            similares = client.query(q_similar)
            if similares:
                resumo = "; ".join(
                    f"Cliente {r['similar_id']} (score {r['score']:.0f}, renda R$ {r['renda']:,.0f})"
                    for r in similares
                )
                blocos.append(f"Clientes similares no grafo: {resumo}.")

        return "\n".join(blocos)
    except Exception:
        log.warning("Erro no RAG de grafo (cluster %d): %s", cluster_id, traceback.format_exc())
        return ""


def _perfil(cluster_id: int) -> Dict[str, Any]:
    # perfis.to_dict() gera {"coluna": {cluster_id: valor}, ...}
    # precisamos inverter para {"coluna": valor} para o cluster específico
    raw = _get_model()["perfis"]
    return {col: vals[cluster_id] for col, vals in raw.items() if cluster_id in vals}


def _system_segmento(cluster_id: int) -> str:
    p = _perfil(cluster_id)
    seg = p.get("segmento", f"Cluster {cluster_id}")
    prompt = p.get("prompt_segmento", "")
    if not prompt:
        prompt = (
            f"Você é um gerente de relacionamento do banco responsável pelo segmento '{seg}'. "
            "Analise os dados do cliente e responda com precisão e clareza em 3ª pessoa. "
            "Seja objetivo, use dados concretos e termine com uma recomendação de ação."
        )
    return prompt


def _system_persona(cluster_id: int) -> str:
    p = _perfil(cluster_id)
    seg = p.get("segmento", f"Cluster {cluster_id}")
    nome = p.get("persona_nome", f"Cliente do Cluster {cluster_id}")
    ocupacao = p.get("persona_ocupacao", "profissional")
    canal = p.get("persona_canal", "uso os canais do banco")
    contexto = p.get("persona_contexto", "")
    return (
        f"Você é {nome}, {ocupacao}. Representa o cliente típico do segmento '{seg}'. "
        f"Canal preferencial: {canal}. {contexto} "
        "REGRAS ABSOLUTAS: (1) Responda SEMPRE em 1ª pessoa. "
        "(2) Seja autêntico ao perfil — use linguagem, prioridades e preocupações coerentes. "
        "(3) Nunca quebre o personagem nem mencione que é uma IA."
    )


def _system_twin(cliente_id: str, dados: Dict) -> str:
    renda = float(dados.get("renda_mensal", 0))
    score = float(dados.get("score_credito", 0))
    idade = float(dados.get("idade", 30))
    canal = "digital (app/internet banking)" if dados.get("canal_digital") else "agência presencial"
    inadimplente = dados.get("inadimplente", dados.get("inadimplencia", 0))
    historico = "em reestruturação financeira após inadimplência" if inadimplente else "adimplente"
    return (
        f"Você é o gêmeo digital do cliente {cliente_id}. "
        f"Simule EXATAMENTE como este cliente específico pensaria e reagiria:\n"
        f"  Idade: {idade:.0f} anos | Renda: R$ {renda:,.0f}/mês | "
        f"Score: {score:.0f} | Canal: {canal} | Situação: {historico}\n\n"
        "REGRAS ABSOLUTAS: (1) Responda em 1ª pessoa ('Eu prefiro...', 'Para mim...'). "
        "(2) Suas opiniões devem refletir fielmente renda, score e histórico acima. "
        "(3) Não quebre o personagem. (4) Não mencione que é uma simulação."
    )


# ── Few-shot examples por modo ────────────────────────────────────────────────

_FEWSHOT_SEGMENTO: List[Dict] = [
    {
        "role": "user",
        "content": (
            "Contexto relevante:\nPerfil 'Jovem Digital': 312 clientes, idade média 27 anos, "
            "renda R$ 2.800/mês, score 640, inadimplência 8,2%, uso digital 94%.\n\n"
            "Pergunta: Que produto de crédito faz mais sentido para este cliente?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Com base no perfil Jovem Digital, o produto mais adequado é o **cartão de crédito com cashback "
            "de 2% sem anuidade**. Justificativa: score 640 permite aprovação sem garantias; uso digital de "
            "94% indica preferência por gestão via app; renda de R$ 2.800 comporta limite inicial de R$ 2.000 "
            "sem risco de superendividamento. Evitar crédito pessoal neste momento — inadimplência de 8,2% "
            "sinaliza fragilidade de caixa. **Ação recomendada:** oferta proativa via push notification no app "
            "com aprovação instantânea e limite pré-aprovado."
        ),
    },
    {
        "role": "user",
        "content": (
            "Contexto relevante:\nPerfil 'Premium Conservador': 87 clientes, idade média 54 anos, "
            "renda R$ 19.000/mês, saldo R$ 142.000, score 835, inadimplência 0,3%, uso digital 41%.\n\n"
            "Pergunta: Como abordar este cliente sobre previdência privada?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "O cliente Premium Conservador é o perfil ideal para PGBL. Abordagem recomendada: destacar o "
            "**benefício fiscal imediato** — com renda de R$ 19.000/mês, a dedução de até 12% da renda bruta "
            "representa economia de até R$ 27.360/ano no IR (tabela progressiva). Saldo de R$ 142.000 indica "
            "patrimônio consolidado que busca proteção real. Score 835 e inadimplência 0,3% confirmam "
            "disciplina financeira. **Ação recomendada:** agendar reunião presencial com gerente dedicado "
            "— uso digital de 41% indica preferência por atendimento exclusivo e personalizado."
        ),
    },
]

_FEWSHOT_PERSONA: List[Dict] = [
    {
        "role": "user",
        "content": "O banco está oferecendo um empréstimo pessoal com taxa de 2,9% ao mês. Você toparia?",
    },
    {
        "role": "assistant",
        "content": (
            "Depende muito do que eu preciso fazer com esse dinheiro. 2,9% ao mês parece pouco, mas no ano "
            "dá quase 42% — isso é caro. Antes de assinar qualquer coisa eu calcularia o custo total, "
            "não só a parcela. Se for para uma emergência real, eu pesaria. Para compra de desejo? "
            "Provavelmente esperaria juntar o dinheiro primeiro."
        ),
    },
    {
        "role": "user",
        "content": "Como você se sente quando recebe uma oferta de produto financeiro por telefone?",
    },
    {
        "role": "assistant",
        "content": (
            "Honestamente? Fico desconfiado. Prefiro muito mais ver as condições por escrito, no app ou no site, "
            "do meu jeito e no meu tempo. Quando alguém liga tentando me convencer na hora, parece que estão "
            "escondendo alguma coisa nas letras miúdas. Se o produto for bom, ele vai continuar bom amanhã "
            "também — não preciso decidir em 3 minutos de chamada."
        ),
    },
]

_FEWSHOT_TWIN: List[Dict] = [
    {
        "role": "user",
        "content": (
            "Contexto relevante:\nCliente adimplente, score 620, renda R$ 4.500, prefere agência.\n\n"
            "Pergunta: Você investiria em Tesouro Direto?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Já ouvi falar do Tesouro Direto, mas confesso que nunca mexi nisso. Com R$ 4.500 de renda, "
            "depois de pagar as contas fixas sobra pouco — uns R$ 400 por mês, quando sobra. Ficaria "
            "mais tranquilo conversando pessoalmente com alguém do banco antes de colocar dinheiro em "
            "qualquer investimento. O que me preocupa é: e se eu precisar do dinheiro antes do prazo?"
        ),
    },
    {
        "role": "user",
        "content": (
            "Contexto relevante:\nCliente inadimplente, score 420, renda variável R$ 2.100.\n\n"
            "Pergunta: O que você acha do programa de renegociação com 80% de desconto nos juros?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Isso seria uma saída que eu precisava. 80% de desconto nos juros? Eu toparia na hora — "
            "o que me paralisa é justamente os juros que só crescem. Com R$ 2.100 de renda, se a "
            "parcela ficar em algo que eu consiga pagar todo mês sem apertar demais, eu assino. "
            "O que eu quero é sair dessa situação e recuperar meu nome. Tem como parcelar em bastantes vezes?"
        ),
    },
]


def _fewshot(modo: str) -> List[Dict]:
    if modo == "segmento":
        return _FEWSHOT_SEGMENTO
    if modo == "persona":
        return _FEWSHOT_PERSONA
    if modo == "twin":
        return _FEWSHOT_TWIN
    return []


def _chamar_claude(system: str, contexto_rag: str, pergunta: str, modo: str = "segmento") -> str:
    conteudo = pergunta
    if contexto_rag:
        conteudo = f"Contexto relevante:\n{contexto_rag}\n\nPergunta: {pergunta}"

    # Converte few-shot turns para o formato Converse API (content como lista de blocos)
    converse_messages = []
    for turn in _fewshot(modo):
        converse_messages.append({
            "role": turn["role"],
            "content": [{"text": turn["content"]}],
        })
    converse_messages.append({"role": "user", "content": [{"text": conteudo}]})

    resp = _bedrock_client.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": system}],
        messages=converse_messages,
        inferenceConfig={"maxTokens": 2048},
    )
    return resp["output"]["message"]["content"][0]["text"]



def _executar(payload: Dict) -> str:
    pergunta: str = payload["pergunta"]
    modo: str = payload.get("modo", "segmento")
    dados: Dict = payload.get("dados_cliente", payload.get("dados", {}))
    cliente_id: str = payload.get("cliente_id", "")

    if modo == "twin":
        cluster_id = payload.get("cluster_id")
        if cluster_id is None and dados:
            cluster_id = _classificar(dados)
        cluster_id = int(cluster_id) if cluster_id is not None else 0
        contexto_bm25 = _rag_twin(cliente_id, pergunta)
        contexto_sync = _rag_graph_sync(cluster_id, pergunta)   # grafo replicado (rápido)
        contexto_graph = _rag_graph(cluster_id, cliente_id, "twin")  # Neptune live (similar)
        contexto = "\n\n".join(filter(None, [contexto_bm25, contexto_sync, contexto_graph]))
        system = _system_twin(cliente_id, dados)
        resultado = _chamar_claude(system, contexto, pergunta, modo="twin")
        return json.dumps({
            "cliente_id": cliente_id,
            "modo": "twin",
            "resposta": resultado,
        }, ensure_ascii=False)

    if modo == "persona":
        cluster_id = payload.get("cluster_id")
        if cluster_id is None:
            if not dados:
                raise ValueError("Modo 'persona' requer 'cluster_id' ou 'dados_cliente'.")
            cluster_id = _classificar(dados)
        cluster_id = int(cluster_id)
        contexto_bm25 = _rag_segmento(cluster_id, pergunta)
        contexto_sync = _rag_graph_sync(cluster_id, pergunta)   # grafo replicado (rápido)
        contexto_graph = _rag_graph(cluster_id, "", "persona")  # Neptune live (multi-hop)
        contexto = "\n\n".join(filter(None, [contexto_bm25, contexto_sync, contexto_graph]))
        system = _system_persona(cluster_id)
        resultado = _chamar_claude(system, contexto, pergunta, modo="persona")
        p = _perfil(cluster_id)
        return json.dumps({
            "cluster_id": cluster_id,
            "segmento": p.get("segmento", ""),
            "persona_nome": p.get("persona_nome", ""),
            "modo": "persona",
            "resposta": resultado,
        }, ensure_ascii=False)

    # modo segmento (default)
    ausentes = set(FEATURES) - set(dados.keys())
    if ausentes:
        raise ValueError(f"Campos ausentes em dados_cliente: {ausentes}")
    cluster_id = _classificar(dados)
    contexto_bm25 = _rag_segmento(cluster_id, pergunta)
    contexto_sync = _rag_graph_sync(cluster_id, pergunta)   # grafo replicado (rápido)
    contexto_graph = _rag_graph(cluster_id, cliente_id, "segmento")  # Neptune live
    contexto = "\n\n".join(filter(None, [contexto_bm25, contexto_sync, contexto_graph]))
    system = _system_segmento(cluster_id)
    resultado = _chamar_claude(system, contexto, pergunta, modo="segmento")
    p = _perfil(cluster_id)
    return json.dumps({
        "cliente_id": cliente_id,
        "cluster_id": cluster_id,
        "segmento": p.get("segmento", ""),
        "modo": "segmento",
        "resposta": resultado,
    }, ensure_ascii=False)



def _atualizar_status(request_id: str, status: str, resultado: str = None, erro: str = None):
    agora = datetime.now(timezone.utc).isoformat()
    expr = "SET #s = :s, atualizado_em = :a"
    attrs = {":s": status, ":a": agora}
    names = {"#s": "status"}
    if resultado is not None:
        expr += ", resultado = :r"
        attrs[":r"] = resultado
    if erro is not None:
        expr += ", erro = :e"
        attrs[":e"] = erro

    _dynamodb.Table(TABLE_NAME).update_item(
        Key={"request_id": request_id},
        UpdateExpression=expr,
        ExpressionAttributeValues=attrs,
        ExpressionAttributeNames=names,
    )


def _notificar(request_id: str, status: str):
    if not SNS_TOPIC_ARN:
        return
    _sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"Agente LangChain: {status}",
        Message=json.dumps({"request_id": request_id, "status": status}),
    )



def lambda_handler(event, context):
    for record in event["Records"]:
        payload = json.loads(record["body"])
        request_id = payload["request_id"]

        _atualizar_status(request_id, "PROCESSING")
        try:
            resultado = _executar(payload)
            _atualizar_status(request_id, "COMPLETED", resultado=resultado)
            _notificar(request_id, "COMPLETED")
        except Exception:
            erro = traceback.format_exc()
            log.error("Erro ao processar request %s:\n%s", request_id, erro)
            _atualizar_status(request_id, "FAILED", erro=erro)
            _notificar(request_id, "FAILED")
            raise
