"""
Ingere um documento de texto no pipeline GraphRAG:
  1. Chunking do texto em parágrafos
  2. Extração de entidades/relacionamentos via Bedrock (LLM)
  3. MERGE das entidades no Neptune via proxy Lambda
  4. Indexação dos chunks no índice OpenSearch 'documentos-knowledge' (BM25)

Uso:
  AWS_REGION=sa-east-1 python indexar_documento.py \
      --titulo "Política de Investimentos 2025" \
      --arquivo politica_investimentos.txt

  Ou passando o texto diretamente:
  python indexar_documento.py --titulo "FAQ Tesouro Direto" --texto "..."

Requer: boto3, opensearch-py, requests-aws4auth
"""
import argparse
import json
import os
import re
import sys
import textwrap
import traceback

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers
from requests_aws4auth import AWS4Auth

OPENSEARCH_ENDPOINT = os.environ.get(
    "OPENSEARCH_ENDPOINT",
    "search-langchain-agent-dev-ujstn5xeniamxdbr4rhh7qgmbu.sa-east-1.es.amazonaws.com",
)
AWS_REGION = os.environ.get("AWS_REGION", "sa-east-1")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250514-v1:0"
)
NEPTUNE_PROXY_FUNCTION = os.environ.get("NEPTUNE_PROXY_FUNCTION", "")
DOC_INDEX = "documentos-knowledge"
ENTREVISTAS_INDEX = "entrevistas-clientes"
CHUNK_SIZE = 400  # palavras por chunk


def _aws_auth() -> AWS4Auth:
    sess = boto3.session.Session()
    creds = sess.get_credentials().get_frozen_credentials()
    return AWS4Auth(creds.access_key, creds.secret_key, AWS_REGION, "es",
                    session_token=creds.token)


def _os_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=_aws_auth(),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def _bedrock_client():
    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _neptune_proxy(cypher: str) -> list:
    if not NEPTUNE_PROXY_FUNCTION:
        return []
    lam = boto3.client("lambda", region_name=AWS_REGION)
    resp = lam.invoke(
        FunctionName=NEPTUNE_PROXY_FUNCTION,
        InvocationType="RequestResponse",
        Payload=json.dumps({"cypher": cypher}),
    )
    return json.loads(resp["Payload"].read()) or []


