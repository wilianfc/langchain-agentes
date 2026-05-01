"""
Testes unitários para o índice de confiabilidade do pipeline RAG.

Cobre:
  - _palavras_chave: filtragem de stopwords e tokens curtos
  - _confiabilidade: scoring por cobertura de fontes e sobreposição léxica
  - _avaliar_llm: LLM-as-judge (Bedrock mockado)
  - documentos_knowledge: quarta fonte no índice de confiabilidade

Para isolar as funções puras do worker sem depender de credenciais AWS,
o módulo otel_config é substituído por um stub antes do import.
"""
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.modules.setdefault("otel_config", MagicMock())

os.environ.setdefault("DYNAMODB_TABLE", "test-table")
os.environ.setdefault("AWS_REGION", "sa-east-1")
os.environ.setdefault("BEDROCK_REGION", "us-east-1")

_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "infraestrutura", "modules", "lambda", "src")
)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import worker  # noqa: E402


class TestPalavrasChave:
    def test_filtra_stopwords_pt(self):
        tokens = worker._palavras_chave("o cliente não tem dívidas mensais")
        assert "cliente" in tokens
        assert "dívidas" in tokens
        assert "o" not in tokens
        assert "não" not in tokens
        assert "tem" not in tokens

    def test_filtra_tokens_curtos(self):
        tokens = worker._palavras_chave("renda alta bom score mensal")
        assert "renda" in tokens
        assert "score" in tokens
        assert "mensal" in tokens
        assert "alta" not in tokens
        assert "bom" not in tokens

    def test_remove_pontuacao_lateral(self):
        tokens = worker._palavras_chave("investimento, patrimônio; previdência.")
        assert "investimento" in tokens
        assert "patrimônio" in tokens
        assert "previdência" in tokens
        assert not any(c in t for t in tokens for c in ".,;:!?()")

    def test_normaliza_para_lowercase(self):
        tokens = worker._palavras_chave("Tesouro DIRETO Selic Previdência")
        assert "tesouro" in tokens
        assert "direto" in tokens
        assert "selic" in tokens
        assert "previdência" in tokens
        tokens_ipca = worker._palavras_chave("Tesouro IPCA")
        assert "ipca" not in tokens_ipca  # 4 chars — abaixo do limiar

    def test_texto_vazio_retorna_set_vazio(self):
        assert worker._palavras_chave("") == set()

    def test_texto_so_stopwords(self):
        assert worker._palavras_chave("o a de do da em no na e ou") == set()


class TestCoberturaFontes:
    def test_sem_contexto_score_zero(self):
        r = worker._confiabilidade("", "", "", "Recomendo diversificar os investimentos.")
        assert r["score"] == pytest.approx(0.0)
        assert r["fontes_ativas"] == []
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.0)

    def test_apenas_bm25_contribui_040(self):
        r = worker._confiabilidade("Perfil Premium Conservador renda mensal", "", "", "resposta")
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.40)
        assert r["fontes_ativas"] == ["opensearch_bm25"]

    def test_apenas_neptune_live_contribui_030(self):
        r = worker._confiabilidade("", "", "Produtos recomendados para segmento", "resposta")
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.30)
        assert r["fontes_ativas"] == ["neptune_live"]

    def test_apenas_neptune_sync_contribui_015(self):
        r = worker._confiabilidade("", "Grafo replicado segmento cluster", "", "resposta")
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.15)
        assert r["fontes_ativas"] == ["neptune_sync"]

    def test_bm25_mais_neptune_live(self):
        r = worker._confiabilidade(
            "Perfil Premium Conservador renda mensal",
            "",
            "Produtos recomendados Tesouro IPCA",
            "resposta",
        )
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.70)
        assert set(r["fontes_ativas"]) == {"opensearch_bm25", "neptune_live"}

    def test_todas_as_tres_fontes(self):
        r = worker._confiabilidade(
            "contexto bm25 longo texto",
            "contexto sync replicado grafo",
            "contexto neptune live produtos",
            "resposta qualquer",
        )
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.85)
        assert set(r["fontes_ativas"]) == {"opensearch_bm25", "neptune_sync", "neptune_live"}

    def test_whitespace_nao_conta_como_fonte(self):
        r = worker._confiabilidade("   ", "\n\n", "\t", "resposta")
        assert r["fontes_ativas"] == []
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.0)


