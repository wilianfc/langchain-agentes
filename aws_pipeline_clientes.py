"""
Pipeline ML + RAG + Agente para Perfis de Clientes — AWS Production
====================================================================

Visão geral
-----------
Combina um pipeline de Machine Learning (segmentação K-Means) com agentes
LangGraph especializados por perfil de cliente. Suporta dois modos de
resposta: agente de segmento (visão gerencial, 3ª pessoa) e digital twin
(simulação do próprio cliente, 1ª pessoa).

Arquitetura
-----------

  Dados de clientes (S3 CSV)
        │
        ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  SageMaker Processing Job  (--mode pipeline)                    │
  │                                                                 │
  │  1. Carregar dados brutos (S3 ou sintéticos)                    │
  │  2. Documento individual por cliente  (dados brutos, sem label) │
  │     →  OpenSearch índice único de twins  (clientes-digital-twins│
  │        filtrado por metadata.cliente_id em tempo de consulta)   │
  │  3. StandardScaler + K-Means  →  N clusters (só estatísticas)   │
  │  4. Athena/Glue Catalog  →  nomes e metadados de segmentos      │
  │     (persona, prompt, produtos definidos pelo time de dados)    │
  │  5. Merge estatísticas + metadados Athena  →  perfis enriquec.  │
  │  6. Documentos de perfil/produtos por cluster                   │
  │     →  OpenSearch índice por cluster  (clientes-segmento-{N})   │
  │  7. KMeans + Scaler + perfis enriquecidos → S3 (clustering.pkl) │
  └─────────────────────────────────────────────────────────────────┘
        │  artefatos persistidos (OpenSearch + S3)
        ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  AWS Lambda — container image  (lambda_handler)                 │
  │                                                                 │
  │  Cold start:                                                    │
  │    · Carrega KMeans + Scaler do S3                              │
  │    · Inicializa agentes por segmento (conecta ao OpenSearch)    │
  │                                                                 │
  │  Por requisição — modo "segmento" (padrão):                     │
  │    1. Classifica cliente  →  cluster_id                         │
  │    2. Recupera RAG do índice do cluster no OpenSearch           │
  │    3. Agente responde em 3ª pessoa ("Este cliente deveria...")  │
  │                                                                 │
  │  Por requisição — modo "twin" (digital twin):                   │
  │    1. Recupera dados individuais do cliente (pre_filter por ID) │
  │    2. Agente responde em 1ª pessoa ("Eu prefiro...", "Para mim")│
  │    NOTA: sem classificação — o twin é independente do clustering│
  └─────────────────────────────────────────────────────────────────┘

Modos de resposta
-----------------
  "segmento" (padrão)
    · Agente representa o gerente do banco falando sobre o cliente
    · RAG: documentos do cluster (perfil médio + produtos + estratégia)
    · Uso: triagem, recomendação de produtos, análise de carteira

  "persona" — arquétipo do segmento
    · Agente é um personagem fictício nomeado que representa o cliente típico do cluster
    · Fala em 1ª pessoa ("Eu, Carlos, gerente de empresa..."), ao contrário do segmento (3ª pessoa)
    · RAG: mesmo índice do cluster — mas com voz e backstory do arquétipo
    · Uso: pesquisa de UX, design de produto, comunicação de marketing,
           testes de copy e jornada de cliente em escala de segmento

  "twin" — digital twin
    · Agente simula o próprio cliente em primeira pessoa
    · RAG: dados individuais do cliente (filtrado por cliente_id no OpenSearch)
    · Perfil comportamental derivado dos dados brutos — sem dependência de clustering
    · Pode ser criado ANTES da clusterização ou sem ela
    · Uso: simulação de reação a ofertas, teste A/B de comunicação,
           predição de aceitação de produtos, personalização extrema

Índices OpenSearch
------------------
  clientes-segmento-{cluster_id}   Um índice por cluster. Documentos:
                                   perfil estatístico, produtos recomendados,
                                   estratégia de abordagem do segmento.

  clientes-digital-twins           Índice único para todos os clientes.
                                   Cada documento contém apenas dados brutos
                                   individuais — sem rótulo de segmento.
                                   Consulta usa pre_filter pelo cliente_id.
                                   Indexado diretamente dos dados brutos,
                                   independentemente da clusterização.

Infraestrutura necessária
--------------------------
  · Amazon Athena + AWS Glue Data Catalog: nomes e metadados de segmentos
  · Amazon OpenSearch Service (managed) ou OpenSearch Serverless
  · Amazon S3: modelo de clustering, dados de entrada e resultados Athena
  · AWS Secrets Manager: chave da Anthropic API
  · IAM Role com permissões:
      athena:StartQueryExecution, athena:GetQueryExecution,
      athena:GetQueryResults     (Athena)
      glue:GetTable, glue:GetDatabase
                                 (Glue Data Catalog — usada pelo Athena)
      es:ESHttp*                 (OpenSearch managed)
      aoss:APIAccessAll          (OpenSearch Serverless)
      s3:GetObject, s3:PutObject, s3:ListBucket
      secretsmanager:GetSecretValue

Variáveis de ambiente
----------------------
  — Athena / Glue Data Catalog —
  ATHENA_DATABASE         Banco de dados no Glue Catalog onde está a tabela de segmentos
                          Ex: banco_clientes
                          Se vazio, nomes de segmento são gerados por heurística local.
  ATHENA_TABLE_SEGMENTOS  Tabela com metadados de segmento (default: segmentos_clientes)
                          Colunas: cluster_id (INT), segmento_nome (VARCHAR),
                          persona_nome, persona_ocupacao, persona_canal,
                          persona_contexto, prompt_segmento, produtos (opcionais)
  ATHENA_WORKGROUP        Workgroup do Athena       (default: primary)
  ATHENA_OUTPUT_BUCKET    Bucket para resultados Athena (default: S3_BUCKET)
  ATHENA_OUTPUT_PREFIX    Prefixo dos resultados Athena (default: athena-results/)

  — OpenSearch —
  OPENSEARCH_ENDPOINT     URL do domínio OpenSearch (sem https://)
  OPENSEARCH_TYPE         "managed" (padrão) | "serverless"
  OPENSEARCH_INDEX_PREFIX Prefixo dos índices de segmento (default: clientes-segmento)
  OPENSEARCH_TWIN_INDEX   Nome do índice de digital twins  (default: clientes-digital-twins)

  — AWS geral —
  AWS_REGION              Região AWS                       (default: us-east-1)
  AWS_ACCOUNT_ID          ID da conta AWS para ExpectedBucketOwner nas chamadas S3
  S3_BUCKET               Bucket de artefatos              (obrigatório em produção)
  S3_PREFIX               Prefixo no bucket                (default: clientes-agente/)
  ANTHROPIC_SECRET_NAME   Nome do secret no Secrets Manager (default: prod/anthropic)
  N_CLUSTERS              Número de segmentos K-Means       (default: 4)
  DATA_SOURCE             "s3" (CSV no S3) | "synthetic"    (default: synthetic)
  S3_DATA_KEY             Chave S3 do CSV de clientes       (ex: data/clientes.csv)

Execução
---------
  SageMaker Processing Job (pipeline completo):
    python aws_pipeline_clientes.py --mode pipeline

    Ordem de execução no pipeline:
      1. Carregar dados brutos (S3 ou sintéticos)
      2. Indexar Digital Twins no OpenSearch (dados brutos, sem clustering)
      3. Executar clustering K-Means → segmentos
      4. Indexar RAG de segmentos no OpenSearch
      5. Salvar modelo de clustering no S3

  Desenvolvimento local (FAISS em memória, sem OpenSearch):
    ANTHROPIC_API_KEY=sk-ant-... python aws_pipeline_clientes.py --mode local

  Lambda — modo segmento:
    {
      "cliente_id": "C12345",
      "dados_cliente": {
        "idade": 35, "renda_mensal": 5000, "saldo_medio": 8000,
        "transacoes_mes": 15, "score_credito": 680, "num_produtos": 3
      },
      "pergunta": "Quais produtos você recomenda para mim?",
      "modo": "segmento"
    }

  Lambda — modo persona (arquétipo do cluster em 1ª pessoa):
    {
      "cluster_id": 2,            ← direto pelo ID, OU
      "dados_cliente": { ... },   ← classifica automaticamente (qualquer um dos dois)
      "pergunta": "O que você acharia deste produto?",
      "modo": "persona"
    }

  Lambda — modo digital twin:
    {
      "cliente_id": "C12345",
      "dados_cliente": { ... },
      "pergunta": "Você aceitaria um cartão com anuidade de R$ 480?",
      "modo": "twin"
    }
    NOTA: dados_cliente são usados apenas para contextualizar o prompt do twin.
    O RAG do twin vem do índice OpenSearch filtrado por cliente_id —
    indexado durante o pipeline a partir dos dados brutos, sem clustering.

Resposta Lambda — modo segmento:
    {
      "statusCode": 200,
      "body": {
        "cliente_id": "C12345",
        "cluster_id": 2,
        "segmento": "Massa Estável",
        "modo": "segmento",
        "resposta": "..."
      }
    }

Resposta Lambda — modo persona:
    {
      "statusCode": 200,
      "body": {
        "cluster_id": 2,
        "segmento": "Massa Estável",
        "persona_nome": "Ana",
        "modo": "persona",
        "resposta": "..."
      }
    }

Resposta Lambda — modo twin:
    {
      "statusCode": 200,
      "body": {
        "cliente_id": "C12345",
        "modo": "twin",
        "resposta": "..."
      }
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import time
import warnings
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS, OpenSearchVectorSearch
from langchain_core.documents import Document
from langchain_core.tools import StructuredTool, tool
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

warnings.filterwarnings("ignore", message=".*create_react_agent.*")

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline-clientes")

# ── Configuração via variáveis de ambiente ─────────────────────────────────────
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
OPENSEARCH_TYPE = os.environ.get("OPENSEARCH_TYPE", "managed")  # "managed" | "serverless"
OPENSEARCH_INDEX_PREFIX = os.environ.get("OPENSEARCH_INDEX_PREFIX", "clientes-segmento")
OPENSEARCH_TWIN_INDEX = os.environ.get("OPENSEARCH_TWIN_INDEX", "clientes-digital-twins")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_PREFIX = os.environ.get("S3_PREFIX", "clientes-agente/")
# AWS_ACCOUNT_ID é usado no parâmetro ExpectedBucketOwner das chamadas S3
# para garantir que o bucket pertence à conta esperada (proteção contra confused deputy).
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "")
ANTHROPIC_SECRET_NAME = os.environ.get("ANTHROPIC_SECRET_NAME", "prod/anthropic")
N_CLUSTERS = int(os.environ.get("N_CLUSTERS", "4"))
DATA_SOURCE = os.environ.get("DATA_SOURCE", "synthetic")
S3_DATA_KEY = os.environ.get("S3_DATA_KEY", "data/clientes.csv")

# ── Athena / Glue Data Catalog ─────────────────────────────────────────────────
# O nome dos segmentos e metadados de persona são lidos do Athena em tempo de
# pipeline (SageMaker job). O Lambda carrega os perfis já enriquecidos do S3 —
# sem dependência de Athena em tempo de execução.
#
# Tabela mínima esperada em {ATHENA_DATABASE}.{ATHENA_TABLE_SEGMENTOS}:
#   cluster_id       INT           -- ID do cluster K-Means
#   segmento_nome    VARCHAR       -- nome curado pelo time de dados (obrigatório)
#   persona_nome     VARCHAR       -- nome do arquétipo (opcional)
#   persona_ocupacao VARCHAR       -- ocupação/descrição da persona (opcional)
#   persona_canal    VARCHAR       -- canal preferencial da persona (opcional)
#   persona_contexto VARCHAR       -- contexto/backstory da persona (opcional)
#   prompt_segmento  VARCHAR       -- system prompt do agente de segmento (opcional)
#   produtos         VARCHAR       -- descrição de produtos recomendados (opcional)
#
# Se ATHENA_DATABASE não for definido, os nomes são derivados por heurística local.
ATHENA_DATABASE = os.environ.get("ATHENA_DATABASE", "")
ATHENA_TABLE_SEGMENTOS = os.environ.get("ATHENA_TABLE_SEGMENTOS", "segmentos_clientes")
ATHENA_WORKGROUP = os.environ.get("ATHENA_WORKGROUP", "primary")
ATHENA_OUTPUT_BUCKET = os.environ.get("ATHENA_OUTPUT_BUCKET", "")
ATHENA_OUTPUT_PREFIX = os.environ.get("ATHENA_OUTPUT_PREFIX", "athena-results/")

# ── Clientes AWS no nível do módulo (S6243: inicializar fora do handler) ───────
# Timeout configurado via variáveis de ambiente padrão do botocore:
#   AWS_DEFAULT_CONNECT_TIMEOUT (default 60 s)
#   AWS_DEFAULT_READ_TIMEOUT    (default 60 s)
# Em produção, defina explicitamente no ambiente Lambda/SageMaker.
_s3_client = boto3.client("s3", region_name=AWS_REGION)  # NOSONAR — timeout via env AWS_DEFAULT_CONNECT/READ_TIMEOUT
_sm_client = boto3.client("secretsmanager", region_name=AWS_REGION)  # NOSONAR
_athena_client = boto3.client("athena", region_name=AWS_REGION)  # NOSONAR

FEATURES = [
    "idade", "renda_mensal", "saldo_medio",
    "transacoes_mes", "score_credito", "num_produtos",
]

# Constantes de nome de segmento — evitam literais duplicados nos dicionários abaixo (S1192)
SEG_PREMIUM = "Premium Conservador"
SEG_JOVEM   = "Jovem Digital"
SEG_RISCO   = "Alto Risco"
SEG_MASSA   = "Massa Estável"

PROMPTS_SEGMENTO: Dict[str, str] = {
    SEG_PREMIUM: (
        "Você é um gerente de relacionamento exclusivo do banco para clientes Premium. "
        "Esses clientes têm alta renda, excelente histórico de crédito e preferem "
        "produtos de investimento de baixo risco e atendimento personalizado. "
        "Seja formal, preciso e ofereça soluções sofisticadas com dados concretos."
    ),
    SEG_JOVEM: (
        "Você atende clientes jovens e altamente digitais do banco. "
        "Eles preferem comunicação direta, produtos via app, cashback e crédito ágil. "
        "Use linguagem leve e destaque praticidade e benefícios digitais."
    ),
    SEG_RISCO: (
        "Você atende clientes com histórico de inadimplência. "
        "Foque em renegociação de dívidas, educação financeira e produtos de baixo limite. "
        "Seja empático, não julgue e apresente caminhos concretos de regularização."
    ),
    SEG_MASSA: (
        "Você atende o público geral e estável do banco. "
        "Esses clientes valorizam segurança e bom custo-benefício. "
        "Foque em fidelização, cross-sell gradual e proteção patrimonial simples."
    ),
}

# Arquétipos nomeados por segmento — usados pelo modo "persona".
# Cada persona é um personagem fictício mas estatisticamente representativo
# do cliente típico do segmento. Diferente do twin (indivíduo real), a persona
# é uma construção de marketing/UX que representa o grupo em 1ª pessoa.
PERSONAS_SEGMENTO: Dict[str, Dict[str, str]] = {
    SEG_PREMIUM: {
        "nome": "Carlos",
        "ocupacao": "gerente de uma empresa de médio porte, 52 anos",
        "canal": "prefiro o atendimento exclusivo com meu gerente de relacionamento",
        "contexto": (
            "Planejei minha aposentadoria com cuidado e tenho patrimônio consolidado. "
            "Priorizo segurança, rentabilidade real acima da inflação e produtos de longo prazo."
        ),
    },
    SEG_JOVEM: {
        "nome": "Júlia",
        "ocupacao": "designer freelancer e criadora de conteúdo, 26 anos",
        "canal": "faço tudo pelo app — nunca precisei ir a uma agência",
        "contexto": (
            "Gosto de movimentação financeira rápida e produtos sem burocracia. "
            "Cashback, rendimento automático e aprovação instantânea são diferenciais importantes para mim."
        ),
    },
    SEG_RISCO: {
        "nome": "Roberto",
        "ocupacao": "motorista autônomo com renda variável, 43 anos",
        "canal": "uso o app para o dia a dia mas prefiro ir à agência para assuntos sérios",
        "contexto": (
            "Passei por um período difícil e acumulei dívidas. "
            "Estou tentando reorganizar minha vida financeira e preciso de orientação concreta e sem julgamentos."
        ),
    },
    SEG_MASSA: {
        "nome": "Ana",
        "ocupacao": "funcionária pública há 12 anos, 38 anos",
        "canal": "uso o internet banking mas às vezes prefiro ir à agência para assuntos importantes",
        "contexto": (
            "Valorizo estabilidade e produtos sem surpresas. "
            "Penso em pequenos investimentos para o futuro da minha família e em proteger o que já conquistei."
        ),
    },
}

PRODUTOS_POR_SEGMENTO: Dict[str, str] = {
    SEG_PREMIUM: (
        "Tesouro Direto IPCA+ e fundos de renda fixa de longo prazo. "
        "Previdência privada PGBL com benefício fiscal. "
        "Cartão Platinum com sala VIP e seguro viagem. "
        "Consultoria de investimentos com gerente dedicado."
    ),
    SEG_JOVEM: (
        "Cartão de crédito com cashback de 2% sem anuidade. "
        "Conta digital com rendimento automático de 100% do CDI. "
        "Crédito pessoal com aprovação em minutos pelo app. "
        "Investimentos a partir de R$ 1 via plataforma digital."
    ),
    SEG_RISCO: (
        "Programa de renegociação com até 90% de desconto nos juros. "
        "Cartão pré-pago sem consulta ao SPC/Serasa. "
        "Microcrédito inicial de R$ 500 com limite crescente. "
        "Curso gratuito de educação financeira no app."
    ),
    SEG_MASSA: (
        "Conta corrente com pacote de tarifas zero. "
        "Previdência VGBL com aportes a partir de R$ 100/mês. "
        "Consórcio imobiliário e de veículos sem juros. "
        "Seguro residencial a partir de R$ 29/mês."
    ),
}


# ══════════════════════════════════════════════════════════════════════════════
# Amazon OpenSearch — autenticação e helpers
# ══════════════════════════════════════════════════════════════════════════════

# Sessão e credenciais no nível do módulo — reutilizadas por _aws_auth()
_boto_session = boto3.session.Session()
_credentials = _boto_session.get_credentials()  # resolve de env, IAM role, etc.


def _aws_auth() -> AWS4Auth:
    """Gera credenciais SigV4 para autenticação no OpenSearch via IAM."""
    frozen = _credentials.get_frozen_credentials()
    # OpenSearch managed → service "es" | OpenSearch Serverless → service "aoss"
    service = "aoss" if OPENSEARCH_TYPE == "serverless" else "es"
    return AWS4Auth(
        frozen.access_key,
        frozen.secret_key,
        AWS_REGION,
        service,
        session_token=frozen.token,
    )


def _opensearch_url() -> str:
    return f"https://{OPENSEARCH_ENDPOINT}"


def _index_name(cluster_id: int) -> str:
    return f"{OPENSEARCH_INDEX_PREFIX}-{cluster_id}"


def criar_indice_opensearch(
    cluster_id: int,
    documentos: List[Document],
    embeddings: HuggingFaceEmbeddings,
) -> OpenSearchVectorSearch:
    """
    Cria (ou recria) um índice OpenSearch para o cluster e indexa os documentos.
    Cada cluster recebe um índice próprio, o que simplifica a recuperação e
    permite atualização independente por segmento.
    """
    index = _index_name(cluster_id)
    auth = _aws_auth()

    # Remove o índice se já existir (re-indexação limpa)
    raw_client = OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )
    if raw_client.indices.exists(index=index):
        raw_client.indices.delete(index=index)
        logger.info("Índice '%s' removido para re-indexação.", index)

    vs = OpenSearchVectorSearch.from_documents(
        documentos,
        embeddings,
        opensearch_url=_opensearch_url(),
        index_name=index,
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        # engine="faiss" também é suportado no OpenSearch k-NN plugin;
        # "lucene" é o padrão gerenciado e não requer configuração extra.
        engine="lucene",
    )
    logger.info(
        "Índice '%s' criado com %d documentos.", index, len(documentos)
    )
    return vs


def carregar_retriever_opensearch(
    cluster_id: int,
    embeddings: HuggingFaceEmbeddings,
    k: int = 3,
) -> VectorStoreRetriever:
    """
    Conecta a um índice OpenSearch existente e retorna um retriever.
    Chamado no Lambda (cold start) — sem transferência de arquivos, apenas
    conexão de rede ao endpoint OpenSearch.
    """
    vs = OpenSearchVectorSearch(
        opensearch_url=_opensearch_url(),
        index_name=_index_name(cluster_id),
        embedding_function=embeddings,
        http_auth=_aws_auth(),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )
    return vs.as_retriever(search_kwargs={"k": k})


# ══════════════════════════════════════════════════════════════════════════════
# AWS S3 — artefatos do modelo de clustering
# ══════════════════════════════════════════════════════════════════════════════

def _s3_key(name: str) -> str:
    return f"{S3_PREFIX}{name}"


def salvar_pkl_s3(obj: Any, name: str) -> None:
    buf = BytesIO()
    pickle.dump(obj, buf)
    buf.seek(0)
    _s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=_s3_key(name),
        Body=buf,
        **( {"ExpectedBucketOwner": AWS_ACCOUNT_ID} if AWS_ACCOUNT_ID else {} ),
    )
    logger.info("Artefato salvo: s3://%s/%s", S3_BUCKET, _s3_key(name))


def carregar_pkl_s3(name: str) -> Any:
    obj = _s3_client.get_object(
        Bucket=S3_BUCKET,
        Key=_s3_key(name),
        **( {"ExpectedBucketOwner": AWS_ACCOUNT_ID} if AWS_ACCOUNT_ID else {} ),
    )
    return pickle.loads(obj["Body"].read())


def get_anthropic_key() -> str:
    resp = _sm_client.get_secret_value(SecretId=ANTHROPIC_SECRET_NAME)
    return json.loads(resp["SecretString"])["ANTHROPIC_API_KEY"]


def carregar_dados_s3() -> pd.DataFrame:
    obj = _s3_client.get_object(
        Bucket=S3_BUCKET,
        Key=S3_DATA_KEY,
        **( {"ExpectedBucketOwner": AWS_ACCOUNT_ID} if AWS_ACCOUNT_ID else {} ),
    )
    return pd.read_csv(BytesIO(obj["Body"].read()))


# ══════════════════════════════════════════════════════════════════════════════
# Athena / Glue Data Catalog — nomes e metadados de segmentos
# ══════════════════════════════════════════════════════════════════════════════

def _coalesce(primary: str, fallback: str) -> str:
    """Retorna `primary` se não vazio após strip, caso contrário `fallback`."""
    return primary.strip() if primary and primary.strip() else fallback


def carregar_segmentos_athena() -> pd.DataFrame:
    """
    Consulta o Athena (via Glue Data Catalog) e retorna os metadados de
    segmentos definidos pelo time de dados.

    O Glue Data Catalog funciona como metastore (schema + localização S3).
    O Athena executa a query SQL sobre os dados em Parquet/ORC no S3.

    Colunas mínimas obrigatórias na tabela:
      cluster_id       INT     — ID do cluster K-Means
      segmento_nome    VARCHAR — nome curado pelo time de dados

    Colunas opcionais (preenchidas com fallback local se ausentes):
      persona_nome, persona_ocupacao, persona_canal, persona_contexto,
      prompt_segmento, produtos

    Retorna DataFrame vazio se ATHENA_DATABASE não está configurado.
    A função é chamada apenas no SageMaker Processing Job; o Lambda carrega
    os perfis já enriquecidos do S3, sem dependência de Athena em runtime.
    """
    output_loc = f"s3://{ATHENA_OUTPUT_BUCKET}/{ATHENA_OUTPUT_PREFIX}"
    query = f"""
        SELECT
            CAST(cluster_id AS INTEGER)              AS cluster_id,
            TRIM(segmento_nome)                      AS segmento_nome,
            COALESCE(TRIM(persona_nome),     '')     AS persona_nome,
            COALESCE(TRIM(persona_ocupacao), '')     AS persona_ocupacao,
            COALESCE(TRIM(persona_canal),    '')     AS persona_canal,
            COALESCE(TRIM(persona_contexto), '')     AS persona_contexto,
            COALESCE(TRIM(prompt_segmento),  '')     AS prompt_segmento,
            COALESCE(TRIM(produtos),         '')     AS produtos
        FROM {ATHENA_DATABASE}.{ATHENA_TABLE_SEGMENTOS}
        ORDER BY cluster_id
    """
    resp = _athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": ATHENA_DATABASE},
        WorkGroup=ATHENA_WORKGROUP,
        ResultConfiguration={"OutputLocation": output_loc},
    )
    exec_id = resp["QueryExecutionId"]
    logger.info("Athena query iniciada: %s", exec_id)

    # Polling com backoff exponencial (máx ~60 s)
    wait = 1
    for _ in range(30):
        status_resp = _athena_client.get_query_execution(QueryExecutionId=exec_id)
        state = status_resp["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in ("FAILED", "CANCELLED"):
            reason = status_resp["QueryExecution"]["Status"].get("StateChangeReason", "")
            raise RuntimeError(f"Athena query {state}: {reason}")
        time.sleep(wait)
        wait = min(wait * 2, 8)
    else:
        raise TimeoutError(f"Athena query não concluiu em tempo hábil: {exec_id}")

    # Coleta resultados paginados
    rows: List[Dict] = []
    kwargs: Dict[str, Any] = {"QueryExecutionId": exec_id, "MaxResults": 1000}
    while True:
        page = _athena_client.get_query_results(**kwargs)
        rows.extend(page["ResultSet"]["Rows"])
        next_token = page.get("NextToken")
        if not next_token:
            break
        kwargs["NextToken"] = next_token

    if len(rows) <= 1:
        logger.warning(
            "Athena retornou 0 linhas — verificar tabela %s.%s",
            ATHENA_DATABASE, ATHENA_TABLE_SEGMENTOS,
        )
        return pd.DataFrame()

    columns = [col["VarCharValue"] for col in rows[0]["Data"]]
    data = [[c.get("VarCharValue", "") for c in row["Data"]] for row in rows[1:]]
    df = pd.DataFrame(data, columns=columns)
    df["cluster_id"] = pd.to_numeric(df["cluster_id"], errors="coerce").astype("Int64")
    logger.info(
        "Segmentos carregados do Athena (%s.%s): %d clusters.",
        ATHENA_DATABASE, ATHENA_TABLE_SEGMENTOS, len(df),
    )
    return df


def _enriquecer_perfis(
    perfis: pd.DataFrame,
    seg_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Enriquece o DataFrame de estatísticas K-Means com nomes de segmento,
    prompts e metadados de persona.

    Fonte primária — Athena/Glue Catalog (`seg_df`):
      Os nomes são definidos pelo time de dados e podem variar livremente
      (ex: "Empreendedor Emergente", "Aposentado Conservador"). O código
      não assume nenhum vocabulário fixo de segmentos.

    Fonte secundária — fallback local:
      Quando `seg_df` é None ou não cobre um cluster, aplica a heurística
      `_nomear_segmento` e usa os dicts PERSONAS/PROMPTS/PRODUTOS como
      defaults de conteúdo.

    Colunas adicionadas ao DataFrame retornado:
      segmento, persona_nome, persona_ocupacao, persona_canal,
      persona_contexto, prompt_segmento, produtos
    """
    perfis = perfis.copy()
    seg_idx = (
        seg_df.set_index("cluster_id")
        if seg_df is not None and not seg_df.empty
        else None
    )

    for cid in perfis.index:
        athena = seg_idx.loc[cid] if seg_idx is not None and cid in seg_idx.index else pd.Series(dtype=str)

        # Nome do segmento: Athena é fonte primária
        segmento = _coalesce(str(athena.get("segmento_nome", "")), _nomear_segmento(perfis.loc[cid]))
        perfis.loc[cid, "segmento"] = segmento

        # Fallbacks locais baseados no nome do segmento (para conteúdo de prompt/persona)
        p_fallback = PERSONAS_SEGMENTO.get(segmento, {})

        perfis.loc[cid, "persona_nome"]     = _coalesce(str(athena.get("persona_nome",     "")), p_fallback.get("nome",     f"Cliente {cid}"))
        perfis.loc[cid, "persona_ocupacao"] = _coalesce(str(athena.get("persona_ocupacao", "")), p_fallback.get("ocupacao", "profissional"))
        perfis.loc[cid, "persona_canal"]    = _coalesce(str(athena.get("persona_canal",    "")), p_fallback.get("canal",    "uso os canais do banco"))
        perfis.loc[cid, "persona_contexto"] = _coalesce(str(athena.get("persona_contexto", "")), p_fallback.get("contexto", ""))
        perfis.loc[cid, "prompt_segmento"]  = _coalesce(str(athena.get("prompt_segmento",  "")), PROMPTS_SEGMENTO.get(segmento,         ""))
        perfis.loc[cid, "produtos"]         = _coalesce(str(athena.get("produtos",         "")), PRODUTOS_POR_SEGMENTO.get(segmento,    ""))

    source = f"Athena ({ATHENA_DATABASE}.{ATHENA_TABLE_SEGMENTOS})" if seg_idx is not None else "heurística local"
    logger.info("Perfis enriquecidos via %s: %d segmentos.", source, len(perfis))
    return perfis


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline ML
# ══════════════════════════════════════════════════════════════════════════════

