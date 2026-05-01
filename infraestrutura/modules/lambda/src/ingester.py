"""
Ingester Lambda — indexa documentos e entrevistas no OpenSearch.

Triggers:
  1. S3 PUT event  — upload de arquivo em s3://bucket/entrevistas/{cluster_N|cliente_ID}/*.txt
  2. API Gateway   — POST /documentos com payload JSON

Schema S3 key esperado:
  entrevistas/cluster_0/entrevista_2025Q1.txt   → cluster_id=0
  entrevistas/cliente_C001/voz_do_cliente.txt   → cliente_id=C001
  documentos/politica_investimentos.txt         → índice documentos-knowledge

Schema API body:
  {
    "tipo": "entrevista" | "documento",
    "titulo": "...",
    "texto": "...",
    "cliente_id": "C001",      # opcional — entrevista individual
    "cluster_id": 0            # opcional — entrevista de segmento
  }
"""
from __future__ import annotations

import json
import logging
import os
import re
import traceback
from typing import Dict, Optional
import urllib.parse

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers
from requests_aws4auth import AWS4Auth

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

AWS_REGION = os.environ.get("AWS_REGION", "sa-east-1")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "")

ENTREVISTAS_INDEX = "entrevistas-clientes"
DOCUMENTOS_INDEX = "documentos-knowledge"

_s3 = boto3.client("s3")


# ── OpenSearch ─────────────────────────────────────────────────────────────────

def _os_client() -> OpenSearch:
    sess = boto3.session.Session()
    creds = sess.get_credentials().get_frozen_credentials()
    auth = AWS4Auth(creds.access_key, creds.secret_key, AWS_REGION, "es",
                    session_token=creds.token)
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def _garantir_indice(client: OpenSearch, index: str, mapping_extra: dict = None) -> None:
    if client.indices.exists(index=index):
        return
    body: dict = {
        "settings": {"number_of_shards": 1, "number_of_replicas": 1},
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "metadata": {"type": "object", "dynamic": True},
            }
        },
    }
    if mapping_extra:
        body["mappings"]["properties"].update(mapping_extra)
    client.indices.create(index=index, body=body)
    log.info("Índice '%s' criado.", index)


# ── Parsing de chave S3 ────────────────────────────────────────────────────────

def _parsear_chave_s3(key: str) -> Optional[Dict]:
    """
    Extrai metadados da chave S3.
    entrevistas/cluster_0/arquivo.txt  → tipo=entrevista, cluster_id=0
    entrevistas/cliente_C001/arq.txt  → tipo=entrevista, cliente_id=C001
    documentos/titulo.txt             → tipo=documento
    """
    partes = key.strip("/").split("/")
    if len(partes) < 2:
        return None

    prefixo = partes[0].lower()
    if prefixo == "entrevistas" and len(partes) >= 3:
        sub = partes[1]
        titulo = partes[-1].rsplit(".", 1)[0].replace("_", " ").title()
        m_cluster = re.match(r"cluster_(\d+)", sub, re.IGNORECASE)
        m_cliente = re.match(r"cliente_(.+)", sub, re.IGNORECASE)
        if m_cluster:
            return {"tipo": "entrevista", "titulo": titulo,
                    "cluster_id": int(m_cluster.group(1))}
        if m_cliente:
            return {"tipo": "entrevista", "titulo": titulo,
                    "cliente_id": m_cliente.group(1)}

    if prefixo == "documentos":
        titulo = partes[-1].rsplit(".", 1)[0].replace("_", " ").title()
        return {"tipo": "documento", "titulo": titulo}

    return None


# ── Indexação ──────────────────────────────────────────────────────────────────