class TestSobreposicaoLexica:
    def test_overlap_alto_quando_contexto_aparece_na_resposta(self):
        contexto = "investimento tesouro previdência selic patrimônio diversificação"
        resposta = "recomendo investimento tesouro previdência selic patrimônio diversificação"
        r = worker._confiabilidade(contexto, "", "", resposta)
        assert r["detalhes"]["sobreposicao_lexica"] > 0.70

    def test_overlap_zero_sem_termos_comuns(self):
        contexto = "xilofone maracujá fibonacci arquipélago quadrilátero"
        resposta = "totalmente diferente nenhuma palavra igual alguma outra"
        r = worker._confiabilidade(contexto, "", "", resposta)
        assert r["detalhes"]["sobreposicao_lexica"] == pytest.approx(0.0)

    def test_overlap_nao_excede_1(self):
        texto = "investimento tesouro previdência selic patrimônio " * 20
        r = worker._confiabilidade(texto, texto, texto, texto)
        assert r["detalhes"]["sobreposicao_lexica"] <= 1.0

    def test_overlap_zero_sem_contexto(self):
        r = worker._confiabilidade("", "", "", "resposta sem contexto algum")
        assert r["detalhes"]["sobreposicao_lexica"] == pytest.approx(0.0)

    def test_bonus_overlap_aumenta_score_sobre_cobertura(self):
        ctx = "investimento tesouro previdência selic patrimônio"
        resp_com_overlap = "recomendo investimento tesouro previdência para patrimônio"
        resp_sem_overlap = "consulte profissional habilitado antes qualquer decisão"
        r_com = worker._confiabilidade(ctx, "", "", resp_com_overlap)
        r_sem = worker._confiabilidade(ctx, "", "", resp_sem_overlap)
        assert r_com["score"] > r_sem["score"]


class TestNiveisELimites:
    def test_nivel_alto_bm25_e_neptune(self):
        r = worker._confiabilidade(
            "perfil cliente renda mensal saldo", "", "produtos recomendados segmento", "resposta"
        )
        assert r["nivel"] == "alto"
        assert r["score"] >= 0.70

    def test_nivel_medio_apenas_bm25(self):
        r = worker._confiabilidade(
            "perfil cliente renda mensal saldo segmento", "", "", "resposta completamente diferente"
        )
        assert r["nivel"] == "medio"
        assert 0.40 <= r["score"] < 0.70

    def test_nivel_baixo_sem_contexto(self):
        r = worker._confiabilidade("", "", "", "resposta sem contexto")
        assert r["nivel"] == "baixo"
        assert r["score"] < 0.40

    def test_score_nao_excede_1_com_tudo_maximo(self):
        ctx = "investimento tesouro previdência selic patrimônio " * 30
        r = worker._confiabilidade(ctx, ctx, ctx, ctx)
        assert r["score"] <= 1.0

    def test_score_e_float_arredondado(self):
        r = worker._confiabilidade("contexto aqui texto", "", "", "resposta")
        assert isinstance(r["score"], float)
        assert r["score"] == round(r["score"], 2)

    def test_fontes_ativas_sem_duplicatas(self):
        r = worker._confiabilidade("bm25 texto", "sync texto", "graph texto", "resposta")
        assert len(r["fontes_ativas"]) == len(set(r["fontes_ativas"]))

    def test_estrutura_completa_do_retorno(self):
        r = worker._confiabilidade("contexto", "", "", "resposta")
        assert set(r.keys()) == {"score", "nivel", "fontes_ativas", "detalhes"}
        assert set(r["detalhes"].keys()) == {"cobertura_fontes", "sobreposicao_lexica"}
        assert isinstance(r["score"], float)
        assert r["nivel"] in {"alto", "medio", "baixo"}
        assert isinstance(r["fontes_ativas"], list)
        assert isinstance(r["detalhes"]["cobertura_fontes"], float)
        assert isinstance(r["detalhes"]["sobreposicao_lexica"], float)


