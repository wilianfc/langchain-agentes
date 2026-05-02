# Arquivo gerado automaticamente a partir de demo_api.ipynb
# Conteudo completo dos blocos de codigo do notebook

# ===== cell_003 =====
import json
import time
import requests
from IPython.display import display, HTML, Markdown

API_URL = "https://3vqrahlmyg.execute-api.sa-east-1.amazonaws.com"

# ?? Cores para o indice de confiabilidade ??????????????????????????????????????
NIVEL_COR = {"alto": "#2d7a2d", "medio": "#c47a00", "baixo": "#c0392b"}
NIVEL_BG  = {"alto": "#eafaea", "medio": "#fff8e1", "baixo": "#fdecea"}

def consultar(payload: dict, poll_interval: int = 3, timeout: int = 90) -> dict:
    """Envia query e aguarda resultado (polling)."""
    r = requests.post(f"{API_URL}/query", json=payload, timeout=30)
    r.raise_for_status()
    request_id = r.json()["request_id"]
    print(f"  request_id: {request_id}")

    for _ in range(timeout // poll_interval):
        time.sleep(poll_interval)
        status = requests.get(f"{API_URL}/status/{request_id}", timeout=10).json()
        st = status["status"]
        if st == "COMPLETED":
            resultado = json.loads(status["resultado"])
            resultado["_request_id"] = request_id
            return resultado
        if st == "FAILED":
            raise RuntimeError(f"Worker falhou:\n{status.get('erro', '')}")
        print(f"  {st}...", end="\r")

    raise TimeoutError(f"Sem resposta em {timeout}s (request_id={request_id})")


def exibir(resultado: dict) -> None:
    """Renderiza resposta + indice de confiabilidade em HTML."""
    modo       = resultado.get("modo", "")
    resposta   = resultado.get("resposta", "")
    ic         = resultado.get("indice_confiabilidade", {})
    score      = ic.get("score", 0)
    nivel      = ic.get("nivel", "baixo")
    fontes     = ic.get("fontes_ativas", [])
    cobertura  = ic.get("detalhes", {}).get("cobertura_fontes", 0)
    overlap    = ic.get("detalhes", {}).get("sobreposicao_lexica", 0)

    cor = NIVEL_COR[nivel]
    bg  = NIVEL_BG[nivel]

    fontes_html = "".join(
        f'<span style="background:#dde;border-radius:4px;padding:2px 7px;'
        f'font-size:0.82em;margin-right:4px">{f}</span>'
        for f in fontes
    ) or '<span style="color:#999">nenhuma</span>'

    barra_largura = int(score * 200)

    html = f"""
    <div style="font-family:sans-serif;max-width:860px;border:1px solid #ddd;
                border-radius:8px;overflow:hidden;margin:12px 0">

      <div style="background:#2c3e50;color:#ecf0f1;padding:10px 16px;
                  font-size:0.85em;letter-spacing:.5px">
        MODO: <strong>{modo.upper()}</strong>
        {'&nbsp;?&nbsp;' + resultado.get('segmento','') if resultado.get('segmento') else ''}
        {'&nbsp;?&nbsp;' + resultado.get('persona_nome','') if resultado.get('persona_nome') else ''}
        {'&nbsp;?&nbsp;' + resultado.get('cliente_id','') if resultado.get('cliente_id') else ''}
      </div>

      <div style="padding:16px 18px;white-space:pre-wrap;line-height:1.6;
                  font-size:0.93em;border-bottom:1px solid #eee">{resposta}</div>

      <div style="background:{bg};padding:10px 18px">
        <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
          <div>
            <span style="font-size:1.5em;font-weight:700;color:{cor}">{score:.2f}</span>
            <span style="margin-left:6px;background:{cor};color:white;border-radius:4px;
                         padding:2px 8px;font-size:0.78em;font-weight:600">{nivel.upper()}</span>
          </div>
          <div style="flex:1;min-width:160px">
            <div style="background:#ddd;border-radius:4px;height:8px">
              <div style="background:{cor};width:{barra_largura}px;max-width:200px;
                           height:8px;border-radius:4px"></div>
            </div>
          </div>
          <div style="font-size:0.82em;color:#555">
            <strong>Fontes:</strong> {fontes_html}<br>
            <strong>Cobertura:</strong> {cobertura:.2f} &nbsp;
            <strong>Sobreposicao lexica:</strong> {overlap:.2f}
          </div>
        </div>
      </div>
    </div>
    """
    display(HTML(html))

print("Setup concluido. API:", API_URL)

# ===== cell_005 =====
print("Enviando consulta modo segmento...")

resultado_segmento = consultar({
    "cliente_id": "C001",
    "dados_cliente": {
        "idade": 52,
        "renda_mensal": 18000,
        "saldo_medio": 140000,
        "transacoes_mes": 8,
        "score_credito": 830,
        "num_produtos": 5
    },
    "pergunta": "Que produto de investimento faz mais sentido para este cliente agora?",
    "modo": "segmento"
})

exibir(resultado_segmento)

# ===== cell_007 =====
print("Enviando consulta modo persona...")

resultado_persona = consultar({
    "cluster_id": 1,
    "pergunta": "O banco lancou um cartao com cashback de 3% e aprovacao pelo app. Voce toparia?",
    "modo": "persona"
})

exibir(resultado_persona)

# ===== cell_009 =====
print("Enviando consulta modo twin...")

resultado_twin = consultar({
    "cliente_id": "GRAPH-C00-0001",
    "cluster_id": 0,
    "dados_cliente": {
        "idade": 43,
        "renda_mensal": 4685,
        "saldo_medio": 35000,
        "transacoes_mes": 6,
        "score_credito": 720,
        "num_produtos": 3
    },
    "pergunta": "Considerando meu perfil e clientes parecidos comigo, que estrategia de previdencia faz sentido?",
    "modo": "twin"
})

exibir(resultado_twin)

# ===== cell_011 =====
PERGUNTA = "O banco oferece um emprestimo pessoal de R$ 5.000 com taxa de 2,5% ao mes. Voce toparia?"

resultados_persona = {}
for cluster_id in range(4):
    print(f"  Consultando cluster {cluster_id}...")
    resultados_persona[cluster_id] = consultar({
        "cluster_id": cluster_id,
        "pergunta": PERGUNTA,
        "modo": "persona"
    })

print("\nRespostas:")
for cluster_id, res in resultados_persona.items():
    exibir(res)

# ===== cell_013 =====
def tabela_comparativa(resultados: list) -> None:
    linhas = ""
    for r in resultados:
        modo      = r.get("modo", "")
        segmento  = r.get("segmento") or r.get("persona_nome") or r.get("cliente_id", "")
        ic        = r.get("indice_confiabilidade", {})
        score     = ic.get("score", 0)
        nivel     = ic.get("nivel", "")
        fontes    = ", ".join(ic.get("fontes_ativas", [])) or "?"
        cobertura = ic.get("detalhes", {}).get("cobertura_fontes", 0)
        overlap   = ic.get("detalhes", {}).get("sobreposicao_lexica", 0)
        cor       = NIVEL_COR[nivel]
        bg        = NIVEL_BG[nivel]
        barra     = int(score * 120)

        linhas += f"""
        <tr style="background:{bg}">
          <td style="padding:8px 12px"><code>{modo}</code></td>
          <td style="padding:8px 12px">{segmento}</td>
          <td style="padding:8px 12px;text-align:center">
            <strong style="color:{cor}">{score:.2f}</strong>
            <div style="background:#ddd;border-radius:3px;height:6px;margin-top:3px">
              <div style="background:{cor};width:{barra}px;height:6px;border-radius:3px"></div>
            </div>
          </td>
          <td style="padding:8px 12px;text-align:center">
            <span style="background:{cor};color:white;border-radius:4px;
                         padding:2px 8px;font-size:0.8em">{nivel.upper()}</span>
          </td>
          <td style="padding:8px 12px;font-size:0.82em">{fontes}</td>
          <td style="padding:8px 12px;text-align:center">{cobertura:.2f}</td>
          <td style="padding:8px 12px;text-align:center">{overlap:.2f}</td>
        </tr>"""

    html = f"""
    <table style="border-collapse:collapse;width:100%;font-family:sans-serif;font-size:0.9em">
      <thead>
        <tr style="background:#2c3e50;color:white">
          <th style="padding:10px 12px;text-align:left">Modo</th>
          <th style="padding:10px 12px;text-align:left">Segmento / Persona</th>
          <th style="padding:10px 12px;text-align:center">Score</th>
          <th style="padding:10px 12px;text-align:center">Nivel</th>
          <th style="padding:10px 12px;text-align:left">Fontes RAG ativas</th>
          <th style="padding:10px 12px;text-align:center">Cobertura</th>
          <th style="padding:10px 12px;text-align:center">Sobreposicao</th>
        </tr>
      </thead>
      <tbody>{linhas}</tbody>
    </table>"""
    display(HTML(html))


# Consolida resultados das secoes anteriores
todos = [
    resultado_segmento,
    resultado_persona,
    resultado_twin,
]

tabela_comparativa(todos)

# ===== cell_016 =====
print("Enviando consulta com cliente sem dados no indice (DEMO-X999)...")

resultado_sem_indice = consultar({
    "cliente_id": "DEMO-X999",
    "cluster_id": 1,
    "dados_cliente": {
        "idade": 28,
        "renda_mensal": 3200,
        "saldo_medio": 5000,
        "transacoes_mes": 20,
        "score_credito": 650,
        "num_produtos": 2
    },
    "pergunta": "Devo aceitar o limite de credito pre-aprovado de R$ 3.000?",
    "modo": "twin"
})

exibir(resultado_sem_indice)

print("\n--- Comparativo ---")
tabela_comparativa([resultado_twin, resultado_sem_indice])

# ===== cell_018 =====
import sys, os
sys.path.insert(0, os.getcwd())
from plantuml_helper import show_plantuml

puml_path = os.path.join("decisoes_projeto", "graphrag_interaction.puml")
with open(puml_path, encoding="utf-8") as f:
    diagrama = f.read()

show_plantuml(diagrama, "GraphRAG Pipeline ? sa-east-1")

# ===== cell_020 =====
# ?? Edite aqui ?????????????????????????????????????????????????????????????????
MODO       = "segmento"          # "segmento" | "persona" | "twin"
PERGUNTA   = "Como este cliente se comporta em relacao a investimentos de longo prazo?"
CLIENTE_ID = "C002"              # usado em modo twin
CLUSTER_ID = None                # None = classificar automaticamente pelos dados

DADOS_CLIENTE = {
    "idade":          35,
    "renda_mensal":   4500,
    "saldo_medio":    8000,
    "transacoes_mes": 15,
    "score_credito":  680,
    "num_produtos":   3,
}
# ???????????????????????????????????????????????????????????????????????????????

payload = {"pergunta": PERGUNTA, "modo": MODO, "dados_cliente": DADOS_CLIENTE}
if CLIENTE_ID:
    payload["cliente_id"] = CLIENTE_ID
if CLUSTER_ID is not None:
    payload["cluster_id"] = CLUSTER_ID

print(f"Consultando modo {MODO!r}...")
resultado_livre = consultar(payload)
exibir(resultado_livre)
