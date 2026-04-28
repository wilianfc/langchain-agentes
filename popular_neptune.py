"""
popular_neptune.py — Popula o grafo de conhecimento no Amazon Neptune.

Cria os nós e arestas que formam o grafo de segmentação bancária:
  (:Segmento)-[:RECOMENDA]->(:Produto)
  (:Segmento)-[:TEM_PERSONA]->(:Persona)
  (:Cliente)-[:PERTENCE_A]->(:Segmento)
  (:Cliente)-[:SIMILAR_A]->(:Cliente)   ← k-NN dentro do mesmo cluster

Uso:
  NEPTUNE_ENDPOINT=xxx.neptune.amazonaws.com \\
  python popular_neptune.py

Dependências locais:
  pip install boto3 requests requests-aws4auth
"""
from __future__ import annotations

import json
import logging
import os
import pickle
import sys
from pathlib import Path

import boto3
import numpy as np
import requests
from requests_aws4auth import AWS4Auth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("popular-neptune")

NEPTUNE_ENDPOINT = os.environ.get("NEPTUNE_ENDPOINT", "")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "sa-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET", "langchain-agent-artifacts-dev")
S3_PREFIX = os.environ.get("S3_PREFIX", "clientes-agente/")
PKL_LOCAL = Path("modelo_clustering_slim.pkl")

# Segmentos e conteúdo correspondente
PRODUTOS = {
    "Premium Conservador": [
        "Tesouro Direto IPCA+",
        "Previdência PGBL",
        "Cartão Platinum com sala VIP",
        "Consultoria de investimentos dedicada",
    ],
    "Jovem Digital": [
        "Cartão cashback 2% sem anuidade",
        "Conta digital 100% CDI",
        "Crédito pessoal pelo app",
        "Investimentos a partir de R$ 1",
    ],
    "Alto Risco": [
        "Renegociação com 90% de desconto nos juros",
        "Cartão pré-pago sem consulta SPC/Serasa",
        "Microcrédito inicial R$ 500",
        "Curso de educação financeira gratuito",
    ],
    "Massa Estável": [
        "Conta corrente tarifa zero",
        "Previdência VGBL a partir de R$ 100/mês",
        "Consórcio imobiliário sem juros",
        "Seguro residencial a partir de R$ 29/mês",
    ],
}

PERSONAS = {
    "Premium Conservador": {
        "nome": "Carlos",
        "ocupacao": "gerente de empresa, 52 anos",
        "contexto": "Patrimônio consolidado, foco em segurança e rentabilidade real acima da inflação.",
    },
    "Jovem Digital": {
        "nome": "Júlia",
        "ocupacao": "designer freelancer, 26 anos",
        "contexto": "Prefere produtos digitais, cashback e aprovação instantânea pelo app.",
    },
    "Alto Risco": {
        "nome": "Roberto",
        "ocupacao": "motorista autônomo, 43 anos",
        "contexto": "Busca reorganizar finanças após inadimplência, precisa de orientação concreta.",
    },
    "Massa Estável": {
        "nome": "Ana",
        "ocupacao": "funcionária pública, 38 anos",
        "contexto": "Valoriza estabilidade e produtos sem surpresas, pensa no futuro da família.",
    },
}


def _auth() -> AWS4Auth:
    session = boto3.session.Session()
    creds = session.get_credentials().get_frozen_credentials()
    return AWS4Auth(creds.access_key, creds.secret_key, AWS_REGION, "neptune-db",
                    session_token=creds.token)