class TestCenariosReais:
    """Fixtures inspiradas no schema do grafo Neptune e perfis do modelo."""

    BM25_PREMIUM = (
        "Perfil Premium Conservador: 87 clientes, idade média 54 anos, renda R$ 19.000/mês, "
        "saldo R$ 142.000, score 835, inadimplência 0.3%, uso digital 41%."
    )
    NEPTUNE_PREMIUM = (
        "Produtos recomendados para 'Premium Conservador': Tesouro IPCA+, PGBL, Conta Platinum. "
        "Persona arquétipo: Carlos, gerente, 52 anos. Perfil conservador e patrimonial."
    )

    def test_segmento_premium_score_alto(self):
        resposta = (
            "Para o cliente Premium Conservador com saldo de R$ 142.000 e score 835, "
            "recomendo PGBL com aporte em Tesouro IPCA+ para proteção patrimonial de longo prazo."
        )
        r = worker._confiabilidade(self.BM25_PREMIUM, "", self.NEPTUNE_PREMIUM, resposta)
        assert r["nivel"] == "alto"
        assert r["score"] >= 0.70
        assert "opensearch_bm25" in r["fontes_ativas"]
        assert "neptune_live" in r["fontes_ativas"]

    def test_resposta_generica_score_medio(self):
        resposta = "Consulte um assessor financeiro para orientações personalizadas sobre investimentos."
        r = worker._confiabilidade(self.BM25_PREMIUM, "", self.NEPTUNE_PREMIUM, resposta)
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.70)
        assert r["detalhes"]["sobreposicao_lexica"] < 0.20

    def test_sem_opensearch_sem_neptune_score_baixo(self):
        """Degradação total: ambas as fontes falham em runtime (timeout/erro de rede).
        Resposta gerada apenas com conhecimento paramétrico do LLM — score zero."""
        r = worker._confiabilidade("", "", "", "Recomendo diversificar o portfólio do cliente.")
        assert r["nivel"] == "baixo"
        assert r["score"] == pytest.approx(0.0)
        assert r["fontes_ativas"] == []

    def test_twin_apenas_neptune_bm25_vazio(self):
        """Degradação parcial: cliente ausente no índice OpenSearch (BM25 vazio).
        Era o comportamento de GRAPH-C* antes do indexar_twins_graph.py.
        Sem BM25, cobertura máxima é 0.30 — score nunca atinge 'alto'."""
        graph_apenas = (
            "Produtos recomendados para 'Premium Conservador': Tesouro IPCA+, PGBL. "
            "Clientes similares: GRAPH-C00-0007 (score 720, renda R$ 5.000)."
        )
        resposta = (
            "Considerando PGBL e Tesouro IPCA+ para proteção patrimonial de longo prazo, "
            "seguindo perfil de clientes similares do segmento."
        )
        r = worker._confiabilidade("", "", graph_apenas, resposta)
        assert "opensearch_bm25" not in r["fontes_ativas"]
        assert "neptune_live" in r["fontes_ativas"]
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.30)
        assert r["nivel"] != "alto"  # sem BM25, score máximo é 0.45 — nunca "alto"

    def test_twin_indexado_ambas_fontes(self):
        """Estado correto pós-fix: GRAPH-C* indexados no OpenSearch.
        BM25 traz perfil individual; Neptune traz produtos + similares.
        Ambas as fontes ativas garantem score alto."""
        bm25 = (
            "Perfil individual do cliente GRAPH-C00-0001:\n"
            "- Segmento: Premium Conservador\n"
            "- Idade: 43 anos\n"
            "- Renda mensal: R$ 4.685\n"
            "- Score de crédito: 720\n"
            "- Canal preferencial: digital (app/internet banking)\n"
            "- Histórico: adimplente, sem pendências"
        )
        neptune = (
            "Produtos recomendados para 'Premium Conservador': Tesouro IPCA+, PGBL, Conta Platinum. "
            "Clientes similares no grafo: GRAPH-C00-0007 (score 718, renda R$ 4.900)."
        )
        resposta = (
            "Com 43 anos e renda de R$ 4.685, faz sentido destinar parte para PGBL. "
            "Clientes similares no segmento Premium Conservador optaram por Tesouro IPCA+ "
            "para proteção patrimonial de longo prazo."
        )
        r = worker._confiabilidade(bm25, "", neptune, resposta)
        assert r["nivel"] == "alto"
        assert set(r["fontes_ativas"]) == {"opensearch_bm25", "neptune_live"}
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.70)
        assert r["detalhes"]["sobreposicao_lexica"] > 0.10

    def test_twin_com_clientes_similares(self):
        graph_twin = (
            "Produtos recomendados para 'Jovem Digital': Cartão Cashback, Conta CDI. "
            "Clientes similares no grafo: Cliente GRAPH-C01-0003 (score 640, renda R$ 3.200); "
            "Cliente GRAPH-C01-0007 (score 615, renda R$ 2.900)."
        )
        bm25_twin = (
            "Cliente digital twin: score 630, renda R$ 3.000, canal app, adimplente. "
            "Segmento Jovem Digital, prefere cashback e gestão mobile."
        )
        resposta = (
            "Com score 630 similar aos clientes do meu cluster, o cashback faz sentido para minha renda. "
            "Prefiro gestão pelo app — o cartão CDI seria ideal para mim."
        )
        r = worker._confiabilidade(bm25_twin, "", graph_twin, resposta)
        assert r["nivel"] == "alto"
        assert r["detalhes"]["sobreposicao_lexica"] > 0.10