def gerar_dados_sinteticos(n: int = 1_000) -> pd.DataFrame:
    rng = np.random.default_rng(42)  # numpy.random.Generator (S6711)
    return pd.DataFrame({
        "cliente_id":     [f"C{i:05d}" for i in range(n)],
        "idade":          rng.integers(18, 75, n),
        "renda_mensal":   rng.exponential(5_000, n).clip(800, 50_000),
        "saldo_medio":    rng.exponential(12_000, n).clip(0, 200_000),
        "transacoes_mes": rng.poisson(18, n),
        "score_credito":  rng.normal(650, 120, n).clip(300, 1_000),
        "num_produtos":   rng.integers(1, 8, n),
        "inadimplente":   rng.choice([0, 1], n, p=[0.87, 0.13]),
        "canal_digital":  rng.choice([0, 1], n, p=[0.35, 0.65]),
    })


def _nomear_segmento(row: pd.Series) -> str:
    if row["renda_media"] > 10_000 and row["score_medio"] > 700:
        return SEG_PREMIUM
    if row["idade_media"] < 35 and row["digital"] > 0.65:
        return SEG_JOVEM
    if row["inadimplencia"] > 0.18:
        return SEG_RISCO
    return SEG_MASSA


def executar_clustering(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, KMeans, StandardScaler, pd.DataFrame]:
    scaler = StandardScaler()
    X = scaler.fit_transform(df[FEATURES])

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    df = df.copy()
    df["cluster"] = kmeans.fit_predict(X)

    perfis = (
        df.groupby("cluster")
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
        .round(2)
    )
    # Nomes de segmento NÃO são atribuídos aqui.
    # _enriquecer_perfis() adiciona a coluna "segmento" a partir do Athena/Glue
    # Catalog (fonte primária) ou por heurística local (fallback).
    logger.info("Clustering concluído: %d clusters, %d clientes.", N_CLUSTERS, len(df))
    return df, kmeans, scaler, perfis


