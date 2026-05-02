"""Validações Sprint A — executa sem AWS."""
import os, json, asyncio, numpy as np, faiss

# ── V2: FAISS offline ─────────────────────────────────────────────────────────
def test_faiss():
    d = 1536
    index = faiss.IndexFlatL2(d)
    docs = [
        "Clientes conservadores priorizam liquidez diaria.",
        "Fundos de renda fixa possuem menor volatilidade.",
        "Acoes de crescimento exigem horizonte de longo prazo.",
        "Titulos do Tesouro Direto sao garantidos pelo governo federal.",
        "CDBs oferecem retorno atrelado ao CDI com protecao do FGC.",
    ]
    # embeddings mock: hash deterministico
    vecs = np.array([
        [float(ord(c) % 17) / 17 for _ in range(d)]
        for c in [s[0] for s in docs]
    ], dtype="float32")
    index.add(vecs)
    q = vecs[0:1].copy()
    q[0, 0] += 0.01  # pequena perturbacao
    D, I = index.search(q, 3)
    assert index.ntotal == 5, "Deve ter 5 vetores"
    assert I[0][0] == 0, "Doc mais próximo deve ser o proprio"
    print(f"[V2] FAISS OK — {index.ntotal} vetores, top-3 indices: {I[0].tolist()}")

    # verificar índice persistido
    idx_path = "faiss_index/index.faiss"
    if os.path.exists(idx_path):
        idx2 = faiss.read_index(idx_path)
        print(f"[V2] faiss_index local: {idx2.ntotal} vetores ({os.path.getsize(idx_path)} bytes)")
    else:
        print("[V2] faiss_index/index.faiss nao encontrado (esperado em ambiente novo)")

# ── V3: agente usa tool MCP (simulado sem LangGraph) ─────────────────────────
async def test_mcp_tools():
    from mcp_mock_server import call_tool, list_tools
    tools = await list_tools()
    nomes = [t.name for t in tools]
    assert set(nomes) == {"executar_query", "listar_tabelas", "descrever_tabela"}

    r = await call_tool("executar_query", {"tabela": "pedidos", "filtro": {"status": "entregue"}})
    data = json.loads(r[0].text)
    assert len(data) == 2, f"Esperado 2 pedidos entregues, obtido {len(data)}"

    r2 = await call_tool("descrever_tabela", {"tabela": "produtos"})
    schema = json.loads(r2[0].text)
    assert "colunas" in schema
    print(f"[V3] MCP tools OK — {len(nomes)} ferramentas, {len(data)} pedidos entregues, schema produtos: {len(schema['colunas'])} colunas")

# ── V4: otel_config importa silenciosamente sem credenciais ──────────────────
def test_otel():
    try:
        import importlib, sys
        # garantir que nao ha chaves no ambiente
        os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
        os.environ.pop("LANGFUSE_SECRET_KEY", None)
        sys.path.insert(0, str(os.path.join(os.path.dirname(__file__),
                                            "infraestrutura/modules/lambda/src")))
        spec = importlib.util.spec_from_file_location(
            "otel_config",
            "infraestrutura/modules/lambda/src/otel_config.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print("[V4] otel_config importado OK (modo silencioso sem chaves Langfuse)")
    except Exception as e:
        print(f"[V4] otel_config FALHOU: {e}")

# ── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Sprint A — Validações")
    print("=" * 60)
    test_faiss()
    asyncio.run(test_mcp_tools())
    test_otel()
    print("=" * 60)
    print("Todas as validações concluídas.")
