# 11 — Frontend Web via CloudFront para interação com a API e ingestão RAG

**Data:** 2026-05-01
**Decisão:** Adotar um frontend web estático, distribuído por CloudFront e armazenado em bucket S3 privado, para interação com a API assíncrona e ingestão de documentos no pipeline RAG.

## Motivação

Até este ponto, a plataforma expunha apenas a API Gateway e exemplos de consumo via scripts e notebook. Para uso operacional, demonstrações e homologação com áreas de negócio, faz-se necessário um canal web simples, acessível por navegador, que permita:

1. Enviar consultas para o endpoint assíncrono `POST /query`.
2. Consultar o andamento via `GET /status/{request_id}`.
3. Ingerir documentos e entrevistas no endpoint `POST /documentos` para enriquecimento do RAG.

## Decisão arquitetural

- **Distribuição:** AWS CloudFront em frente a um bucket S3 privado.
- **Origem:** bucket S3 com `Origin Access Control` (OAC), sem exposição pública direta.
- **Configuração:** arquivo `config.js` gerado no deploy com a URL real da API Gateway.
- **Frontend:** página estática HTML/CSS/JavaScript sem dependência de framework.
- **Contrato de upload:** inicialmente suportar arquivos textuais (`.txt`, `.md`, `.json`, `.csv`, `.html`) e colagem manual de conteúdo.

## Implicações

- **Vantagem:** implantação simples, baixo custo, sem servidor adicional.
- **Segurança:** bucket permanece privado; entrega pública ocorre apenas via CloudFront.
- **Limitação atual:** o backend de ingestão não recebe multipart nem extrai texto de PDF/DOCX; por isso a UI expõe apenas upload textual e explica a restrição.
- **Evolução recomendada:** incluir uma etapa de extração para PDF/DOCX (por exemplo, Lambda com Textract, Tika ou parser dedicado) antes da indexação no endpoint `/documentos`.

## Arquivos envolvidos

- `frontend/cloudfront_console/` — interface estática
- `infraestrutura/modules/cloudfront_frontend/` — bucket S3 privado + CloudFront + publicação dos assets
- `infraestrutura/main.tf` — inclusão do módulo
- `infraestrutura/outputs.tf` — saída `frontend_url`

## Relação com o livro

Adicionar um capítulo específico para a superfície web de operação da plataforma, cobrindo arquitetura, fluxo da UI, segurança e ingestão de documentos para RAG.
