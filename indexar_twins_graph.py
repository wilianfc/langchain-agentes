"""
Indexa os 200 clientes GRAPH-C* no índice clientes-digital-twins do OpenSearch.

Esses clientes existem no grafo Neptune (criados pelo seed_neptune_lambda.py)
mas nunca foram indexados no pipeline gerar_clustering.py, que indexa apenas
clientes com IDs C* gerados sinteticamente.

O worker usa BM25 com term filter por cliente_id no modo twin. Sem esses
documentos, _rag_twin retorna vazio e o índice de confiabilidade fica baixo.

Uso:
  AWS_REGION=sa-east-1 python indexar_twins_graph.py

Requer: boto3, opensearch-py, requests-aws4auth, numpy
"""
import json
import os
import sys

import boto3
import numpy as np
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers
from requests_aws4auth import AWS4Auth

OPENSEARCH_ENDPOINT = os.environ.get(
    "OPENSEARCH_ENDPOINT",
    "search-langchain-agent-dev-ujstn5xeniamxdbr4rhh7qgmbu.sa-east-1.es.amazonaws.com",
)
TWIN_INDEX = "clientes-digital-twins"
AWS_REGION = os.environ.get("AWS_REGION", "sa-east-1")

SEGMENTOS = {
    0: "Premium Conservador",
    1: "Jovem Digital",
    2: "Alto Risco",
    3: "Massa Estável",
}


def _aws_auth() -> AWS4Auth:
    sess = boto3.session.Session()
    creds = sess.get_credentials().get_frozen_credentials()
    return AWS4Auth(
        creds.access_key, creds.secret_key, AWS_REGION, "es",
        session_token=creds.token,
    )


def _os_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=_aws_auth(),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def _doc_text(cliente_id: str, dados: dict, cluster_id: int) -> str:
    segmento = SEGMENTOS.get(cluster_id, f"Cluster {cluster_id}")
    canal = "digital (app/internet banking)" if dados.get("canal_digital") else "presencial (agência)"
    historico = (
        "inadimplente, histórico de atraso em pagamentos"
        if dados.get("inadimplente")
        else "adimplente, sem pendências"
    )
    return (
        f"Perfil individual do cliente {cliente_id}:\n"
        f"- Segmento: {segmento}\n"
        f"- Idade: {dados['idade']:.0f} anos\n"
        f"- Renda mensal: R$ {dados['renda_mensal']:,.0f}\n"
        f"- Saldo médio: R$ {dados['saldo_medio']:,.0f}\n"
        f"- Transações/mês: {dados['transacoes_mes']:.0f}\n"
        f"- Score de crédito: {dados['score_credito']:.0f}\n"
        f"- Número de produtos: {dados['num_produtos']:.0f}\n"
        f"- Canal preferencial: {canal}\n"
        f"- Histórico: {historico}"
    )


def gerar_clientes_graph(model_data: dict) -> list:
    """
    Reconstrói deterministicamente os 200 clientes GRAPH-C* usando a mesma
    seed e lógica do seed_neptune_lambda.py (np.random.default_rng(42)).
    """
    centroids = model_data["centroids"]
    scale_mean = np.array(model_data["scale_mean"])
    scale_std = np.array(model_data["scale_std"])
    features = model_data["features"]
    n_clusters = model_data["n_clusters"]

    rng = np.random.default_rng(42)
    clientes = []

    for cid in range(n_clusters):
        centroid = np.array(centroids[cid])
        for i in range(50):
            X = centroid + rng.normal(0, 0.3, size=centroid.shape)
            dados_raw = X * scale_std + scale_mean
            dados = {f: float(max(0, v)) for f, v in zip(features, dados_raw)}
            dados["canal_digital"] = dados["idade"] < 38 or dados["score_credito"] > 700
            dados["inadimplente"] = dados["score_credito"] < 450
            clientes.append({
                "cliente_id": f"GRAPH-C{cid:02d}-{i:04d}",
                "cluster_id": cid,
                **dados,
            })

    return clientes


def indexar(clientes: list, client: OpenSearch) -> None:
    if not client.indices.exists(index=TWIN_INDEX):
        print(f"ERRO: índice '{TWIN_INDEX}' não existe. Execute gerar_clustering.py primeiro.")
        sys.exit(1)

    # Verifica quais IDs já existem para evitar duplicatas
    ids_existentes = set()
    resp = client.search(
        index=TWIN_INDEX,
        body={
            "query": {"prefix": {"metadata.cliente_id.keyword": "GRAPH-C"}},
            "size": 10000,
            "_source": ["metadata.cliente_id"],
        },
    )
    for hit in resp.get("hits", {}).get("hits", []):
        ids_existentes.add(hit["_source"]["metadata"]["cliente_id"])

    novos = [c for c in clientes if c["cliente_id"] not in ids_existentes]
    if not novos:
        print(f"Todos os {len(clientes)} clientes GRAPH-C* já estão indexados.")
        return

    print(f"Já indexados: {len(ids_existentes)} | A indexar: {len(novos)}")

    actions = [
        {
            "_index": TWIN_INDEX,
            "_source": {
                "text": _doc_text(c["cliente_id"], c, c["cluster_id"]),
                "metadata": {
                    "cliente_id": c["cliente_id"],
                    "tipo": "twin",
                },
            },
        }
        for c in novos
    ]

    success, errors = helpers.bulk(client, actions, raise_on_error=False)
    print(f"Inseridos: {success} | Erros: {len(errors) if isinstance(errors, list) else errors}")
    if errors:
        for e in (errors[:3] if isinstance(errors, list) else [errors]):
            print(f"  erro: {e}")

    client.indices.refresh(index=TWIN_INDEX)
    total = client.count(index=TWIN_INDEX)["count"]
    print(f"Total de documentos em '{TWIN_INDEX}': {total}")


def main():
    model_data_path = os.path.join(os.path.dirname(__file__), "model_data.json")
    print(f"Carregando {model_data_path}...")
    with open(model_data_path) as f:
        model_data = json.load(f)

    print("Gerando 200 clientes GRAPH-C* (seed=42, determinístico)...")
    clientes = gerar_clientes_graph(model_data)

    for cid in range(model_data["n_clusters"]):
        n = sum(1 for c in clientes if c["cluster_id"] == cid)
        seg = SEGMENTOS.get(cid, f"Cluster {cid}")
        print(f"  GRAPH-C{cid:02d}-*: {n} clientes | {seg}")

    print(f"\nConectando ao OpenSearch: {OPENSEARCH_ENDPOINT}")
    client = _os_client()
    indexar(clientes, client)

    # Validação rápida: verifica se GRAPH-C00-0001 está acessível
    r = client.search(
        index=TWIN_INDEX,
        body={
            "query": {
                "bool": {
                    "must": {"match": {"text": "investimento previdência"}},
                    "filter": {"term": {"metadata.cliente_id.keyword": "GRAPH-C00-0001"}},
                }
            },
            "size": 1,
        },
    )
    hits = r.get("hits", {}).get("hits", [])
    if hits:
        print("\nValidação OK — GRAPH-C00-0001 encontrado no índice:")
        print(hits[0]["_source"]["text"][:200])
    else:
        print("\nAVISO: GRAPH-C00-0001 não encontrado após indexação.")


if __name__ == "__main__":
    main()
