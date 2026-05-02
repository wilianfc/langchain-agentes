# 09 — Guia de Redação do Livro

**Data:** 2026-05-01
**Decisão:** Adotar estilo de escrita baseado na tese doutoral da Escola Politécnica da USP
(tese_poli_wilian_revBCA.pdf, Engenharia de Computação, 2016).

## Regra geral

Toda redação do livro "Arquitetura de LLMs e IA Aplicada" deve seguir o guia
completo em `livro/GUIA_REDACAO.md`. Este arquivo é a fonte canônica e deve ser
lido antes de redigir ou revisar qualquer capítulo.

## Resumo das regras fundamentais

- **Tom:** acadêmico-formal, impessoal e objetivo.
- **Voz:** impessoal preferida — "observa-se que", "verifica-se que", "foi implementado".
- **1ª pessoa:** evitar; aceita-se apenas em seções de autoria explícita (prefácio, agradecimentos).
- **Frases:** densas, completas, ~23 palavras em média.
- **Parágrafos:** frase tópico + desenvolvimento + fechamento/transição.
- **Conectores aprovados:** portanto, assim, contudo, ou seja, neste contexto, todavia, conforme.
- **Proibido:** coloquialismos, "basicamente", "no fundo", "meio que", gírias técnicas.
- **Siglas:** definir na primeira ocorrência — ex.: "Retrieval-Augmented Generation (RAG)".
- **Métricas:** sempre com unidade e contexto — ex.: "latência média de 1.240 ms (±120 ms, n=10)".
- **Referências:** padrão ABNT NBR 6023.

## Estrutura obrigatória de cada capítulo

1. Escopo do capítulo
2. Objetivos de aprendizagem
3. Implementação orientada por passos
4. Plano de testes (funcional, desempenho, qualidade de resposta)
5. Critérios de aceite
6. Espaço para expansão iterativa

## Checklist pré-entrega de capítulo

- [ ] Siglas definidas na primeira ocorrência
- [ ] Nenhuma frase em 1ª pessoa sem justificativa
- [ ] Plano de testes preenchido com critérios verificáveis
- [ ] Figuras e tabelas referenciadas no texto antes de aparecerem
- [ ] Referências bibliográficas no padrão ABNT

## Termos técnicos e índice remissivo

**OBRIGATÓRIO em toda redação de capítulo:**

1. Termos em inglês ou técnicos: ao aparecerem pela primeira vez, escrever em itálico e definir na mesma frase ou nota de rodapé.
2. Registrar no índice com `\index{termo}`. Primeira definição: `\index{termo|textbf}`.
3. Sigla com remissiva: `\index{BPE|see{Byte-Pair Encoding}}`. Subentrada: `\index{prompt!system prompt}`.
4. **Nunca usar `\index{}` dentro de `lstlisting`** — causará erro.
5. Após adicionar `\index{}`: rodar `pdflatex → makeindex → pdflatex → pdflatex`.

## Termos matemáticos e técnicos — definição obrigatória

1. **Definição inline** (≤ 2 linhas): itálico + definição entre travessões/parênteses + equação se possível.
   ```latex
   A função \textit{softmax}\index{softmax|textbf}, $\sigma(\mathbf{z})_i = e^{z_i}/\sum_j e^{z_j}$,
   converte o vetor de \textit{logits}\index{logits|textbf} --- valores reais não normalizados ---
   em distribuição de probabilidade sobre o vocabulário.
   ```
2. **Definição em apêndice** (>2 linhas ou equações múltiplas): inserir em `chapters/98_apendice_glossario_matematico.tex`.
   - No texto: `\footnote{Definição completa no Apêndice~\ref{apendice:glossario_matematico}, p.~\pageref{sec:NOME}.}`
   - Usar `\label{sec:NOME}` no apêndice para referência cruzada.
3. **Categorias com tratamento obrigatório:**
   - Operações de ML (*softmax*, *logits*, *embedding*): inline + equação + `\index{|textbf}`
   - Tokenização (*BPE*, *SentencePiece*, *WordPiece*): inline + apêndice se >3 linhas
   - Amostragem (*top-p*, *top-k*, temperatura): inline + equação `\[...\]`
   - Métricas (*BLEU*, *ROUGE*, *perplexity*, *F1*): inline; equação no Apêndice B
4. **Apêndice de glossário**: `chapters/98_apendice_glossario_matematico.tex` incluído em `main.tex` antes do `\backmatter`.

## Diretrizes para inserção de referências bibliográficas

**OBRIGATÓRIO antes de inserir qualquer entrada no `referencias.bib`:**

1. **Verificar existência real** — acessar DOI, URL do arXiv ou página do publisher e confirmar que a obra existe.
2. **Confirmar autores e ano** na fonte original; nunca inferir a partir do título ou memória.
3. **Confirmar título exato** — capitalização especial protegida com `{{...}}` no BibTeX.
4. **Usar o tipo correto de entrada:**
   - Periódico revisado: `@article`
   - Conferência com anais: `@inproceedings`
   - Preprint arXiv: `@misc` com `howpublished = {arXiv:XXXX.XXXXX}`
   - Repositório/documentação: `@misc` com `url` + `note` de acesso
5. **Nunca inventar** DOI, volume, páginas ou número de edição — omitir campos não verificados.
6. **Fontes aceitáveis para verificação:** arxiv.org, doi.org, ACM DL, IEEE Xplore, Semantic Scholar, página oficial do projeto.

## Localização dos arquivos

- Guia completo: `livro/GUIA_REDACAO.md`
- Memória do repositório: `/memories/repo/livro_guia_redacao.md`
- Template de capítulo: `livro/chapters/99_apendice_template_capitulo.tex`
- Glossário matemático: `livro/chapters/98_apendice_glossario_matematico.tex`
