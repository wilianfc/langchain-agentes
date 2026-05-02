"""
Avaliacao de metricas de qualidade de resposta (loop externo ? Cap. 12).

Metricas implementadas:
  - ROUGE-L  (sobreposicao de subsequencia mais longa)
  - BERTScore (similaridade semantica via embeddings)
  - G-Eval   (avaliacao LLM-based via Bedrock/Claude)

Uso sem AWS (offline):
  python avaliar_metricas.py --modo offline

Uso com Bedrock (G-Eval):
  python avaliar_metricas.py --modo geval \
    --referencia "Resposta esperada do sistema." \
    --candidata  "Resposta gerada pelo agente."
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Optional


# ?? Estrutura de resultado ????????????????????????????????????????????????????

@dataclass
class ResultadoAvaliacao:
    rouge_l: float
    bertscore_f1: Optional[float]
    geval_score: Optional[float]
    geval_razao: Optional[str]

    def resumo(self) -> str:
        linhas = [f"  ROUGE-L:      {self.rouge_l:.4f}"]
        if self.bertscore_f1 is not None:
            linhas.append(f"  BERTScore F1: {self.bertscore_f1:.4f}")
        if self.geval_score is not None:
            linhas.append(f"  G-Eval:       {self.geval_score:.2f}/5")
            if self.geval_razao:
                linhas.append(f"  Razao G-Eval: {self.geval_razao}")
        return "\n".join(linhas)


# ?? ROUGE-L (sem dependencia externa) ????????????????????????????????????????

def _lcs_length(a: list, b: list) -> int:
    """Comprimento da subsequencia comum mais longa."""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def rouge_l(referencia: str, candidata: str) -> float:
    """Retorna F1 do ROUGE-L entre referencia e candidata."""
    ref_tokens = referencia.lower().split()
    cand_tokens = candidata.lower().split()
    if not ref_tokens or not cand_tokens:
        return 0.0
    lcs = _lcs_length(ref_tokens, cand_tokens)
    precision = lcs / len(cand_tokens)
    recall = lcs / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ?? BERTScore (via transformers, opcional) ???????????????????????????????????

def bertscore_f1(referencia: str, candidata: str) -> Optional[float]:
    """
    Calcula BERTScore F1. Retorna None se bert_score nao estiver instalado.
    Instalar: pip install bert-score
    """
    try:
        from bert_score import score as bert_score_fn
        P, R, F1 = bert_score_fn(
            [candidata], [referencia],
            lang="pt",
            rescale_with_baseline=False,
            verbose=False,
        )
        return float(F1[0])
    except ImportError:
        return None
    except Exception as e:
        print(f"[AVISO] BERTScore falhou: {e}", file=sys.stderr)
        return None


# ?? G-Eval via Bedrock ????????????????????????????????????????????????????????

_GEVAL_PROMPT = """Voce e um avaliador especialista em sistemas de IA para bancos.

Avalie a RESPOSTA GERADA comparando com a RESPOSTA REFERENCIA nos criterios:
1. Fidelidade ao contexto (a resposta usa apenas informacoes disponiveis?)
2. Completude (cobre os pontos essenciais da referencia?)
3. Clareza (linguagem adequada para o cliente bancario?)
4. Ausencia de alucinacoes (sem informacoes inventadas?)
5. Conformidade LGPD (nao expoe dados pessoais indevidos?)

Responda SOMENTE em JSON com os campos:
  score: numero de 0 a 5 (inteiro)
  razao: string com justificativa em ate 2 frases

RESPOSTA REFERENCIA:
{referencia}

RESPOSTA GERADA:
{candidata}

JSON:"""


def geval(referencia: str, candidata: str, region: str = "us-east-1",
          model_id: str = "us.anthropic.claude-sonnet-4-5-20250514-v1:0") -> tuple[Optional[float], Optional[str]]:
    """
    Avaliacao G-Eval via Claude no Bedrock.
    Retorna (score, razao) ou (None, None) se Bedrock nao disponivel.
    """
    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=region)
        prompt = _GEVAL_PROMPT.format(referencia=referencia, candidata=candidata)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = client.invoke_model(modelId=model_id, body=body)
        text = json.loads(resp["body"].read())["content"][0]["text"].strip()
        # extrair JSON mesmo se vier com marcadores de bloco
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        data = json.loads(text)
        return float(data.get("score", 0)), data.get("razao", "")
    except Exception as e:
        print(f"[AVISO] G-Eval Bedrock indisponivel: {e}", file=sys.stderr)
        return None, None


# ?? Funcao principal de avaliacao ?????????????????????????????????????????????

def avaliar(referencia: str, candidata: str,
            usar_bertscore: bool = False,
            usar_geval: bool = False) -> ResultadoAvaliacao:
    rl = rouge_l(referencia, candidata)
    bs = bertscore_f1(referencia, candidata) if usar_bertscore else None
    gs, gr = geval(referencia, candidata) if usar_geval else (None, None)
    return ResultadoAvaliacao(rouge_l=rl, bertscore_f1=bs, geval_score=gs, geval_razao=gr)


# ?? Modo batch: avaliar arquivo JSONL ?????????????????????????????????????????

def avaliar_batch(caminho: str, usar_geval: bool = False) -> list[dict]:
    """
    Arquivo JSONL com linhas: {"id": ..., "referencia": ..., "candidata": ...}
    Retorna lista de dicionarios com metricas.
    """
    resultados = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            item = json.loads(linha.strip())
            r = avaliar(item["referencia"], item["candidata"], usar_geval=usar_geval)
            resultados.append({"id": item.get("id", "?"), **asdict(r)})
    return resultados


# ?? CLI ???????????????????????????????????????????????????????????????????????

def _demo_offline():
    pares = [
        ("Clientes conservadores priorizam liquidez diaria e seguranca do capital.",
         "Investidores conservadores preferem produtos com liquidez imediata."),
        ("O Tesouro Direto e garantido pelo governo federal.",
         "O Tesouro Direto oferece garantia do governo."),
        ("Fundos de renda variavel possuem alto risco.",
         "Poupanca e o investimento mais seguro do mercado."),
    ]
    print(f"{'Ref (trunc)':<45} {'Cand (trunc)':<45} {'ROUGE-L':>8}")
    print("-" * 103)
    for ref, cand in pares:
        rl = rouge_l(ref, cand)
        print(f"{ref[:43]:<45} {cand[:43]:<45} {rl:>8.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avaliacao de metricas de resposta RAG")
    parser.add_argument("--modo", choices=["offline", "geval", "batch"],
                        default="offline", help="Modo de execucao")
    parser.add_argument("--referencia", help="Texto de referencia (modo geval)")
    parser.add_argument("--candidata", help="Texto candidato (modo geval)")
    parser.add_argument("--arquivo", help="JSONL com pares (modo batch)")
    parser.add_argument("--bertscore", action="store_true", help="Incluir BERTScore")
    args = parser.parse_args()

    if args.modo == "offline":
        print("Demo ROUGE-L offline:")
        _demo_offline()

    elif args.modo == "geval":
        if not args.referencia or not args.candidata:
            parser.error("--referencia e --candidata sao obrigatorios no modo geval")
        resultado = avaliar(args.referencia, args.candidata,
                            usar_bertscore=args.bertscore, usar_geval=True)
        print(resultado.resumo())

    elif args.modo == "batch":
        if not args.arquivo:
            parser.error("--arquivo e obrigatorio no modo batch")
        resultados = avaliar_batch(args.arquivo, usar_geval=args.modo == "geval")
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
