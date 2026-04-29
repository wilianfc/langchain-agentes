"""
Lambda de seeding Neptune — invocada uma vez via AWS CLI, depois removida.
Recebe o model_data como JSON no event.
"""
import json
import os
import boto3
import botocore.auth
import botocore.awsrequest
import requests

NEPTUNE_ENDPOINT = os.environ["NEPTUNE_ENDPOINT"]
# Lambda seta AWS_REGION automaticamente; AWS_DEFAULT_REGION é reservado e não é setado
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "sa-east-1"))

PRODUTOS = {
    "Premium Conservador": [
        "Tesouro Direto IPCA+", "Previdência PGBL",
        "Cartão Platinum com sala VIP", "Consultoria de investimentos dedicada",
    ],
    "Jovem Digital": [
        "Cartão cashback 2% sem anuidade", "Conta digital 100% CDI",
        "Crédito pessoal pelo app", "Investimentos a partir de R$ 1",
    ],
    "Alto Risco": [
        "Renegociação com 90% de desconto nos juros",
        "Cartão pré-pago sem consulta SPC/Serasa",
        "Microcrédito inicial R$ 500", "Curso de educação financeira gratuito",
    ],
    "Massa Estável": [
        "Conta corrente tarifa zero", "Previdência VGBL a partir de R$ 100/mês",
        "Consórcio imobiliário sem juros", "Seguro residencial a partir de R$ 29/mês",
    ],
}

PERSONAS = {
    "Premium Conservador": {"nome": "Carlos", "ocupacao": "gerente de empresa, 52 anos",
        "contexto": "Patrimônio consolidado, foco em segurança e rentabilidade real acima da inflação."},
    "Jovem Digital": {"nome": "Júlia", "ocupacao": "designer freelancer, 26 anos",
        "contexto": "Prefere produtos digitais, cashback e aprovação instantânea pelo app."},
    "Alto Risco": {"nome": "Roberto", "ocupacao": "motorista autônomo, 43 anos",
        "contexto": "Busca reorganizar finanças após inadimplência, precisa de orientação concreta."},
    "Massa Estável": {"nome": "Ana", "ocupacao": "funcionária pública, 38 anos",
        "contexto": "Valoriza estabilidade e produtos sem surpresas, pensa no futuro da família."},
}


def _cypher(query, params=None):
    url = f"https://{NEPTUNE_ENDPOINT}:8182/openCypher"
    payload = {"query": query}
    if params:
        payload["parameters"] = json.dumps(params)  # Neptune expects JSON string inside JSON body
    body = json.dumps(payload).encode("utf-8")

    session = boto3.session.Session()
    creds = session.get_credentials()
    aws_req = botocore.awsrequest.AWSRequest(
        method="POST", url=url, data=body,
        headers={"Content-Type": "application/json", "Host": f"{NEPTUNE_ENDPOINT}:8182"},
    )
    botocore.auth.SigV4Auth(creds, "neptune-db", AWS_REGION).add_auth(aws_req)

    resp = requests.post(url, data=body, headers=dict(aws_req.headers), timeout=30)
    if not resp.ok:
        print(f"Neptune {resp.status_code}: {resp.text[:500]}")
    resp.raise_for_status()
    return resp.json()


def lambda_handler(event, context):
    import numpy as np

    model_data = event  # event IS the model_data dict

    # Limpa grafo
    _cypher("MATCH (n) DETACH DELETE n")

    perfis = model_data["perfis"]
    n_clusters = len(perfis.get("segmento", {}))

    # Segmentos + produtos + personas
    for cid_str, segmento in perfis["segmento"].items():
        cid = int(cid_str)
        _cypher(
            "MERGE (s:Segmento {cluster_id: $cid}) "
            "SET s.nome = $nome, s.inadimplencia = $inadimplencia, "
            "s.renda_media = $renda_media, s.score_medio = $score_medio, s.n_clientes = $n_clientes",
            {"cid": cid, "nome": segmento,
             "inadimplencia": float(perfis.get("inadimplencia", {}).get(cid_str, 0)),
             "renda_media": float(perfis.get("renda_media", {}).get(cid_str, 0)),
             "score_medio": float(perfis.get("score_medio", {}).get(cid_str, 0)),
             "n_clientes": int(perfis.get("n", {}).get(cid_str, 0))},
        )
        for produto in PRODUTOS.get(segmento, []):
            _cypher(
                "MERGE (p:Produto {nome: $nome}) WITH p "
                "MATCH (s:Segmento {cluster_id: $cid}) MERGE (s)-[:RECOMENDA]->(p)",
                {"nome": produto, "cid": cid},
            )
        p_data = PERSONAS.get(segmento, {})
        if p_data:
            _cypher(
                "MERGE (p:Persona {nome: $nome}) SET p.ocupacao=$ocupacao, p.contexto=$contexto "
                "WITH p MATCH (s:Segmento {cluster_id: $cid}) MERGE (s)-[:TEM_PERSONA]->(p)",
                {"nome": p_data["nome"], "ocupacao": p_data["ocupacao"],
                 "contexto": p_data["contexto"], "cid": cid},
            )

    # 50 clientes por cluster
    centroids = model_data["centroids"]
    scale_mean = model_data["scale_mean"]
    scale_std = model_data["scale_std"]
    features = model_data["features"]
    rng = np.random.default_rng(42)
    clientes_por_cluster = {}
    for cid in range(n_clusters):
        centroid = np.array(centroids[cid])
        clientes = []
        for i in range(50):
            X = centroid + rng.normal(0, 0.3, size=centroid.shape)
            dados = X * np.array(scale_std) + np.array(scale_mean)
            cid_str2 = f"GRAPH-C{cid:02d}-{i:04d}"
            cliente = {f: float(max(0, v)) for f, v in zip(features, dados)}
            clientes.append((cid_str2, cliente))
            _cypher(
                "MERGE (c:Cliente {id: $id}) SET c.cluster_id=$cid, c.score_credito=$score, "
                "c.renda_mensal=$renda, c.idade=$idade "
                "WITH c MATCH (s:Segmento {cluster_id: $cid}) MERGE (c)-[:PERTENCE_A]->(s)",
                {"id": cid_str2, "cid": cid,
                 "score": cliente.get("score_credito", 0),
                 "renda": cliente.get("renda_mensal", 0),
                 "idade": cliente.get("idade", 0)},
            )
        clientes_por_cluster[cid] = clientes

    # k-NN
    for cid, clientes in clientes_por_cluster.items():
        fm = np.array([list(c[1].values()) for c in clientes])
        norm = (fm - np.array(scale_mean)) / np.array(scale_std)
        for idx, (cid_str2, _) in enumerate(clientes):
            dists = np.linalg.norm(norm - norm[idx], axis=1)
            dists[idx] = np.inf
            for nn_idx in np.argsort(dists)[:3]:
                _cypher(
                    "MATCH (a:Cliente {id:$a}),(b:Cliente {id:$b}) MERGE (a)-[:SIMILAR_A]->(b)",
                    {"a": cid_str2, "b": clientes[nn_idx][0]},
                )

    result = _cypher("MATCH (n) RETURN labels(n)[0] AS tipo, count(n) AS total ORDER BY total DESC")
    return {"status": "ok", "nodes": result.get("results", [])}
