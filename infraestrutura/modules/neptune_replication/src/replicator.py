"""
replicator.py — Lambda que replica alterações do Neptune para o OpenSearch.

Triggered pelo Neptune Streams via EventBridge Pipes ou polling SQS.
Processa eventos de criação/atualização/remoção de nós e arestas,
mantendo o índice OpenSearch sincronizado com o grafo Neptune.

Eventos Neptune Streams têm o formato:
  {
    "commitTimestamp": 1234567890,
    "eventId": { "commitNum": 1, "opNum": 1 },
    "data": {
      "id": "node-id",
      "type": "vl",           # vl = vertex label, e = edge
      "key": "nome",
      "value": { "dataType": "String", "value": "Premium Conservador" },
      "op": "ADD"             # ADD | REMOVE | MODIFY
    },
    "op": "ADD"
  }
"""
from __future__ import annotations

import json
import logging
import os
import traceback
from typing import Any, Dict, List

import boto3
import requests
from botocore.config import Config
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

AWS_REGION = os.environ.get("AWS_REGION", "sa-east-1")
OPENSEARCH_ENDPOINT = os.environ["OPENSEARCH_ENDPOINT"]
NEPTUNE_ENDPOINT = os.environ["NEPTUNE_ENDPOINT"]
SYNC_INDEX = "neptune-graph-sync"

_config = Config(connect_timeout=5, read_timeout=30)
_s3 = boto3.client("s3", config=_config)


def _auth() -> AWS4Auth:
    session = boto3.session.Session()
    creds = session.get_credentials().get_frozen_credentials()
    return AWS4Auth(creds.access_key, creds.secret_key, AWS_REGION, "es",
                    session_token=creds.token)


def _os_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=_auth(),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def _neptune_query(cypher: str) -> List[Dict]:
    url = f"https://{NEPTUNE_ENDPOINT}:8182/openCypher"
    auth = AWS4Auth(
        *boto3.session.Session().get_credentials().get_frozen_credentials()[:2],
        AWS_REGION, "neptune-db",
        session_token=boto3.session.Session().get_credentials().get_frozen_credentials().token,
    )
    resp = requests.post(url, json={"query": cypher}, auth=auth, timeout=15)
    resp.raise_for_status()
    return resp.json().get("results", [])


def _ensure_index(client: OpenSearch) -> None:
    if not client.indices.exists(index=SYNC_INDEX):
        client.indices.create(
            index=SYNC_INDEX,
            body={
                "mappings": {
                    "properties": {
                        "node_id":    {"type": "keyword"},
                        "node_type":  {"type": "keyword"},
                        "cluster_id": {"type": "integer"},
                        "text":       {"type": "text", "analyzer": "portuguese"},
                        "properties": {"type": "object", "dynamic": True},
                        "relacoes":   {"type": "text"},
                        "updated_at": {"type": "date"},
                    }
                }
            },
        )
        log.info("Índice '%s' criado.", SYNC_INDEX)


def _snapshot_node(node_id: str) -> Dict[str, Any] | None:
    """Consulta o Neptune para obter o estado atual do nó e seus relacionamentos."""
    rows = _neptune_query(
        f"MATCH (n) WHERE id(n) = '{node_id}' "
        "OPTIONAL MATCH (n)-[r]->(m) "
        "RETURN labels(n) AS labels, properties(n) AS props, "
        "collect(type(r) + ' -> ' + coalesce(m.nome, id(m))) AS relacoes"
    )
    if not rows:
        return None
    row = rows[0]
    props = row.get("props", {})
    labels = row.get("labels", [])
    relacoes = row.get("relacoes", [])

    # Texto livre para BM25 — combina propriedades e relacionamentos
    text_parts = [f"{k}: {v}" for k, v in props.items() if v]
    if relacoes:
        text_parts.append("Relações: " + "; ".join(r for r in relacoes if r))

    return {
        "node_id": node_id,
        "node_type": labels[0] if labels else "Unknown",
        "cluster_id": props.get("cluster_id", -1),
        "properties": props,
        "relacoes": "; ".join(r for r in relacoes if r),
        "text": ". ".join(text_parts),
        "updated_at": "now",
    }


def _process_event(event: Dict, client: OpenSearch) -> None:
    data = event.get("data", {})
    op = event.get("op", "")
    node_id = data.get("id", "")

    if not node_id or data.get("type") == "e":
        # Ignora eventos de arestas — o snapshot do nó já captura relações
        return

    if op == "REMOVE":
        try:
            client.delete(index=SYNC_INDEX, id=node_id, ignore=[404])
            log.info("Nó removido do índice: %s", node_id)
        except Exception:
            log.warning("Erro ao remover nó %s: %s", node_id, traceback.format_exc())
        return

    doc = _snapshot_node(node_id)
    if doc:
        client.index(index=SYNC_INDEX, id=node_id, body=doc)
        log.debug("Nó indexado: %s (%s)", node_id, doc["node_type"])


def _poll_streams(commit_num_from: int = 1) -> List[Dict]:
    """Consulta Neptune Streams para obter eventos recentes."""
    url = (
        f"https://{NEPTUNE_ENDPOINT}:8182/gremlin/stream"
        f"?commitNum={commit_num_from}&limit=100"
    )
    auth = AWS4Auth(
        *boto3.session.Session().get_credentials().get_frozen_credentials()[:2],
        AWS_REGION, "neptune-db",
        session_token=boto3.session.Session().get_credentials().get_frozen_credentials().token,
    )
    try:
        resp = requests.get(url, auth=auth, timeout=15)
        if resp.status_code == 404:
            return []  # Sem eventos novos
        resp.raise_for_status()
        return resp.json().get("records", [])
    except Exception:
        log.warning("Erro ao consultar Neptune Streams: %s", traceback.format_exc())
        return []


def lambda_handler(event, context):
    """
    Triggered por EventBridge Schedule (polling) ou diretamente.
    Lê Neptune Streams e sincroniza com OpenSearch.
    """
    client = _os_client()
    _ensure_index(client)

    # Suporte a dois modos: eventos diretos (SNS/SQS) ou polling de Streams
    records = event.get("Records", [])
    if records:
        # Modo push — eventos via SQS/SNS
        processed = 0
        for record in records:
            try:
                body = json.loads(record.get("body", "{}"))
                stream_events = body.get("events", [body])
                for evt in stream_events:
                    _process_event(evt, client)
                    processed += 1
            except Exception:
                log.error("Erro ao processar record: %s", traceback.format_exc())
        log.info("Replicação concluída: %d eventos processados.", processed)
    else:
        # Modo polling — chamada agendada
        stream_records = _poll_streams()
        for rec in stream_records:
            _process_event(rec, client)
        log.info("Polling de Streams: %d eventos sincronizados.", len(stream_records))

    return {"statusCode": 200, "body": "OK"}
