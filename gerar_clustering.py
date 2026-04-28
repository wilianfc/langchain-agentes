"""
Gera clustering com dados sintéticos, indexa no OpenSearch e salva PKL slim no S3.

Uso:
  # Apenas gerar PKL local (sem AWS):
  python gerar_clustering.py

  # Gerar + indexar OpenSearch + salvar no S3:
  OPENSEARCH_ENDPOINT=search-xxx.sa-east-1.es.amazonaws.com \
  S3_BUCKET=langchain-agent-artifacts-dev \
  python gerar_clustering.py

Dependências locais:
  pip install scikit-learn pandas numpy boto3 langchain-aws langchain-community \
              langchain-anthropic opensearch-py requests-aws4auth
"""
from __future__ import annotations

import os
import pickle
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from aws_pipeline_clientes import (
    gerar_dados_sinteticos,
    executar_clustering,
    _enriquecer_perfis,
    criar_indice_opensearch,
    salvar_pkl_s3,
    _aws_auth,
    _opensearch_url,
    _doc_twin,
    FEATURES,
    N_CLUSTERS,
    S3_BUCKET,
    S3_PREFIX,
    OPENSEARCH_ENDPOINT,
    OPENSEARCH_TWIN_INDEX,
    SEG_PREMIUM,
    SEG_JOVEM,
    SEG_RISCO,
    SEG_MASSA,
)
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from opensearchpy import OpenSearch, RequestsHttpConnection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gerar-clustering")

PKL_FILENAME = "modelo_clustering_slim.pkl"
PKL_LOCAL = Path(PKL_FILENAME)

# Garante segmentos distintos com dados sintéticos
SEGMENTOS_FORCADOS = {
    0: SEG_PREMIUM,
    1: SEG_JOVEM,
    2: SEG_RISCO,
    3: SEG_MASSA,
}


def _gerar_docs_cluster(cluster_id: int, perfil) -> list[Document]:
    seg = perfil["segmento"]
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
            page_content=f"Produtos para '{seg}': {perfil.get('produtos', '')}",
            metadata={"cluster": cluster_id, "segmento": seg, "tipo": "produtos"},
        ),
        Document(
            page_content=f"Estratégia para '{seg}': {perfil.get('prompt_segmento', '')}",
            metadata={"cluster": cluster_id, "segmento": seg, "tipo": "estrategia"},
        ),
    ]


def _indexar_twins(df, embeddings: BedrockEmbeddings, batch_size: int = 400) -> None:
    """Indexa digital twins em lotes para evitar o limite de bulk_size do OpenSearch."""
    auth = _aws_auth()
    raw_client = OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )
    if raw_client.indices.exists(index=OPENSEARCH_TWIN_INDEX):
        raw_client.indices.delete(index=OPENSEARCH_TWIN_INDEX)
        log.info("Índice '%s' removido para re-indexação.", OPENSEARCH_TWIN_INDEX)

    docs = [_doc_twin(row) for _, row in df.iterrows()]
    total = len(docs)
    log.info("Indexando %d digital twins em lotes de %d...", total, batch_size)

    for i in range(0, total, batch_size):
        batch = docs[i:i + batch_size]
        if i == 0:
            OpenSearchVectorSearch.from_documents(
                batch, embeddings,
                opensearch_url=_opensearch_url(),
                index_name=OPENSEARCH_TWIN_INDEX,
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                engine="lucene",
                bulk_size=batch_size,
            )
        else:
            vs = OpenSearchVectorSearch(
                opensearch_url=_opensearch_url(),
                index_name=OPENSEARCH_TWIN_INDEX,
                embedding_function=embeddings,
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
            )
            vs.add_documents(batch, bulk_size=batch_size)
        log.info("  Lote %d/%d indexado (%d docs)", i // batch_size + 1, -(-total // batch_size), len(batch))

    log.info("Digital twins indexados: %d documentos em '%s'.", total, OPENSEARCH_TWIN_INDEX)


def main():
    log.info("Gerando 1000 clientes sintéticos...")
    df = gerar_dados_sinteticos(1000)

    log.info("Executando K-Means (%d clusters)...", N_CLUSTERS)
    df, kmeans, scaler, perfis = executar_clustering(df)

    # Passa seg_df sintético para _enriquecer_perfis — assim os nomes forçados
    # já são usados durante o lookup de personas em PERSONAS_SEGMENTO,
    # garantindo que Carlos→Premium, Júlia→Jovem, Roberto→Risco, Ana→Massa.
    import pandas as pd
    seg_df = pd.DataFrame({
        "cluster_id": list(SEGMENTOS_FORCADOS.keys()),
        "segmento_nome": list(SEGMENTOS_FORCADOS.values()),
        "persona_nome":     ["", "", "", ""],
        "persona_ocupacao": ["", "", "", ""],
        "persona_canal":    ["", "", "", ""],
        "persona_contexto": ["", "", "", ""],
        "prompt_segmento":  ["", "", "", ""],
        "produtos":         ["", "", "", ""],
    })
    perfis = _enriquecer_perfis(perfis, seg_df)

    log.info("Segmentos:\n%s", perfis[["segmento", "n"]].to_string())

    slim = {
        "centroids": kmeans.cluster_centers_.copy(),
        "scale_mean": scaler.mean_.copy(),
        "scale_std": scaler.scale_.copy(),
        "perfis": perfis.to_dict(),
        "features": FEATURES,
        "n_clusters": N_CLUSTERS,
    }

    PKL_LOCAL.write_bytes(pickle.dumps(slim))
    log.info("PKL slim salvo localmente: %s", PKL_LOCAL)

    use_opensearch = bool(OPENSEARCH_ENDPOINT)

    if use_opensearch:
        log.info("Carregando Bedrock Titan Embeddings (amazon.titan-embed-text-v2:0)...")
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v2:0",
            region_name=os.environ.get("BEDROCK_REGION", "us-east-1"),
        )
        splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=40)

        log.info("Indexando digital twins no OpenSearch (em lotes)...")
        _indexar_twins(df, embeddings, batch_size=400)

        log.info("Indexando RAG de segmentos no OpenSearch...")
        for cid in perfis.index:
            docs = _gerar_docs_cluster(int(cid), perfis.loc[cid])
            chunks = splitter.split_documents(docs)
            criar_indice_opensearch(int(cid), chunks, embeddings)
    else:
        log.warning("OPENSEARCH_ENDPOINT não definido — indexação ignorada.")

    if S3_BUCKET:
        log.info("Salvando PKL no S3: s3://%s/%s", S3_BUCKET, S3_PREFIX + PKL_FILENAME)
        salvar_pkl_s3(slim, PKL_FILENAME)
    else:
        log.warning("S3_BUCKET não definido — PKL não enviado ao S3.")

    log.info("=== Concluído ===")


if __name__ == "__main__":
    main()