def _chunkar(texto: str, tamanho: int = 400) -> list[str]:
    paragrafos = [p.strip() for p in re.split(r"\n{2,}", texto) if p.strip()]
    chunks, atual, contagem = [], [], 0
    for par in paragrafos:
        n = len(par.split())
        if contagem + n > tamanho and atual:
            chunks.append("\n\n".join(atual))
            atual, contagem = [], 0
        atual.append(par)
        contagem += n
    if atual:
        chunks.append("\n\n".join(atual))
    return chunks or [texto]


def _indexar_entrevista(texto: str, titulo: str, cliente_id: str, cluster_id: int,
                        client: OpenSearch) -> int:
    _garantir_indice(client, ENTREVISTAS_INDEX)
    chunks = _chunkar(texto)
    actions = []
    for i, chunk in enumerate(chunks):
        meta: Dict = {"titulo": titulo, "chunk_idx": i}
        if cliente_id:
            meta["cliente_id"] = cliente_id
        if cluster_id is not None:
            meta["cluster_id"] = cluster_id
        actions.append({
            "_index": ENTREVISTAS_INDEX,
            "_source": {"text": chunk, "metadata": meta},
        })
    success, _ = helpers.bulk(client, actions, raise_on_error=False)
    client.indices.refresh(index=ENTREVISTAS_INDEX)
    return success


def _indexar_documento(texto: str, titulo: str, client: OpenSearch) -> int:
    _garantir_indice(client, DOCUMENTOS_INDEX)
    chunks = _chunkar(texto)
    actions = [
        {
            "_index": DOCUMENTOS_INDEX,
            "_source": {
                "text": chunk,
                "metadata": {"titulo": titulo, "chunk_idx": i},
            },
        }
        for i, chunk in enumerate(chunks)
    ]
    success, _ = helpers.bulk(client, actions, raise_on_error=False)
    client.indices.refresh(index=DOCUMENTOS_INDEX)
    return success


# ── Handler principal ──────────────────────────────────────────────────────────

def _processar(titulo: str, texto: str, tipo: str,
               cliente_id: str = "", cluster_id: int = None) -> Dict:
    client = _os_client()
    if tipo == "entrevista":
        n = _indexar_entrevista(texto, titulo, cliente_id, cluster_id, client)
    else:
        n = _indexar_documento(texto, titulo, client)
    return {"ok": True, "chunks_indexados": n, "tipo": tipo, "titulo": titulo}


def _handle_s3(event: dict) -> list:
    resultados = []
    for rec in event.get("Records", []):
        bucket = rec["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
        log.info("S3 trigger: s3://%s/%s", bucket, key)

        meta = _parsear_chave_s3(key)
        if not meta:
            log.warning("Chave S3 não reconhecida: %s", key)
            continue

        obj = _s3.get_object(Bucket=bucket, Key=key)
        texto = obj["Body"].read().decode("utf-8", errors="replace")

        r = _processar(
            titulo=meta.get("titulo", key),
            texto=texto,
            tipo=meta["tipo"],
            cliente_id=meta.get("cliente_id", ""),
            cluster_id=meta.get("cluster_id"),
        )
        log.info("Indexado: %s", r)
        resultados.append(r)
    return resultados


def _handle_api(event: dict) -> Dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"erro": "JSON inválido"})}

    tipo = body.get("tipo", "documento")
    titulo = body.get("titulo", "Sem título")
    texto = body.get("texto", "")
    cliente_id = body.get("cliente_id", "")
    cluster_id = body.get("cluster_id")

    if not texto.strip():
        return {"statusCode": 400, "body": json.dumps({"erro": "'texto' obrigatório"})}

    try:
        r = _processar(titulo, texto, tipo, cliente_id, cluster_id)
        return {"statusCode": 200, "body": json.dumps(r, ensure_ascii=False)}
    except Exception:
        log.error("Erro ao indexar: %s", traceback.format_exc())
        return {"statusCode": 500, "body": json.dumps({"erro": "Erro interno"})}


def lambda_handler(event, context):
    if "Records" in event and event["Records"][0].get("eventSource") == "aws:s3":
        return _handle_s3(event)
    return _handle_api(event)
