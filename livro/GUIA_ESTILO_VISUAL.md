# Guia de Estilo Visual — Livro

## Objetivo
Definir um estilo leve, técnico e confiável para documentação de arquitetura de IA.

## Princípios
- Leveza com seriedade: contraste moderado, sem excesso de saturação.
- Hierarquia clara: capítulos, seções e subtítulos com pesos distintos.
- Consistência: mesma lógica visual em texto, tabelas, figuras e código.
- Legibilidade em longa duração: espaçamentos equilibrados e tipografia editorial.

## Paleta
- TitleBlue: #153E63
- SectionBlue: #1F567D
- AccentGray: #5F6B73
- RuleBlue: #B8CBD8
- LinkBlue: #1E5A88
- CodeBg: #F5F7F9
- CodeKeyword: #1D4E75
- CodeString: #8A4B14

## Tipografia
- Texto e matemática: newtxtext + newtxmath.
- Entrelinha global: 1.3.
- Recuo de parágrafo: 1.2em.
- Espaçamento entre parágrafos: 0.25em.

## Títulos
- Capítulos com linha divisória inferior e rótulo discreto.
- Seções em azul institucional (SectionBlue).
- Subseções em cinza técnico (AccentGray).

## Capa
- Título principal em TitleBlue.
- Subtítulo em SectionBlue.
- Linhas horizontais finas (RuleBlue) para estrutura.

## Sumário
- Título do sumário com destaque em TitleBlue.
- Capítulos em SectionBlue.
- Seções e paginação secundária em AccentGray.

## Cabeçalho e paginação
- Cabeçalho esquerdo: capítulo atual.
- Cabeçalho direito: número da página.
- Linha superior do cabeçalho em TitleBlue.

## Citações
- Ambiente quote em itálico leve, tom AccentGray e recuo lateral.

## Tabelas
- Alternância de linha (zebra): CodeBg / branco.
- Espaçamento vertical ampliado para leitura técnica.
- Legenda alinhada à esquerda.

## Figuras
- Largura padrão de 95% da área de texto, mantendo proporção.
- Legenda centralizada.
- Espaçamento vertical controlado para evitar blocos densos.

## Blocos de código
- Fundo suave (CodeBg).
- Borda discreta em RuleBlue com cantos arredondados.
- Paleta semântica para keywords e strings.
- Numeração lateral para referência no texto.

## Apêndices
- Página de abertura dedicada para separar o corpo principal.
- Capítulos de apêndice rotulados como "Apêndice A, B, C...".
- Entrada própria no sumário: "Apêndices".

## Checklist de consistência
- Compilar com pdflatex após qualquer ajuste de estilo.
- Verificar warnings de layout no main.log.
- Validar contraste de links e legendas no PDF final.
