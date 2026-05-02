# 11 — Evolução do Pipeline: Diagrama v7 como Visão-Alvo

**Data:** 2026-05-02
**Decisão:** O `diagram_v7.drawio` é a visão-alvo oficial do projeto. O projeto atual
está adiantado nas camadas de recuperação (Neptune, twins, índice de confiabilidade),
mas precisa evoluir nas camadas de avaliação e qualidade para convergir com o diagrama.

## Princípio arquitetural estabelecido

O projeto tem **dois eixos de evolução independentes**:

### Eixo 1 — Qualidade de Resposta (lacuna principal)
- Diagrama prevê: Judge LLM por segmento → Meta-Judge → feedback loop
- Implementação atual: apenas índice de confiabilidade léxico/estatístico
- Próxima ação: implementar `LLMChain` como Judge + DeepEval metrics

### Eixo 2 — Segmentação Real (alinhamento de domínio)
- Diagrama prevê: PF/PJ/FP/PJA com sub-clusters por produtos bancários reais
- Implementação atual: K-Means genérico (Premium Conservador / Jovem Digital / Alto Risco / Massa Estável)
- Próxima ação: migrar para segmentos regulatórios + criar KBs de domínio

## Decisão sobre arquitetura LLM Judge

Usar **LangChain `LLMChain`** com:
- Prompt few-shot específico por segmento
- `GEval` do DeepEval com critérios customizados por segmento
- Critérios PF: suitability + LGPD
- Critérios PJ: compliance financeiro (DRE, rating, garantias)
- Critérios FP: margem consignável + Lei 8.112 + SIAPE
- Critérios PJA: Plano Safra + zoneamento agroclimático + risco commodity

## Manter (não regredir)

- Digital Twin (`clientes-digital-twins`) — vantagem competitiva sobre o diagrama
- Neptune GraphRAG — não está no diagrama, mas é diferencial
- Índice de confiabilidade — documentado no cap. 10 do livro, manter
- CloudFront + frontend — manter como interface de acesso

## Referências

- Arquivo diagrama: `C:\Documentos\diagram_v7.drawio`
- Análise completa: `decisoes_projeto/12_estado_sessao_comparacao_v7.md`
- Livro: `c:\Documentos\langchain\livro\main.pdf` (18 caps, 763.333 bytes)
- Pipeline principal: `c:\Documentos\langchain\aws_pipeline_clientes.py`