def _cypher(query: str, params: dict | None = None) -> dict:
    url = f"https://{NEPTUNE_ENDPOINT}:8182/openCypher"
    payload = {"query": query}
    if params:
        payload["parameters"] = json.dumps(params)
    resp = requests.post(url, json=payload, auth=_auth(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _carregar_pkl() -> dict:
    if PKL_LOCAL.exists():
        log.info("Carregando PKL local: %s", PKL_LOCAL)
        return pickle.loads(PKL_LOCAL.read_bytes())

    log.info("PKL local não encontrado. Baixando do S3: s3://%s/%s", S3_BUCKET, S3_PREFIX)
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}modelo_clustering_slim.pkl")
    data = pickle.loads(obj["Body"].read())
    PKL_LOCAL.write_bytes(pickle.dumps(data))
    return data


def limpar_grafo() -> None:
    log.info("Removendo todos os nós e arestas existentes...")
    _cypher("MATCH (n) DETACH DELETE n")
    log.info("Grafo limpo.")


def criar_segmentos(perfis_dict: dict) -> None:
    log.info("Criando nós :Segmento...")
    raw = perfis_dict
    n_clusters = len(raw.get("segmento", {}))

    for cid in range(n_clusters):
        segmento = raw["segmento"][cid]
        inadimplencia = float(raw.get("inadimplencia", {}).get(cid, 0))
        renda_media = float(raw.get("renda_media", {}).get(cid, 0))
        score_medio = float(raw.get("score_medio", {}).get(cid, 0))
        n_clientes = int(raw.get("n", {}).get(cid, 0))

        _cypher(
            "MERGE (s:Segmento {cluster_id: $cid}) "
            "SET s.nome = $nome, s.inadimplencia = $inadimplencia, "
            "s.renda_media = $renda_media, s.score_medio = $score_medio, "
            "s.n_clientes = $n_clientes",
            {"cid": cid, "nome": segmento, "inadimplencia": inadimplencia,
             "renda_media": renda_media, "score_medio": score_medio,
             "n_clientes": n_clientes},
        )

        # Produtos → arestas :RECOMENDA
        for produto in PRODUTOS.get(segmento, []):
            _cypher(
                "MERGE (p:Produto {nome: $nome}) "
                "WITH p "
                "MATCH (s:Segmento {cluster_id: $cid}) "
                "MERGE (s)-[:RECOMENDA]->(p)",
                {"nome": produto, "cid": cid},
            )

        # Persona → aresta :TEM_PERSONA
        p_data = PERSONAS.get(segmento, {})
        if p_data:
            _cypher(
                "MERGE (p:Persona {nome: $nome}) "
                "SET p.ocupacao = $ocupacao, p.contexto = $contexto "
                "WITH p "
                "MATCH (s:Segmento {cluster_id: $cid}) "
                "MERGE (s)-[:TEM_PERSONA]->(p)",
                {"nome": p_data["nome"], "ocupacao": p_data["ocupacao"],
                 "contexto": p_data["contexto"], "cid": cid},
            )

    log.info("Segmentos, produtos e personas criados.")


def criar_clientes(model_data: dict, n_sample: int = 200) -> None:
    """
    Cria nós :Cliente e arestas :PERTENCE_A e :SIMILAR_A.
    Usa os centroides do PKL para calcular similaridade (k-NN dentro do cluster).
    """
    log.info("Criando %d nós :Cliente de amostra...", n_sample)
    rng = np.random.default_rng(42)
    centroids = model_data["centroids"]
    scale_mean = model_data["scale_mean"]
    scale_std = model_data["scale_std"]
    features = model_data["features"]
    n_clusters = model_data["n_clusters"]

    # Gera dados sintéticos representativos de cada cluster
    clientes_por_cluster: dict[int, list] = {c: [] for c in range(n_clusters)}
    per_cluster = n_sample // n_clusters

    for cid in range(n_clusters):
        centroid = centroids[cid]
        for i in range(per_cluster):
            # Perturbação gaussiana ao redor do centroide
            X = centroid + rng.normal(0, 0.3, size=centroid.shape)
            # Desnormaliza
            dados_raw = X * scale_std + scale_mean
            cliente_id = f"GRAPH-C{cid:02d}-{i:04d}"
            cliente = {f: float(max(0, v)) for f, v in zip(features, dados_raw)}
            clientes_por_cluster[cid].append((cliente_id, cliente))

            _cypher(
                "MERGE (c:Cliente {id: $id}) "
                "SET c.cluster_id = $cid, c.score_credito = $score, "
                "c.renda_mensal = $renda, c.idade = $idade "
                "WITH c "
                "MATCH (s:Segmento {cluster_id: $cid}) "
                "MERGE (c)-[:PERTENCE_A]->(s)",
                {
                    "id": cliente_id, "cid": cid,
                    "score": cliente.get("score_credito", 0),
                    "renda": cliente.get("renda_mensal", 0),
                    "idade": cliente.get("idade", 0),
                },
            )

    # Arestas :SIMILAR_A — conecta cada cliente aos 3 mais próximos no cluster
    log.info("Criando arestas :SIMILAR_A (k-NN intra-cluster)...")
    for cid, clientes in clientes_por_cluster.items():
        features_matrix = np.array([[v for v in c[1].values()] for c in clientes])
        norm = (features_matrix - scale_mean) / scale_std

        for idx, (cid_str, _) in enumerate(clientes):
            dists = np.linalg.norm(norm - norm[idx], axis=1)
            dists[idx] = np.inf  # exclui ele mesmo
            k_nearest = np.argsort(dists)[:3]
            for nn_idx in k_nearest:
                nn_id = clientes[nn_idx][0]
                _cypher(
                    "MATCH (a:Cliente {id: $a}), (b:Cliente {id: $b}) "
                    "MERGE (a)-[:SIMILAR_A]->(b)",
                    {"a": cid_str, "b": nn_id},
                )

    log.info("Clientes e similaridades criados.")


def main():
    if not NEPTUNE_ENDPOINT:
        log.error("NEPTUNE_ENDPOINT não definido.")
        sys.exit(1)

    log.info("Conectando ao Neptune: %s", NEPTUNE_ENDPOINT)
    model_data = _carregar_pkl()

    limpar_grafo()
    criar_segmentos(model_data["perfis"])
    criar_clientes(model_data)

    # Resumo do grafo
    result = _cypher(
        "MATCH (n) RETURN labels(n)[0] AS tipo, count(n) AS total "
        "ORDER BY total DESC"
    )
    log.info("=== Grafo populado ===")
    for row in result.get("results", []):
        log.info("  %-12s : %d nós", row["tipo"], row["total"])

    edges = _cypher("MATCH ()-[r]->() RETURN type(r) AS tipo, count(r) AS total ORDER BY total DESC")
    for row in edges.get("results", []):
        log.info("  %-20s : %d arestas", row["tipo"], row["total"])


if __name__ == "__main__":
    main()
