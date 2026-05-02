"""
Golden Dataset ? Criacao, execucao e regressao de qualidade (loop externo ? Cap. 14).

Fluxo:
  1. Carregar golden dataset (JSONL com pares pergunta/resposta esperada + metadados)
  2. Executar o agente atual contra cada caso
  3. Avaliar com ROUGE-L e/ou LLM Judge
  4. Comparar com baseline anterior e exibir diff de regressao

Estrutura de um item do golden dataset:
  {
    "id": "GD-001",
    "segmento": "PF",
    "categoria": "investimentos",
    "pergunta": "Qual o melhor investimento para perfil conservador?",
    "resposta_esperada": "Para perfil conservador, recomendamos Tesouro Selic...",
    "threshold_rouge": 0.4,
    "threshold_judge": 7
  }

Uso offline (mock):
  python golden_dataset.py --modo criar   # gera golden_dataset_sample.jsonl
  python golden_dataset.py --modo rodar   # executa regressao mock
  python golden_dataset.py --modo diff --baseline resultados_v1.json --atual resultados_v2.json
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Optional
from avaliar_metricas import rouge_l
from llm_judge import _mock_judge


# ?? Dataset de exemplo ????????????????????????????????????????????????????????

GOLDEN_SAMPLE = [
    {
        "id": "GD-001", "segmento": "PF", "categoria": "investimentos",
        "pergunta": "Qual o melhor investimento para perfil conservador?",
        "resposta_esperada": "Para perfil conservador, recomendamos Tesouro Selic com liquidez diaria e CDB com protecao do FGC.",
        "threshold_rouge": 0.35, "threshold_judge": 7,
    },
    {
        "id": "GD-002", "segmento": "PF", "categoria": "cartao",
        "pergunta": "Quais sao os beneficios do cartao gold?",
        "resposta_esperada": "O cartao gold oferece programa de pontos, seguro viagem e isencao de anuidade para clientes premium.",
        "threshold_rouge": 0.30, "threshold_judge": 7,
    },
    {
        "id": "GD-003", "segmento": "PJ", "categoria": "credito",
        "pergunta": "Como solicitar capital de giro para minha empresa?",
        "resposta_esperada": "Empresas podem solicitar capital de giro via conta PJ com analise de faturamento dos ultimos 3 meses.",
        "threshold_rouge": 0.30, "threshold_judge": 7,
    },
    {
        "id": "GD-004", "segmento": "FP", "categoria": "investimentos",
        "pergunta": "Quais produtos sao indicados para private banking?",
        "resposta_esperada": "Clientes FP tem acesso a fundos exclusivos, COE estruturado e gestao de patrimonio personalizada.",
        "threshold_rouge": 0.30, "threshold_judge": 7,
    },
]

# Respostas simuladas do agente (para demo offline)
_RESPOSTAS_AGENTE_MOCK = {
    "GD-001": "Para clientes conservadores, Tesouro Selic e a opcao mais indicada pela liquidez imediata.",
    "GD-002": "O cartao gold da pontos a cada compra e tem seguro viagem incluido.",
    "GD-003": "Para capital de giro, analisamos o faturamento da empresa nos ultimos meses.",
    "GD-004": "Private banking oferece fundos exclusivos e gestao personalizada do patrimonio.",
}


# ?? Estrutura de resultado ????????????????????????????????????????????????????

@dataclass
class ResultadoCaso:
    id: str
    segmento: str
    categoria: str
    rouge_l: float
    judge_score: Optional[int]
    aprovado_rouge: bool
    aprovado_judge: bool
    aprovado: bool
    resposta_gerada: str


# ?? Criacao do golden dataset ?????????????????????????????????????????????????

def criar_dataset(caminho: str = "golden_dataset.jsonl"):
    with open(caminho, "w", encoding="utf-8") as f:
        for item in GOLDEN_SAMPLE:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[golden_dataset] Dataset criado: {caminho} ({len(GOLDEN_SAMPLE)} casos)")


# ?? Execucao de regressao ?????????????????????????????????????????????????????

def rodar_regressao(caminho_dataset: str = "golden_dataset.jsonl",
                    usar_bedrock: bool = False) -> list[ResultadoCaso]:
    """
    Para cada caso do golden dataset:
      1. Obtem resposta do agente (mock offline ou real)
      2. Calcula ROUGE-L vs resposta esperada
      3. Executa LLM Judge (mock ou Bedrock)
      4. Verifica se passou nos thresholds
    """
    resultados = []
    with open(caminho_dataset, encoding="utf-8") as f:
        casos = [json.loads(l) for l in f]

    for caso in casos:
        cid = caso["id"]
        # obter resposta do agente
        if usar_bedrock:
            resposta_gerada = _chamar_agente_bedrock(caso["pergunta"], caso["segmento"])
        else:
            resposta_gerada = _RESPOSTAS_AGENTE_MOCK.get(cid, "Resposta nao disponivel.")

        # avaliar ROUGE-L
        rl = rouge_l(caso["resposta_esperada"], resposta_gerada)
        aprovado_rouge = rl >= caso.get("threshold_rouge", 0.3)

        # avaliar LLM Judge
        if usar_bedrock:
            from llm_judge import julgar
            v = julgar(caso["pergunta"], resposta_gerada, segmento=caso["segmento"])
        else:
            v = _mock_judge(caso["segmento"])
        aprovado_judge = v.score_total >= caso.get("threshold_judge", 7)

        resultados.append(ResultadoCaso(
            id=cid,
            segmento=caso["segmento"],
            categoria=caso["categoria"],
            rouge_l=round(rl, 4),
            judge_score=v.score_total,
            aprovado_rouge=aprovado_rouge,
            aprovado_judge=aprovado_judge,
            aprovado=aprovado_rouge and aprovado_judge,
            resposta_gerada=resposta_gerada,
        ))

    return resultados


def _chamar_agente_bedrock(pergunta: str, segmento: str) -> str:
    """Stub ? substituir pelo invoke real do agente LangGraph em producao."""
    raise NotImplementedError("Integracao com agente Bedrock nao implementada aqui. Use aws_pipeline_clientes.py.")


# ?? Diff de regressao ?????????????????????????????????????????????????????????

def diff_regressao(baseline: list[dict], atual: list[dict]) -> dict:
    """
    Compara dois conjuntos de resultados e identifica:
      - Regressoes: casos que passaram no baseline e falharam no atual
      - Melhorias: casos que falharam no baseline e passaram no atual
      - Estavel: sem mudanca
    """
    base_map = {r["id"]: r for r in baseline}
    atual_map = {r["id"]: r for r in atual}

    regressoes, melhorias, estavel = [], [], []
    for cid, r_atual in atual_map.items():
        r_base = base_map.get(cid)
        if r_base is None:
            continue
        if r_base["aprovado"] and not r_atual["aprovado"]:
            delta_rouge = round(r_atual["rouge_l"] - r_base["rouge_l"], 4)
            regressoes.append({"id": cid, "delta_rouge": delta_rouge,
                                "judge_base": r_base["judge_score"],
                                "judge_atual": r_atual["judge_score"]})
        elif not r_base["aprovado"] and r_atual["aprovado"]:
            melhorias.append({"id": cid})
        else:
            estavel.append(cid)

    total = len(atual_map)
    aprovados = sum(1 for r in atual_map.values() if r["aprovado"])
    return {
        "resumo": {
            "total": total,
            "aprovados": aprovados,
            "taxa_aprovacao": round(aprovados / total, 3) if total else 0,
        },
        "regressoes": regressoes,
        "melhorias": melhorias,
        "estavel": estavel,
    }


# ?? CLI ???????????????????????????????????????????????????????????????????????

def _imprimir_resultados(resultados: list[ResultadoCaso]):
    print(f"\n{'ID':<10} {'Seg':<5} {'Cat':<15} {'ROUGE-L':>8} {'Judge':>6} {'Status':>10}")
    print("-" * 62)
    for r in resultados:
        status = "? PASS" if r.aprovado else "? FAIL"
        print(f"{r.id:<10} {r.segmento:<5} {r.categoria:<15} {r.rouge_l:>8.4f} "
              f"{str(r.judge_score):>6} {status:>10}")
    aprovados = sum(1 for r in resultados if r.aprovado)
    print(f"\nTotal: {aprovados}/{len(resultados)} aprovados "
          f"({100*aprovados//len(resultados)}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Golden Dataset ? regressao de qualidade")
    parser.add_argument("--modo", choices=["criar", "rodar", "diff"],
                        default="rodar")
    parser.add_argument("--dataset", default="golden_dataset.jsonl")
    parser.add_argument("--saida", default="resultados_golden.json")
    parser.add_argument("--baseline", help="JSON de baseline (modo diff)")
    parser.add_argument("--atual", help="JSON atual (modo diff)")
    parser.add_argument("--bedrock", action="store_true",
                        help="Usar Bedrock (padrao: mock offline)")
    args = parser.parse_args()

    if args.modo == "criar":
        criar_dataset(args.dataset)

    elif args.modo == "rodar":
        if not os.path.exists(args.dataset):
            print(f"Dataset nao encontrado: {args.dataset}. Criando sample...")
            criar_dataset(args.dataset)
        resultados = rodar_regressao(args.dataset, usar_bedrock=args.bedrock)
        _imprimir_resultados(resultados)
        with open(args.saida, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in resultados], f, ensure_ascii=False, indent=2)
        print(f"\nResultados salvos em: {args.saida}")

    elif args.modo == "diff":
        if not args.baseline or not args.atual:
            parser.error("--baseline e --atual sao obrigatorios no modo diff")
        with open(args.baseline, encoding="utf-8") as f:
            base = json.load(f)
        with open(args.atual, encoding="utf-8") as f:
            atual = json.load(f)
        resultado_diff = diff_regressao(base, atual)
        print(json.dumps(resultado_diff, ensure_ascii=False, indent=2))