def _gerar_docs_cluster(cluster_id: int, perfil: pd.Series) -> List[Document]:
    """
    Gera os documentos RAG de um cluster a partir do perfil enriquecido.

    Usa as colunas `produtos` e `prompt_segmento` do DataFrame — que vêm do
    Athena/Glue Catalog (se disponível) ou dos dicts de fallback local.
    Não faz lookup direto em PRODUTOS_POR_SEGMENTO/PROMPTS_SEGMENTO.
    """
    seg = perfil["segmento"]
    produtos = str(perfil.get("produtos", ""))
    estrategia = str(perfil.get("prompt_segmento", ""))
    return [
        Document(
            page_content=(
                f"Perfil '{seg}' (Cluster {cluster_id}): "
                f"{perfil['n']:.0f} clientes, idade média {perfil['idade_media']:.0f} anos, "
                f"renda R$ {perfil['renda_media']:,.0f}/mês, saldo R$ {perfil['saldo_medio_']:,.0f}, "
                f"score {perfil['score_medio']:.0f}, "
                f"inadimplência {perfil['inadimplencia'] * 100:.1f}%, "
                f"uso digital {perfil['digital'] * 100:.0f}%."
            ),
            metadata={"cluster": cluster_id, "segmento": seg, "tipo": "perfil"},
        ),
        Document(
            page_content=f"Produtos para '{seg}': {produtos}",
            metadata={"cluster": cluster_id, "segmento": seg, "tipo": "produtos"},
        ),
        Document(
            page_content=f"Estratégia para '{seg}': {estrategia}",
            metadata={"cluster": cluster_id, "segmento": seg, "tipo": "estrategia"},
        ),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Digital Twins — indexação e agente por cliente individual
# ══════════════════════════════════════════════════════════════════════════════

def _doc_twin(row: pd.Series) -> Document:
    """
    Cria o Document individual de um cliente para indexação no twin index.

    Contém apenas dados brutos do cliente — sem rótulos derivados de clustering.
    O twin representa o indivíduo diretamente, não o grupo ao qual pertence.
    """
    canal = "digital (app/internet)" if row.get("canal_digital") else "agência física"
    historico = (
        "possui histórico de inadimplência — em processo de regularização"
        if row.get("inadimplente") else "adimplente, sem pendências"
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
        metadata={
            "cliente_id": str(row["cliente_id"]),
            "tipo": "twin",
        },
    )


def _prompt_twin(row: pd.Series) -> str:
    """
    Gera o system prompt que coloca o agente no papel do cliente.

    O perfil comportamental é derivado diretamente dos dados brutos do cliente,
    sem depender de rótulos de clustering. O twin é independente do pipeline
    de segmentação — pode ser criado antes ou sem clusterização.
    """
    canal = (
        "prefiro usar aplicativo e internet banking"
        if row.get("canal_digital") else "prefiro atendimento presencial na agência"
    )
    financeiro = (
        "estou reestruturando minhas finanças após um período de inadimplência"
        if row.get("inadimplente") else "mantenho histórico financeiro limpo"
    )
    renda = float(row.get("renda_mensal", 0))
    score = float(row.get("score_credito", 0))
    idade = float(row.get("idade", 30))
    digital = bool(row.get("canal_digital", False))

    if renda > 10_000 and score > 700:
        perfil_desc = (
            "Tenho alta renda e excelente histórico de crédito. "
            "Valorizo produtos sofisticados, investimentos de longo prazo e atendimento exclusivo."
        )
    elif idade < 35 and digital:
        perfil_desc = (
            "Sou jovem e muito conectado digitalmente. "
            "Valorizo praticidade, cashback, aprovações rápidas e tudo pelo app."
        )
    elif score < 450:
        perfil_desc = (
            "Estou em processo de recuperação financeira. "
            "Preciso de soluções acessíveis, sem burocracia, e orientação sobre como regularizar minha situação."
        )
    else:
        perfil_desc = (
            "Valorizo segurança e bom custo-benefício. "
            "Sou um cliente fiel que prefere produtos confiáveis sem surpresas."
        )

    return (
        f"Você é o gêmeo digital (digital twin) do cliente {row['cliente_id']}. "
        f"Simule EXATAMENTE como este cliente pensaria, reagiria e tomaria "
        f"decisões financeiras com base no seu perfil real:\n\n"
        f"  Idade: {row['idade']:.0f} anos | Renda: R$ {row['renda_mensal']:,.0f}/mês\n"
        f"  Saldo: R$ {row['saldo_medio']:,.0f} | Score: {row['score_credito']:.0f}\n"
        f"  Produtos: {row['num_produtos']:.0f} | Canal: {canal}\n"
        f"  Situação: {financeiro}\n\n"
        f"Perfil comportamental (derivado dos dados brutos): {perfil_desc}\n\n"
        f"REGRAS ABSOLUTAS:\n"
        f"- Responda SEMPRE em primeira pessoa ('Eu prefiro...', 'Para mim...', 'Eu aceitaria se...')\n"
        f"- Seja coerente com a realidade financeira deste perfil\n"
        f"- Não quebre o personagem — você É este cliente"
    )


def indexar_digital_twins(
    df: pd.DataFrame,
    embeddings: HuggingFaceEmbeddings,
) -> None:
    """
    Indexa todos os clientes no índice de digital twins do OpenSearch.

    Estratégia: índice único `OPENSEARCH_TWIN_INDEX` com metadado `cliente_id`.
    Na consulta, usa pre_filter por `cliente_id` para recuperar apenas os
    documentos do cliente específico — sem criar um índice por cliente.

    Os documentos contêm apenas dados brutos individuais, sem rótulo de
    segmento. O twin é independente da clusterização e pode ser indexado
    antes ou sem o pipeline de segmentação K-Means.

    Executado como parte do SageMaker Processing Job.
    """
    auth = _aws_auth()
    raw_client = OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )
    # Recria o índice para re-indexação limpa
    if raw_client.indices.exists(index=OPENSEARCH_TWIN_INDEX):
        raw_client.indices.delete(index=OPENSEARCH_TWIN_INDEX)

    docs = [_doc_twin(row) for _, row in df.iterrows()]

    # Indexa em lote (OpenSearch suporta bulk insert)
    OpenSearchVectorSearch.from_documents(
        docs,
        embeddings,
        opensearch_url=_opensearch_url(),
        index_name=OPENSEARCH_TWIN_INDEX,
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        engine="lucene",
    )
    logger.info(
        "Digital Twins indexados: %d clientes no índice '%s'.",
        len(docs), OPENSEARCH_TWIN_INDEX,
    )


