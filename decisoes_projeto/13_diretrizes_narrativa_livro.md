# 13 — Diretrizes de Narrativa e Progressão do Livro

**Data:** sessão de trabalho (pós-compactação v1)  
**Status:** ATIVO — requisito permanente do texto

---

## Requisito Central

O leitor deve **perceber que existe uma história sendo contada** e que ela se
desenvolve ao longo dos capítulos. O livro não é uma coleção de receitas
isoladas: é uma jornada de construção de um sistema de IA corporativo que nasce
simples (uma chamada ao LLM) e amadurece até operar em produção com
rastreabilidade, avaliação contínua e governança técnica.

---

## Estrutura Narrativa Aprovada

### Dois ciclos interdependentes

| Ciclo | Capítulos | Fase | Pergunta central |
|-------|-----------|------|-----------------|
| **Loop interno** (inner loop) | 1 – 10 | Desenvolvimento offline | "Como construir?" |
| **Loop externo** (outer loop) | 11 – 18 | Operação em produção | "Como garantir que funciona?" |

- **Cap. 10** é o ponto de convergência — junção dos dois loops.
- Os loops giram em paralelo e se alimentam mutuamente (outer → evidências → inner → melhoria → deploy → outer).

### Marcos narrativos

| Cap. | Evento na história |
|------|-------------------|
| 1–2  | O sistema aprende a falar (fundamentos + ambiente) |
| 3    | **Primeira virada:** o sistema passa a agir (agentes) |
| 4–5  | O sistema aprende a lembrar e a buscar (tools, RAG) |
| 6–9  | O sistema cresce: RAG corporativo, pipeline, twins, grafo |
| 10   | **Convergência:** tudo junto pela primeira vez |
| 11   | **Segunda virada:** o loop externo começa (observabilidade) |
| 12–14| O sistema aprende a se avaliar (métricas, Judge, golden dataset) |
| 15   | O sistema planeja sua própria evolução (roadmap) |
| 16–18| O sistema se sustenta (CI/CD, qualidade, frontend) |

---

## Regras de Aplicação no Texto

1. **Bloco de posicionamento narrativo** (`\begin{quote}\itshape ...\end{quote}`)
   no início da seção "Escopo" de cada capítulo. Formato:
   > **Onde estamos na história:** [frase única situando o capítulo no arco geral]

2. **Frase de abertura** de cada seção "Escopo" deve:
   - Referenciar o que veio antes ("os capítulos anteriores construíram X")
   - Declarar o que este capítulo acrescenta
   - Antecipar o que vem depois ("nos capítulos N–M, este componente será ...")

3. **Transições entre capítulos**: a última seção de cada capítulo ("Para saber
   mais" ou "Espaço para expansão") pode incluir uma frase de gancho para o
   próximo capítulo.

4. **Índice no prefácio**: organizado em dois grupos explícitos ("Loop interno"
   e "Loop externo") com o cap. 10 destacado como ponto de convergência.

---

## Estado de Implementação

| Arquivo | Status |
|---------|--------|
| `00_prefacio.tex` | ✅ Reescrito — narrativa completa + índice em 2 grupos |
| `01_fundamentos_llm_ia.tex` | ✅ Bloco de posicionamento adicionado |
| `03_agentes_langgraph_memoria.tex` | ✅ Bloco de posicionamento adicionado ("primeira virada") |
| `10_pipeline_integrado_producao.tex` | ✅ Bloco de posicionamento adicionado ("convergência") |
| `11_confiabilidade_observabilidade.tex` | ✅ Bloco de posicionamento adicionado ("loop externo") |
| caps. 02, 04–09, 12–18 | ⏳ Pendente — adicionar bloco de posicionamento |

---

## Próximos Passos

- Adicionar bloco de posicionamento nos caps. restantes conforme evolução do conteúdo
- Ao revisar/expandir qualquer capítulo, verificar coerência com a tabela de marcos narrativos
- O bloco `\begin{quote}` deve ser a **última coisa a ser escrita** de cada capítulo (após o conteúdo estar estável)
