"""
Gera clustering com dados sintéticos, indexa no OpenSearch e salva PKL slim no S3.

Uso:
  # Apenas gerar PKL local (sem AWS):
  python gerar_clustering.py

  # Gerar + indexar OpenSearch + salvar no S3:
  OPENSEARCH_ENDPOINT=search-xxx.sa-east-1.es.amazonaws.com \
  S3_BUCKET=langchain-agent-artifacts-dev \
  python gerar_clustering.py

Dependências locais (instalar com pip):
  pip install scikit-learn pandas numpy boto3 langchain-community \
              langchain-anthropic sentence-transformers opensearch-py requests-aws4auth
"""
from __future__ import annotations

import os
import pickle
import logging
import sys
from pathlib import Path

import numpy as np

# Garante que aws_pipeline_clientes.py está no path
sys.path.insert(0, str(Path(__file__).parent))

from aws_pipeline_clientes import (
    gerar_dados_sinteticos,
    executar_clustering,
    _enriquecer_perfis,
    indexar_digital_twins,
    criar_indice_opensearch,
    salvar_pkl_s3,
    FEATURES,
    N_CLUSTERS,
    S3_BUCKET,
    S3_PREFIX,
    OPENSEARCH_ENDPOINT,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gerar-clustering")

PKL_LOCAL = Path("modelo_clustering_slim.pkl")


def _gerar_docs_cluster(cluster_id, perfil):
    from langchain_core.documents import Document
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


def main():
    log.info("Gerando %d clientes sintéticos...", 1000)
    df = gerar_dados_sinteticos(1000)

    log.info("Executando K-Means (%d clusters)...", N_CLUSTERS)
    df, kmeans, scaler, perfis = executar_clustering(df)
    perfis = _enriquecer_perfis(perfis)

    log.info("Segmentos encontrados:\n%s", perfis[["segmento", "n"]].to_string())

    # PKL slim: só numpy arrays + metadata — sem sklearn em Lambda
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
        log.info("Carregando modelo de embeddings HuggingFace (all-MiniLM-L6-v2)...")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=40)

        log.info("Indexando digital twins no OpenSearch...")
        indexar_digital_twins(df, embeddings)

        log.info("Indexando RAG de segmentos no OpenSearch...")
        for cid in perfis.index:
            docs = _gerar_docs_cluster(int(cid), perfis.loc[cid])
            chunks = splitter.split_documents(docs)
            criar_indice_opensearch(int(cid), chunks, embeddings)
    else:
        log.warning(
            "OPENSEARCH_ENDPOINT não definido — indexação OpenSearch ignorada. "
            "Defina a variável para indexar."
        )

    if S3_BUCKET:
        log.info("Salvando PKL slim no S3: s3://%s/%s", S3_BUCKET, S3_PREFIX + "modelo_clustering_slim.pkl")
        salvar_pkl_s3(slim, "modelo_clustering_slim.pkl")
    else:
        log.warning(
            "S3_BUCKET não definido — PKL não enviado ao S3. "
            "Defina S3_BUCKET e execute novamente, ou faça upload manual de '%s'.",
            PKL_LOCAL,
        )

    log.info("=== Concluído ===")
    log.info("Próximos passos:")
    if not use_opensearch:
        log.info("  1. Crie o domínio OpenSearch via terraform apply")
        log.info("  2. Execute: OPENSEARCH_ENDPOINT=... S3_BUCKET=... python gerar_clustering.py")
    if not S3_BUCKET:
        log.info("  3. Defina S3_BUCKET e execute novamente")
    log.info("  4. O Worker Lambda carregará o PKL slim do S3 automaticamente no cold start.")


if __name__ == "__main__":
    main()