def chunkar(texto: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Divide o texto em chunks de ~chunk_size palavras respeitando parágrafos."""
    paragrafos = [p.strip() for p in re.split(r"\n{2,}", texto) if p.strip()]
    chunks, atual = [], []
    contagem = 0
    for par in paragrafos:
        palavras = len(par.split())
        if contagem + palavras > chunk_size and atual:
            chunks.append("\n\n".join(atual))
            atual, contagem = [], 0
        atual.append(par)
        contagem += palavras
    if atual:
        chunks.append("\n\n".join(atual))
    return chunks


def extrair_entidades(titulo: str, chunk: str) -> dict:
    """Usa o LLM para extrair entidades e relacionamentos do chunk."""
    prompt = textwrap.dedent(f"""
        Extraia entidades e relacionamentos do trecho abaixo para um grafo de conhecimento bancário.
        Responda APENAS com JSON válido, sem texto adicional.

        Documento: {titulo}
        Trecho: {chunk[:1500]}

        JSON esperado:
        {{
          "entidades": [
            {{"tipo": "Produto|Segmento|Regulacao|Conceito", "nome": "<nome>", "descricao": "<1 frase>"}}
          ],
          "relacionamentos": [
            {{"origem": "<nome>", "relacao": "<VERBO_CAPS>", "destino": "<nome>"}}
          ]
        }}
    """).strip()

    bedrock = _bedrock_client()
    resp = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 512},
    )
    texto = resp["output"]["message"]["content"][0]["text"]
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"entidades": [], "relacionamentos": []}


def merge_neptune(entidades: list, relacionamentos: list) -> None:
    """Faz MERGE das entidades e relacionamentos no Neptune via proxy Lambda."""
    if not NEPTUNE_PROXY_FUNCTION:
        print("  [Neptune] NEPTUNE_PROXY_FUNCTION não definido — pulando grafo.")
        return

    for ent in entidades:
        tipo = re.sub(r"[^A-Za-z]", "", ent.get("tipo", "Conceito"))
        nome = ent.get("nome", "").replace("'", "\\'")
        desc = ent.get("descricao", "").replace("'", "\\'")
        cypher = (
            f"MERGE (n:{tipo} {{nome: '{nome}'}}) "
            f"ON CREATE SET n.descricao = '{desc}' "
            f"ON MATCH SET n.descricao = '{desc}'"
        )
        try:
            _neptune_proxy(cypher)
        except Exception:
            print(f"  [Neptune] Erro ao inserir entidade '{nome}': {traceback.format_exc()[:200]}")

    for rel in relacionamentos:
        orig = rel.get("origem", "").replace("'", "\\'")
        dest = rel.get("destino", "").replace("'", "\\'")
        relacao = re.sub(r"[^A-Z_]", "", rel.get("relacao", "RELACIONADO_A").upper())
        cypher = (
            f"MATCH (a {{nome: '{orig}'}}), (b {{nome: '{dest}'}}) "
            f"MERGE (a)-[:{relacao}]->(b)"
        )
        try:
            _neptune_proxy(cypher)
        except Exception:
            print(f"  [Neptune] Erro ao inserir rel '{orig}'->{dest}: {traceback.format_exc()[:200]}")


def _garantir_indice(client: OpenSearch, index: str) -> None:
    if client.indices.exists(index=index):
        return
    client.indices.create(
        index=index,
        body={
            "settings": {"number_of_shards": 1, "number_of_replicas": 1},
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "metadata": {"type": "object", "dynamic": True},
                }
            },
        },
    )
    print(f"Indice '{index}' criado.")


def indexar_chunks(titulo: str, chunks: list[str], client: OpenSearch,
                   index: str = DOC_INDEX, meta_extra: dict = None) -> None:
    actions = [
        {
            "_index": index,
            "_source": {
                "text": chunk,
                "metadata": {"titulo": titulo, "chunk_idx": i, **(meta_extra or {})},
            },
        }
        for i, chunk in enumerate(chunks)
    ]
    success, errors = helpers.bulk(client, actions, raise_on_error=False)
    print(f"OpenSearch [{index}]: {success} chunks inseridos | erros: {len(errors) if isinstance(errors, list) else errors}")
    client.indices.refresh(index=index)


def main():
    parser = argparse.ArgumentParser(description="Ingere documento ou entrevista no pipeline GraphRAG.")
    parser.add_argument("--titulo", required=True, help="Título do documento")
    parser.add_argument(
        "--tipo", choices=["documento", "entrevista"], default="documento",
        help="'documento' → documentos-knowledge; 'entrevista' → entrevistas-clientes",
    )
    parser.add_argument("--cliente-id", default="", help="ID do cliente (entrevistas individuais, modo twin)")
    parser.add_argument("--cluster-id", type=int, default=None, help="Cluster ID (entrevistas de grupo, modo segmento/persona)")

    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--arquivo", help="Caminho para arquivo .txt")
    grupo.add_argument("--texto", help="Texto do documento diretamente")
    parser.add_argument("--sem-grafo", action="store_true", help="Pular extração de entidades Neptune")
    args = parser.parse_args()

    if args.arquivo:
        with open(args.arquivo, encoding="utf-8") as f:
            texto = f.read()
    else:
        texto = args.texto

    eh_entrevista = args.tipo == "entrevista"
    index = ENTREVISTAS_INDEX if eh_entrevista else DOC_INDEX

    meta_extra = {}
    if eh_entrevista:
        if args.cliente_id:
            meta_extra["cliente_id"] = args.cliente_id
        if args.cluster_id is not None:
            meta_extra["cluster_id"] = args.cluster_id
        if not meta_extra:
            parser.error("Entrevistas requerem --cliente-id ou --cluster-id.")

    print(f"Tipo: {args.tipo} | Índice: {index}")
    print(f"Documento: '{args.titulo}' ({len(texto)} chars)")
    chunks = chunkar(texto)
    print(f"Chunks gerados: {len(chunks)}")

    os_client = _os_client()
    _garantir_indice(os_client, index)

    # Extração de entidades Neptune apenas para documentos (não entrevistas)
    if not eh_entrevista and not args.sem_grafo:
        for i, chunk in enumerate(chunks):
            print(f"\n--- Chunk {i + 1}/{len(chunks)} — extraindo entidades ---")
            grafo = extrair_entidades(args.titulo, chunk)
            ents = grafo.get("entidades", [])
            rels = grafo.get("relacionamentos", [])
            print(f"  {len(ents)} entidades, {len(rels)} relacionamentos")
            merge_neptune(ents, rels)

    indexar_chunks(args.titulo, chunks, os_client, index=index, meta_extra=meta_extra)

    total = os_client.count(index=index)["count"]
    print(f"\nTotal de chunks em '{index}': {total}")


if __name__ == "__main__":
    main()
