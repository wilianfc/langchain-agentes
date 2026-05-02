# Guia de Redação do Livro
# Baseado na análise da tese de doutorado: tese_poli_wilian_revBCA.pdf
# Escola Politécnica da USP — Engenharia de Computação (2016)

## 1. Registro e Tom

- Estilo acadêmico-formal, técnico e objetivo.
- Neutro e impessoal: preferir construções passivas e impessoais em vez de 1ª pessoa.
  - ✅ "observa-se que", "verifica-se que", "foi implementado", "constata-se"
  - ❌ "eu fiz", "nós criamos" (usar apenas se o capítulo exigir autoria explícita)
- Afirmações devem ser fundamentadas: citar referências, dados ou resultados experimentais.
- Evitar coloquialismos, gírias técnicas e expressões informais.

## 2. Sintaxe e Estrutura de Frases

- Períodos completos e densos (média ~23 palavras por frase é referência).
- Frases curtas são aceitáveis para conclusões pontuais; evitar parágrafos com uma única frase curta.
- Estrutura preferencial de parágrafo:
  1. Frase tópico (o que será discutido).
  2. Desenvolvimento com argumentos e evidências.
  3. Frase de fechamento com inferência ou transição.

## 3. Coesão e Conectores Argumentativos

Usar os conectores conforme a função lógica:

| Função | Conectores aprovados |
|---|---|
| Conclusão/Inferência | portanto, logo, assim, dessa forma, desse modo |
| Adição/Complemento | além disso, adicionalmente, neste contexto, sobretudo |
| Contraste/Ressalva | todavia, contudo, entretanto, não obstante, porém |
| Explicação/Equivalência | ou seja, isto é, a saber |
| Referência/Confirmação | conforme, de acordo com, segundo |

**Proibido:** "daí", "aí", "tipo assim", "basicamente", "no fundo", "meio que".

## 4. Léxico e Vocabulário

- Vocabulário técnico-científico preciso e consistente.
- Ao introduzir um termo técnico pela primeira vez, defini-lo na mesma frase ou em nota de rodapé.
- Não misturar sinônimos para o mesmo conceito técnico dentro do mesmo capítulo.
- Siglas: definir na primeira ocorrência — ex.: "Retrieval-Augmented Generation (RAG)".
- Evitar redundância lexical e pleonasmos — ex.: "planejamento futuro" → "planejamento".

### 4.1 Termos matemáticos e técnicos — obrigatoriedade de definição

Termos matemáticos, estatísticos e de aprendizado de máquina devem ser tratados com rigor especial.

**Categorias e tratamento obrigatório:**

| Categoria | Exemplos | Tratamento |
|---|---|---|
| Operações matemáticas de ML | *softmax*, *logits*, *embedding* | Definir inline + `\index{termo|textbf}` |
| Algoritmos de tokenização | *Byte-Pair Encoding* (BPE), *SentencePiece*, *WordPiece* | Definir inline + `\index{termo|textbf}` + apêndice se >3 linhas |
| Estratégias de amostragem | *top-p* (nucleus sampling), *top-k*, temperatura | Definir inline + equação `\[ \]` se possível + `\index{termo|textbf}` |
| Arquiteturas | *Transformer*, *encoder*, *decoder*, *attention head* | Definir inline + remissiva para o capítulo de fundamentos |
| Métricas de avaliação | *BLEU*, *ROUGE*, *perplexity*, *F1* | Definir inline; equação no Apêndice B — Glossário Matemático |

**Padrão de definição inline (definição curta — ≤ 2 linhas):**

```latex
A função \textit{softmax}\index{softmax|textbf}, definida como
$\sigma(\mathbf{z})_i = e^{z_i} / \sum_j e^{z_j}$, converte o
vetor de \textit{logits}\index{logits|textbf} --- valores reais não
normalizados produzidos pela última camada da rede --- em uma
distribuição de probabilidade sobre o vocabulário.
```

**Padrão para definição em apêndice (definição longa — >2 linhas, equações múltiplas):**

- Inserir no arquivo `chapters/98_apendice_glossario_matematico.tex`.
- No texto principal, usar nota de rodapé de remissão:
  ```latex
  	extit{Byte-Pair Encoding} (BPE)\index{Byte-Pair Encoding|textbf}%
  \footnote{Definição completa no Apêndice~\ref{apendice:glossario_matematico},
  p.~\pageref{sec:bpe}.}
  ```
- Usar `\label{sec:NOME}` dentro do apêndice para referência cruzada.

**Checklist por termo novo introduzido:**
- [ ] Aparece em itálico na primeira ocorrência?
- [ ] Definido inline ou no apêndice?
- [ ] `\index{termo|textbf}` inserido fora de `lstlisting`?
- [ ] Equação formatada com `$...$` ou `\[...\]` quando aplicável?
- [ ] Variante em português indexada com `|see{}`?

## 5. Estrutura Interna de Cada Capítulo

Seguir rigorosamente o esqueleto definido em `chapters/99_apendice_template_capitulo.tex`:

1. **Escopo** — delimita o que será tratado.
2. **Objetivos** — o que o leitor saberá ao final.
3. **Implementação orientada por passos** — sequência numerada, do simples ao complexo.
4. **Plano de testes** — funcional, desempenho e qualidade de resposta.
5. **Critérios de aceite** — condições objetivas e verificáveis.
6. **Espaço de expansão iterativa** — notas de versão, melhorias, lacunas.

## 6. Referências e Citações

- Padrão ABNT NBR 6023.
- Toda afirmação quantitativa ou metodológica deve ter fonte.
- Figuras e tabelas: legenda abaixo, numeração sequencial por capítulo (Fig. 3.1, Tab. 3.1).
- Código-fonte: usar ambiente `verbatim` ou `lstlisting`; comentar inline em português.

## 7. Apresentação de Resultados Técnicos

- Métricas sempre acompanhadas de unidade e contexto: "latência média de 1.240 ms (±120 ms, n=10)".
- Comparativos em tabelas; evitar listas longas de números em prosa.
- Gráficos e diagramas: sempre referenciados no texto antes de aparecerem.

## 8. Exemplo de Padrão de Escrita (trecho da tese de referência)

> "Diversas atividades necessitam do desenvolvimento de soluções capazes de auxiliar na
> extração de informações de dados oriundos de sistemas de sensoriamento remoto e outras
> geotecnologias [...] a identificação de requisitos para o monitoramento ambiental; a
> definição de regiões de conservação; o planejamento e execução de atividades de
> verificação quanto ao cumprimento e uso do espaço."

Características observadas: nominalização ("identificação", "definição", "planejamento"),
voz passiva implícita, ausência de sujeito explícito, encadeamento por ponto e vírgula.

## 9. Checklist antes de submeter um capítulo

- [ ] Todas as siglas definidas na primeira ocorrência?
- [ ] Nenhuma frase em 1ª pessoa sem justificativa?
- [ ] Todos os termos técnicos novos definidos (inline ou apêndice)?
- [ ] Termos matemáticos/ML com `\index{termo|textbf}` e equação quando aplicável?
- [ ] Plano de testes preenchido e critérios de aceite verificáveis?
- [ ] Referências bibliográficas no padrão ABNT?
- [ ] Figuras e tabelas referenciadas no texto?
