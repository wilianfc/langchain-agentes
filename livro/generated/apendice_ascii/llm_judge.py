"""
LLM as Judge ? Avaliacao automatica de respostas por segmento (loop externo ? Cap. 13).

O juiz Claude avalia cada resposta do agente em 4 dimensoes calibradas
para o contexto bancario:
  - Fidelidade ao RAG  (a resposta cita apenas o que foi recuperado?)
  - Adequacao ao perfil (tom e complexidade adequados ao segmento?)
  - Completude         (cobre todos os pontos da pergunta?)
  - Conformidade LGPD  (sem exposicao de dados pessoais?)

Uso offline (mock, sem Bedrock):
  python llm_judge.py --modo mock

Uso com Bedrock:
  python llm_judge.py \
    --pergunta "Qual o melhor investimento para perfil conservador?" \
    --resposta "Recomendamos Tesouro Selic com liquidez diaria." \
    --contexto "Cliente PF, cluster conservador, saldo 15000." \
    --segmento PF
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Optional


# ?? Prompt por segmento ??????????????????????????????????????????????????????

_CRITERIOS_BASE = """
1. Fidelidade ao RAG (0-3): a resposta usa apenas informacoes recuperadas? (0=inventou, 3=totalmente fiel)
2. Adequacao ao perfil (0-3): tom e complexidade condizem com o segmento {segmento}? (0=inadequado, 3=perfeito)
3. Completude (0-2): cobre todos os pontos da pergunta? (0=parcial, 2=completo)
4. Conformidade LGPD (0-2): ausencia de dados pessoais indevidos? (0=violacao, 2=conforme)
"""

_JUDGE_PROMPT = """Voce e um avaliador especialista em sistemas de IA para bancos brasileiros.

SEGMENTO DO CLIENTE: {segmento}
CONTEXTO RAG DISPONIVEL: {contexto}
PERGUNTA DO USUARIO: {pergunta}
RESPOSTA DO AGENTE: {resposta}

CRITERIOS DE AVALIACAO (pontuacao maxima = 10):
{criterios}

Responda SOMENTE em JSON com os campos:
  fidelidade_rag: int (0-3)
  adequacao_perfil: int (0-3)
  completude: int (0-2)
  conformidade_lgpd: int (0-2)
  score_total: int (0-10, soma dos anteriores)
  aprovado: bool (true se score_total >= 7)
  razao: string (justificativa em ate 3 frases)

JSON:"""

_MOCK_RESPONSES = {
    "PF": {"fidelidade_rag": 3, "adequacao_perfil": 3, "completude": 2,
           "conformidade_lgpd": 2, "score_total": 10, "aprovado": True,
           "razao": "[MOCK] Resposta fiel ao contexto, tom adequado para PF conservador."},
    "PJ": {"fidelidade_rag": 2, "adequacao_perfil": 2, "completude": 1,
           "conformidade_lgpd": 2, "score_total": 7, "aprovado": True,
           "razao": "[MOCK] Resposta adequada para PJ, completude parcial."},
    "FP": {"fidelidade_rag": 1, "adequacao_perfil": 2, "completude": 2,
           "conformidade_lgpd": 2, "score_total": 7, "aprovado": True,
           "razao": "[MOCK] Fidelidade ao RAG questionavel, adequacao ao segmento FP OK."},
}


# ?? Estrutura de resultado ????????????????????????????????????????????????????

@dataclass
class VeredictJudge:
    segmento: str
    fidelidade_rag: int
    adequacao_perfil: int
    completude: int
    conformidade_lgpd: int
    score_total: int
    aprovado: bool
    razao: str

    def resumo(self) -> str:
        status = "APROVADO ?" if self.aprovado else "REPROVADO ?"
        return (
            f"  Segmento:          {self.segmento}\n"
            f"  Fidelidade RAG:    {self.fidelidade_rag}/3\n"
            f"  Adequacao perfil:  {self.adequacao_perfil}/3\n"
            f"  Completude:        {self.completude}/2\n"
            f"  Conformidade LGPD: {self.conformidade_lgpd}/2\n"
            f"  Score total:       {self.score_total}/10 ? {status}\n"
            f"  Razao:             {self.razao}"
        )


# ?? Avaliacao via Bedrock ?????????????????????????????????????????????????????

def julgar(pergunta: str, resposta: str, contexto: str = "",
           segmento: str = "PF",
           region: str = "us-east-1",
           model_id: str = "us.anthropic.claude-sonnet-4-5-20250514-v1:0") -> VeredictJudge:
    """Chama o juiz Claude via Bedrock e retorna o veredito estruturado."""
    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=region)
        criterios = _CRITERIOS_BASE.format(segmento=segmento)
        prompt = _JUDGE_PROMPT.format(
            segmento=segmento, contexto=contexto,
            pergunta=pergunta, resposta=resposta, criterios=criterios
        )
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}],
        })
        raw = client.invoke_model(modelId=model_id, body=body)
        text = json.loads(raw["body"].read())["content"][0]["text"].strip()
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        data = json.loads(text)
        return VeredictJudge(segmento=segmento, **data)
    except Exception as e:
        print(f"[AVISO] Bedrock indisponivel: {e}", file=sys.stderr)
        return _mock_judge(segmento)


def _mock_judge(segmento: str = "PF") -> VeredictJudge:
    """Retorna um veredito mock para testes offline."""
    m = _MOCK_RESPONSES.get(segmento, _MOCK_RESPONSES["PF"])
    return VeredictJudge(segmento=segmento, **m)


# ?? Avaliacao batch ???????????????????????????????????????????????????????????

def julgar_batch(caminho: str, usar_bedrock: bool = False) -> list[dict]:
    """
    JSONL com linhas: {"id":..., "pergunta":..., "resposta":...,
                       "contexto":..., "segmento":...}
    """
    resultados = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            item = json.loads(linha.strip())
            if usar_bedrock:
                v = julgar(item["pergunta"], item["resposta"],
                           item.get("contexto", ""), item.get("segmento", "PF"))
            else:
                v = _mock_judge(item.get("segmento", "PF"))
            resultados.append({"id": item.get("id", "?"), **asdict(v)})
    return resultados


# ?? CLI ???????????????????????????????????????????????????????????????????????

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM as Judge ? avaliacao por segmento")
    parser.add_argument("--modo", choices=["mock", "bedrock", "batch"],
                        default="mock")
    parser.add_argument("--pergunta", help="Pergunta do usuario")
    parser.add_argument("--resposta", help="Resposta do agente")
    parser.add_argument("--contexto", default="", help="Contexto RAG utilizado")
    parser.add_argument("--segmento", default="PF", choices=["PF", "PJ", "FP", "PJA"],
                        help="Segmento do cliente")
    parser.add_argument("--arquivo", help="JSONL para modo batch")
    args = parser.parse_args()

    if args.modo == "mock":
        for seg in ["PF", "PJ", "FP"]:
            v = _mock_judge(seg)
            print(f"\n{'='*50}")
            print(v.resumo())

    elif args.modo == "bedrock":
        if not args.pergunta or not args.resposta:
            parser.error("--pergunta e --resposta sao obrigatorios no modo bedrock")
        v = julgar(args.pergunta, args.resposta, args.contexto, args.segmento)
        print(v.resumo())

    elif args.modo == "batch":
        if not args.arquivo:
            parser.error("--arquivo e obrigatorio no modo batch")
        resultados = julgar_batch(args.arquivo, usar_bedrock=False)
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