def _retriever_twin_opensearch(
    cliente_id: str,
    embeddings: HuggingFaceEmbeddings,
) -> VectorStoreRetriever:
    """
    Retorna um retriever que filtra por `cliente_id` no índice de twins.
    Usa `pre_filter` do OpenSearch para restringir a busca ao cliente específico.
    """
    vs = OpenSearchVectorSearch(
        opensearch_url=_opensearch_url(),
        index_name=OPENSEARCH_TWIN_INDEX,
        embedding_function=embeddings,
        http_auth=_aws_auth(),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )
    return vs.as_retriever(
        search_kwargs={
            "k": 3,
            "pre_filter": {"term": {"metadata.cliente_id": cliente_id}},
        }
    )


def criar_twin_sob_demanda(
    cliente_id: str,
    dados_cliente: Dict[str, Any],
    embeddings: HuggingFaceEmbeddings,
    model: ChatAnthropic,
) -> Any:
    """
    Cria um agente digital twin para um cliente específico sob demanda.

    O twin é gerado exclusivamente a partir dos dados individuais do cliente:
      - retriever_individual: filtra o índice OpenSearch pelo cliente_id
      - prompt: derivado dos dados brutos (renda, score, canal, histórico)

    Não requer clustering — o twin representa o indivíduo diretamente.
    O perfil comportamental é inferido dos dados brutos, não de um rótulo
    de segmento. Isso permite criar o twin antes ou sem o pipeline K-Means.

    Padrão de uso no Lambda: instancie por requisição ou cache por cliente_id.
    """
    retriever_individual = _retriever_twin_opensearch(cliente_id, embeddings)

    def _meus_dados(consulta: str) -> str:
        """Acessa os dados pessoais e histórico financeiro deste cliente."""
        return "\n\n".join(d.page_content for d in retriever_individual.invoke(consulta))

    meus_dados_tool = StructuredTool.from_function(
        func=_meus_dados,
        name="meus_dados_individuais",
        description="Dados pessoais e histórico financeiro deste cliente.",
    )

    @tool
    def calcular(expressao: str) -> str:
        """Calcula parcelas, juros e comprometimento de renda."""
        try:
            return str(round(eval(expressao, {"__builtins__": {}}), 2))
        except Exception as exc:
            return f"Erro: {exc}"

    row = pd.Series({**dados_cliente, "cliente_id": cliente_id})
    return create_react_agent(
        model,
        [meus_dados_tool, calcular],
        checkpointer=MemorySaver(),
        prompt=_prompt_twin(row),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Persona — arquétipo nomeado por cluster (1ª pessoa, grupo)
# ══════════════════════════════════════════════════════════════════════════════

def _prompt_persona(cluster_id: int, perfil: pd.Series) -> str:
    """
    Gera o system prompt para o agente persona de um cluster.

    O persona é um arquétipo nomeado que representa o cliente típico do segmento.
    Diferente do twin (indivíduo real com dados brutos), o persona é uma
    construção estatisticamente representativa do grupo — útil para pesquisa
    de UX, design de produto e testes de comunicação em escala de segmento.

    Diferente do agente de segmento (3ª pessoa gerencial), o persona fala
    em 1ª pessoa como um membro típico do cluster.
    """
    seg = perfil["segmento"]
    # Lê da coluna do perfil enriquecido (Athena ou fallback local).
    # Não faz lookup direto em PERSONAS_SEGMENTO pelo nome do segmento,
    # pois o nome pode ser qualquer string definida no Glue Catalog.
    nome     = str(perfil.get("persona_nome",     f"Cliente do Cluster {cluster_id}"))
    ocupacao = str(perfil.get("persona_ocupacao", "profissional"))
    canal    = str(perfil.get("persona_canal",    "uso os canais disponíveis do banco"))
    contexto = str(perfil.get("persona_contexto", ""))

    renda = float(perfil["renda_media"])
    score = float(perfil["score_medio"])
    idade = int(perfil["idade_media"])

    return (
        f"Você é {nome}, {ocupacao}. "
        f"Você representa o cliente típico do segmento '{seg}' do banco.\n\n"
        f"Perfil financeiro médio do seu grupo:\n"
        f"  Renda: R$ {renda:,.0f}/mês | Score: {score:.0f} | Idade média: {idade} anos\n"
        f"  Canal: {canal}\n\n"
        f"Contexto pessoal: {contexto}\n\n"
        f"REGRAS:\n"
        f"- Responda SEMPRE em 1ª pessoa, como {nome}\n"
        f"- Você é um arquétipo do segmento '{seg}' — não um cliente específico real\n"
        f"- Suas opiniões devem refletir o que a maioria dos clientes deste grupo sentiria\n"
        f"- Seja autêntico ao perfil estatístico do segmento\n"
        f"- Não quebre o personagem — você É {nome}"
    )


def _criar_agente_persona(
    cluster_id: int,
    perfil: pd.Series,
    retriever: VectorStoreRetriever,
    model: ChatAnthropic,
):
    """
    Fábrica — cria agente persona para um cluster.

    Reutiliza o mesmo RAG do agente de segmento (índice do cluster),
    mas com prompt em 1ª pessoa como arquétipo nomeado do grupo.
    Isolamento de closure garantido pelo parâmetro `cluster_id`.
    """
    def _buscar(consulta: str) -> str:
        """Busca informações sobre produtos e estratégia do meu segmento."""
        return "\n\n".join(d.page_content for d in retriever.invoke(consulta))

    buscar_perfil = StructuredTool.from_function(
        func=_buscar,
        name="buscar_info_segmento",
        description="Busca produtos, perfil e estratégia disponíveis para o meu segmento.",
    )

    @tool
    def calcular(expressao: str) -> str:
        """Calcula parcelas, juros e comprometimento de renda."""
        try:
            return str(round(eval(expressao, {"__builtins__": {}}), 2))
        except Exception as exc:
            return f"Erro: {exc}"

    return create_react_agent(
        model,
        [buscar_perfil, calcular],
        checkpointer=MemorySaver(),
        prompt=_prompt_persona(cluster_id, perfil),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Inferência: agente por segmento
# ══════════════════════════════════════════════════════════════════════════════

def _criar_agente(
    segmento: str,
    retriever: VectorStoreRetriever,
    model: ChatAnthropic,
    prompt: str = "",
):
    """
    Fábrica — cria agente de segmento (3ª pessoa gerencial).

    O `prompt` vem da coluna `prompt_segmento` do perfil enriquecido
    (Athena ou fallback local). O parâmetro `segmento` é mantido para
    identificação em logs; o conteúdo do prompt não é derivado do nome.
    """
    def _buscar(consulta: str) -> str:
        """Busca perfil, produtos e estratégia do segmento do cliente."""
        return "\n\n".join(d.page_content for d in retriever.invoke(consulta))

    buscar_perfil = StructuredTool.from_function(
        func=_buscar,
        name="buscar_perfil_segmento",
        description="Busca perfil, produtos recomendados e estratégia do segmento.",
    )

    @tool
    def calcular(expressao: str) -> str:
        """Calcula valores financeiros: juros, parcelas, totais."""
        try:
            return str(round(eval(expressao, {"__builtins__": {}}), 2))
        except Exception as exc:
            return f"Erro: {exc}"

    system_prompt = prompt or PROMPTS_SEGMENTO.get(segmento, "")
    return create_react_agent(
        model,
        [buscar_perfil, calcular],
        checkpointer=MemorySaver(),
        prompt=system_prompt,
    )


class PipelineInference:
    """
    Encapsula clustering + agentes por segmento.

    No Lambda:
      - Cold start: carrega KMeans/Scaler do S3, conecta ao OpenSearch
      - Warm start: reutiliza esta instância em memória
      - O RAG é servido pelo OpenSearch — sem carregar índices localmente
    """

    def __init__(
        self,
        kmeans: KMeans,
        scaler: StandardScaler,
        perfis: pd.DataFrame,
        embeddings: HuggingFaceEmbeddings,
        api_key: str,
        use_opensearch: bool = True,
        vector_stores_local: Optional[Dict[int, FAISS]] = None,
    ) -> None:
        self.kmeans = kmeans
        self.scaler = scaler
        self.perfis = perfis
        self._embeddings = embeddings
        self.model = ChatAnthropic(
            model="claude-sonnet-4-6",
            temperature=0,
            anthropic_api_key=api_key,
        )
        self._agentes = self._inicializar_agentes(
            embeddings, use_opensearch, vector_stores_local
        )

    def _inicializar_agentes(
        self,
        embeddings: HuggingFaceEmbeddings,
        use_opensearch: bool,
        local_stores: Optional[Dict[int, FAISS]],
    ) -> Dict[int, Dict[str, Any]]:
        agentes: Dict[int, Dict[str, Any]] = {}
        for cid in self.perfis.index:
            perfil = self.perfis.loc[cid]
            segmento = perfil["segmento"]
            if use_opensearch:
                retriever = carregar_retriever_opensearch(int(cid), embeddings)
            else:
                retriever = local_stores[cid].as_retriever(search_kwargs={"k": 3})

            agentes[cid] = {
                "segmento": segmento,
                # Modo segmento: 3ª pessoa gerencial — prompt vem do perfil enriquecido
                "agente": _criar_agente(segmento, retriever, self.model,
                                        prompt=str(perfil.get("prompt_segmento", ""))),
                # Modo persona: 1ª pessoa como arquétipo — nome/ocupação/contexto do perfil
                "persona": _criar_agente_persona(int(cid), perfil, retriever, self.model),
                # Nome do arquétipo para incluir na resposta (coluna do perfil enriquecido)
                "persona_nome": str(perfil.get("persona_nome", f"Cluster {cid}")),
            }
            logger.info(
                "Agentes prontos: cluster %d — %s (segmento + persona '%s')",
                cid, segmento, agentes[cid]["persona_nome"],
            )
        return agentes

    def classificar(self, dados: Dict[str, float]) -> int:
        X = self.scaler.transform([[
            dados["idade"], dados["renda_mensal"], dados["saldo_medio"],
            dados["transacoes_mes"], dados["score_credito"], dados["num_produtos"],
        ]])
        return int(self.kmeans.predict(X)[0])

    def responder(
        self,
        cliente_id: str,
        dados_cliente: Dict[str, float],
        pergunta: str,
    ) -> Dict[str, Any]:
        cluster_id = self.classificar(dados_cliente)
        info = self._agentes[cluster_id]
        config = {"configurable": {"thread_id": f"cliente-{cliente_id}"}}
        resultado = info["agente"].invoke(
            {"messages": [{"role": "user", "content": pergunta}]},
            config=config,
        )
        return {
            "cliente_id": cliente_id,
            "cluster_id": cluster_id,
            "segmento": info["segmento"],
            "modo": "segmento",
            "resposta": resultado["messages"][-1].content,
        }

    def responder_como_persona(
        self,
        pergunta: str,
        cluster_id: Optional[int] = None,
        dados_cliente: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Responde em 1ª pessoa como o arquétipo nomeado do cluster.

        O cluster pode ser fornecido diretamente (`cluster_id`) ou inferido
        automaticamente a partir de `dados_cliente` via K-Means.
        Pelo menos um dos dois deve ser fornecido.

        Diferença em relação aos outros modos:
          - segmento → 3ª pessoa gerencial (sobre o cliente)
          - persona  → 1ª pessoa como arquétipo do grupo (Carlos, Júlia, etc.)
          - twin     → 1ª pessoa como indivíduo real (sem clustering)
        """
        if cluster_id is None:
            if dados_cliente is None:
                raise ValueError("Forneça 'cluster_id' ou 'dados_cliente'.")
            cluster_id = self.classificar(dados_cliente)

        info = self._agentes[cluster_id]
        config = {"configurable": {"thread_id": f"persona-{cluster_id}"}}
        resultado = info["persona"].invoke(
            {"messages": [{"role": "user", "content": pergunta}]},
            config=config,
        )
        return {
            "cluster_id": cluster_id,
            "segmento": info["segmento"],
            "persona_nome": info["persona_nome"],
            "modo": "persona",
            "resposta": resultado["messages"][-1].content,
        }

    def responder_como_twin(
        self,
        cliente_id: str,
        dados_cliente: Dict[str, float],
        pergunta: str,
    ) -> Dict[str, Any]:
        """
        Cria um digital twin do cliente e responde em primeira pessoa.

        O twin é gerado exclusivamente dos dados individuais — sem classificação
        por segmento. O perfil comportamental é derivado dos dados brutos
        (renda, score, canal, histórico) e o RAG recupera o documento do cliente
        no índice OpenSearch filtrado por cliente_id.

        Independente de clustering: funciona antes ou sem o pipeline K-Means.
        Para uso intensivo, implemente cache LRU ou ElastiCache por cliente_id.
        """
        agente_twin = criar_twin_sob_demanda(
            cliente_id=cliente_id,
            dados_cliente=dados_cliente,
            embeddings=self._embeddings,
            model=self.model,
        )
        config = {"configurable": {"thread_id": f"twin-{cliente_id}"}}
        resultado = agente_twin.invoke(
            {"messages": [{"role": "user", "content": pergunta}]},
            config=config,
        )
        return {
            "cliente_id": cliente_id,
            "modo": "twin",
            "resposta": resultado["messages"][-1].content,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Modo pipeline — SageMaker Processing Job
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline() -> Tuple[KMeans, StandardScaler, pd.DataFrame, Optional[Dict]]:
    """
    Pipeline completo em ordem lógica:

      1. Carregar dados brutos (S3 ou sintéticos)
      2. Indexar Digital Twins no OpenSearch — dados brutos, independente de clustering
      3. Executar clustering K-Means → estatísticas por cluster (sem nomear segmentos)
      4. Enriquecer perfis com nomes e metadados do Athena/Glue Catalog
         → fallback: heurística local se ATHENA_DATABASE não configurado
      5. Indexar RAG de segmentos no OpenSearch (usa nomes vindos do Athena)
      6. Persistir perfis enriquecidos + modelo K-Means no S3
         → o Lambda carrega este artefato no cold start, sem chamar Athena

    Separação de responsabilidades:
      - Nomes de segmento  → Athena/Glue Catalog (domínio do time de dados)
      - Estatísticas       → K-Means (domínio do pipeline ML)
      - Twins              → dados brutos individuais (sem clustering)
    """
    logger.info("=== Iniciando pipeline ML + RAG ===")

    df = carregar_dados_s3() if DATA_SOURCE == "s3" else gerar_dados_sinteticos(1_000)
    logger.info("Dados: %d clientes.", len(df))

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=40)
    use_opensearch = bool(OPENSEARCH_ENDPOINT)

    # ── Etapa 1: Digital Twins — dados brutos, antes e independente do clustering ──
    if use_opensearch:
        logger.info("Indexando digital twins (dados brutos, pré-clustering)...")
        indexar_digital_twins(df, embeddings)

    # ── Etapa 2: Clustering K-Means — retorna apenas estatísticas ────────────
    df, kmeans, scaler, perfis = executar_clustering(df)

    # ── Etapa 3: Nomes e metadados de segmento via Athena/Glue Catalog ───────
    if ATHENA_DATABASE:
        try:
            seg_df = carregar_segmentos_athena()
            perfis = _enriquecer_perfis(perfis, seg_df)
        except Exception:
            logger.warning(
                "Falha ao carregar segmentos do Athena — usando heurística local.",
                exc_info=True,
            )
            perfis = _enriquecer_perfis(perfis)
    else:
        logger.info("ATHENA_DATABASE não configurado — nomes de segmento por heurística local.")
        perfis = _enriquecer_perfis(perfis)

    logger.info("Segmentos:\n%s", perfis[["segmento", "n"]].to_string())

    # ── Etapa 4: Índices RAG por segmento no OpenSearch ──────────────────────
    local_stores: Dict[int, FAISS] = {}
    for cid in perfis.index:
        docs = _gerar_docs_cluster(cid, perfis.loc[cid])
        chunks = splitter.split_documents(docs)

        if use_opensearch:
            criar_indice_opensearch(cid, chunks, embeddings)
        else:
            local_stores[cid] = FAISS.from_documents(chunks, embeddings)
            logger.info(
                "FAISS local cluster %d (%s) — %d chunks.",
                cid, perfis.loc[cid, "segmento"], len(chunks),
            )

    # ── Etapa 5: Persistir perfis enriquecidos + modelo K-Means no S3 ────────
    # O Lambda carrega este artefato no cold start — sem dependência de Athena.
    if S3_BUCKET:
        salvar_pkl_s3(
            {"kmeans": kmeans, "scaler": scaler, "perfis": perfis.to_dict()},
            "modelo_clustering.pkl",
        )

    logger.info("=== Pipeline concluído ===")
    return kmeans, scaler, perfis, (local_stores if not use_opensearch else None)


# ══════════════════════════════════════════════════════════════════════════════
# Lambda handler
# ══════════════════════════════════════════════════════════════════════════════

_pipeline_instance: Optional[PipelineInference] = None


def _get_pipeline() -> PipelineInference:
    """Singleton: cold start carrega do S3/OpenSearch; warm start reutiliza."""
    global _pipeline_instance
    if _pipeline_instance is not None:
        return _pipeline_instance

    logger.info("Cold start: inicializando pipeline...")

    artefatos = carregar_pkl_s3("modelo_clustering.pkl")
    kmeans: KMeans = artefatos["kmeans"]
    scaler: StandardScaler = artefatos["scaler"]
    perfis = pd.DataFrame(artefatos["perfis"])

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    api_key = get_anthropic_key()

    # O retriever conecta ao OpenSearch — sem carregar índices localmente
    _pipeline_instance = PipelineInference(
        kmeans, scaler, perfis, embeddings, api_key, use_opensearch=True
    )
    logger.info("Pipeline pronto.")
    return _pipeline_instance


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Entry point AWS Lambda.

    Entrada — modo segmento (padrão):
      {
        "cliente_id": "C12345",
        "dados_cliente": {"idade": 35, "renda_mensal": 5000, "saldo_medio": 8000,
                          "transacoes_mes": 15, "score_credito": 680, "num_produtos": 3},
        "pergunta": "Quais produtos você recomenda para mim?",
        "modo": "segmento"   ← opcional, default
      }

    Entrada — modo persona (arquétipo do cluster em 1ª pessoa):
      {
        "cluster_id": 2,            ← direto pelo ID do cluster, OU
        "dados_cliente": { ... },   ← classifica automaticamente (qualquer um dos dois)
        "pergunta": "O que você acha deste produto?",
        "modo": "persona"
      }

    Entrada — modo digital twin:
      {
        "cliente_id": "C12345",
        "dados_cliente": { ... },
        "pergunta": "Você aceitaria este cartão de crédito?",
        "modo": "twin"       ← agente fala em 1ª pessoa como o cliente
      }
    """
    try:
        pipeline = _get_pipeline()

        pergunta: str = event["pergunta"]
        modo: str = event.get("modo", "segmento")

        if modo == "persona":
            cluster_id = event.get("cluster_id")
            dados = event.get("dados_cliente")
            if cluster_id is None and dados is None:
                raise KeyError("Modo 'persona' requer 'cluster_id' ou 'dados_cliente'.")
            resultado = pipeline.responder_como_persona(
                pergunta,
                cluster_id=int(cluster_id) if cluster_id is not None else None,
                dados_cliente=dados,
            )
        else:
            cliente_id: str = event["cliente_id"]
            dados: Dict[str, float] = event["dados_cliente"]
            ausentes = set(FEATURES) - set(dados.keys())
            if ausentes:
                raise KeyError(f"Campos ausentes em dados_cliente: {ausentes}")

            if modo == "twin":
                resultado = pipeline.responder_como_twin(cliente_id, dados, pergunta)
            else:
                resultado = pipeline.responder(cliente_id, dados, pergunta)

        return {"statusCode": 200, "body": json.dumps(resultado, ensure_ascii=False)}

    except KeyError as exc:
        logger.error("Campo obrigatório ausente: %s", exc)
        return {"statusCode": 400, "body": json.dumps({"erro": str(exc)})}
    except Exception:
        logger.exception("Erro inesperado.")
        return {"statusCode": 500, "body": json.dumps({"erro": "Erro interno."})}


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["pipeline", "local"],
        default="local",
        help=(
            "pipeline: clustering + indexação no OpenSearch + S3 (SageMaker). "
            "local: pipeline com FAISS em memória + consultas de teste."
        ),
    )
    args = parser.parse_args()

    if args.mode == "pipeline":
        run_pipeline()

    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError("Defina ANTHROPIC_API_KEY para o modo local.")

        kmeans, scaler, perfis, local_stores = run_pipeline()
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        inference = PipelineInference(
            kmeans, scaler, perfis, embeddings, api_key,
            use_opensearch=False,          # local: FAISS em memória
            vector_stores_local=local_stores,
        )

        clientes_teste = [
            {"id": "C001", "label": "Alta renda, conservador",
             "dados": {"idade": 54, "renda_mensal": 22_000, "saldo_medio": 95_000,
                       "transacoes_mes": 10, "score_credito": 840, "num_produtos": 6}},
            {"id": "C002", "label": "Jovem digital, baixo saldo",
             "dados": {"idade": 23, "renda_mensal": 2_500, "saldo_medio": 800,
                       "transacoes_mes": 40, "score_credito": 580, "num_produtos": 2}},
            {"id": "C003", "label": "Inadimplente, alto risco",
             "dados": {"idade": 41, "renda_mensal": 3_100, "saldo_medio": 300,
                       "transacoes_mes": 6, "score_credito": 360, "num_produtos": 1}},
            {"id": "C004", "label": "Massa estável típica",
             "dados": {"idade": 45, "renda_mensal": 5_500, "saldo_medio": 12_000,
                       "transacoes_mes": 18, "score_credito": 680, "num_produtos": 3}},
        ]

        # ── Modo segmento (visão gerencial, 3ª pessoa) ───────────────────────
        pergunta_seg = "Quais produtos você recomenda para melhorar minha situação financeira?"
        print("\n" + "═" * 65)
        print("MODO SEGMENTO — agente fala sobre o cliente em 3ª pessoa")
        print("═" * 65)
        for c in clientes_teste:
            r = inference.responder(c["id"], c["dados"], pergunta_seg)
            print(f"\nCliente {r['cliente_id']} ({c['label']})")
            print(f"Segmento: {r['segmento']}  |  Cluster: {r['cluster_id']}")
            print("-" * 65)
            print(r["resposta"])

        # ── Modo persona (arquétipo do cluster, 1ª pessoa) ───────────────────
        # O persona representa o grupo em 1ª pessoa, diferente do segmento (3ª)
        # e do twin (indivíduo real). Útil para pesquisa de UX e comunicação.
        pergunta_persona = "O banco está lançando um cartão com cashback de 2% e anuidade de R$ 480. O que você acha?"
        print("\n" + "═" * 65)
        print("MODO PERSONA — arquétipo do cluster em 1ª pessoa")
        print("═" * 65)
        for cluster_id in sorted(perfis.index):
            r = inference.responder_como_persona(pergunta_persona, cluster_id=int(cluster_id))
            print(f"\n{r['persona_nome']} — {r['segmento']} (cluster {r['cluster_id']})")
            print("-" * 65)
            print(r["resposta"])

        # ── Modo twin (simulação individual, 1ª pessoa) ──────────────────────
        # O twin não usa clustering — derivado dos dados brutos do cliente.
        pergunta_twin = "Você aceitaria um cartão de crédito com anuidade de R$ 480/ano?"
        print("\n" + "═" * 65)
        print("MODO TWIN — agente simula o cliente em 1ª pessoa (sem clustering)")
        print("═" * 65)
        for c in clientes_teste[:2]:  # demo com 2 clientes
            r = inference.responder_como_twin(c["id"], c["dados"], pergunta_twin)
            print(f"\nTwin de {r['cliente_id']} ({c['label']})")
            print("-" * 65)
            print(r["resposta"])