class TestDocumentosKnowledge:
    """Quarta fonte RAG: documentos-knowledge (+0.10 na cobertura)."""

    def test_documentos_contribui_010(self):
        r = worker._confiabilidade("", "", "", "resposta", documentos="Política investimentos 2025 fundos")
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.10)
        assert r["fontes_ativas"] == ["documentos_knowledge"]

    def test_documentos_mais_bm25(self):
        r = worker._confiabilidade("perfil cliente renda mensal", "", "", "resposta",
                                   documentos="Regulamento fundos tesouro")
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.50)
        assert set(r["fontes_ativas"]) == {"opensearch_bm25", "documentos_knowledge"}

    def test_todas_quatro_fontes_cobertura_095(self):
        r = worker._confiabilidade(
            "perfil segmento renda mensal",
            "grafo replicado cluster",
            "produtos neptune tesouro",
            "resposta",
            documentos="regulamento investimentos fundos",
        )
        assert r["detalhes"]["cobertura_fontes"] == pytest.approx(0.95)
        assert set(r["fontes_ativas"]) == {
            "opensearch_bm25", "neptune_sync", "neptune_live", "documentos_knowledge"
        }

    def test_documentos_vazio_nao_conta(self):
        r = worker._confiabilidade("bm25 texto", "", "", "resposta", documentos="")
        assert "documentos_knowledge" not in r["fontes_ativas"]

    def test_documentos_whitespace_nao_conta(self):
        r = worker._confiabilidade("bm25 texto", "", "", "resposta", documentos="   \n\t")
        assert "documentos_knowledge" not in r["fontes_ativas"]

    def test_score_nao_excede_1_com_quatro_fontes(self):
        ctx = "investimento tesouro previdência selic patrimônio " * 20
        r = worker._confiabilidade(ctx, ctx, ctx, ctx, documentos=ctx)
        assert r["score"] <= 1.0

    def test_documentos_contribui_para_overlap(self):
        docs = "investimento tesouro previdência selic patrimônio"
        resposta = "recomendo investimento tesouro previdência para proteção patrimonial"
        r_com = worker._confiabilidade("", "", "", resposta, documentos=docs)
        r_sem = worker._confiabilidade("", "", "", resposta)
        assert r_com["detalhes"]["sobreposicao_lexica"] > 0
        assert r_sem["detalhes"]["sobreposicao_lexica"] == pytest.approx(0.0)


class TestAvaliarLlm:
    """_avaliar_llm: LLM-as-judge com Bedrock mockado."""

    def _mock_bedrock_response(self, payload: dict) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp["output"]["message"]["content"][0]["text"] = json.dumps(payload)
        return mock_resp

    def test_retorna_scores_e_media(self):
        resposta_llm = {"relevancia": 8, "fidelidade": 7, "completude": 9,
                        "raciocinio": "Resposta bem fundamentada no contexto RAG."}
        with patch.object(worker._bedrock_client, "converse") as mock_converse:
            mock_converse.return_value = {
                "output": {"message": {"content": [{"text": json.dumps(resposta_llm)}]}}
            }
            r = worker._avaliar_llm("contexto rag aqui", "pergunta teste", "resposta gerada")

        assert r["disponivel"] is True
        assert r["relevancia"] == 8
        assert r["fidelidade"] == 7
        assert r["completude"] == 9
        assert r["media"] == pytest.approx(8.0)
        assert "raciocinio" in r

    def test_media_calculada_corretamente(self):
        resposta_llm = {"relevancia": 6, "fidelidade": 9, "completude": 3, "raciocinio": "x"}
        with patch.object(worker._bedrock_client, "converse") as mock_converse:
            mock_converse.return_value = {
                "output": {"message": {"content": [{"text": json.dumps(resposta_llm)}]}}
            }
            r = worker._avaliar_llm("ctx", "q", "resp")

        assert r["media"] == pytest.approx(6.0)

    def test_retorna_disponivel_false_se_bedrock_falha(self):
        with patch.object(worker._bedrock_client, "converse", side_effect=Exception("timeout")):
            r = worker._avaliar_llm("contexto", "pergunta", "resposta")

        assert r["disponivel"] is False

    def test_retorna_disponivel_false_se_json_invalido(self):
        with patch.object(worker._bedrock_client, "converse") as mock_converse:
            mock_converse.return_value = {
                "output": {"message": {"content": [{"text": "não é json válido"}]}}
            }
            r = worker._avaliar_llm("ctx", "q", "resp")

        assert r["disponivel"] is False
