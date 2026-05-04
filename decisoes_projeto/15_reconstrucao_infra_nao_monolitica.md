# Decisao 15 - Reconstrucao completa da infra nao monolitica

Data: 2026-05-03
Status: Aprovada e validada em execucao real

## Contexto
Foi executado deploy faseado completo da infraestrutura por produtos (15 stacks) para validar reconstrucao end-to-end fora do modelo monolitico.

## Decisoes
1. Manter arquitetura por produtos com orquestracao via deploy_faseado.
2. Evitar apply isolado em stacks dependentes quando os outputs upstream ainda nao foram coletados.
3. Tratar segredo Anthropic vazio sem criar secret_version vazio.
4. Serializar vpc_security_group_ids para Neptune proxy/replication em formato JSON valido com aspas duplas.

## Evidencias de validacao
- Resumo final do deploy: APPLY CONCLUIDO COM SUCESSO (erros = 0).
- API endpoint provisionado: https://t9o3dos21k.execute-api.sa-east-1.amazonaws.com/
- CloudFront provisionado: d2ezjxnkbue8v9.cloudfront.net (distribution id E2FD7BTQ2OD6J5).
- Lambdas provisionadas: controller, worker, status e ingester.

### Smoke test end-to-end (2026-05-03)
- POST /query retornou request_id `0e73a7f9-84ee-4359-aff3-54bd019b3410`, status PENDING em ~1s.
- GET /status/{id} retornou status COMPLETED em ~18s com resposta LLM gerada pelo Bedrock (Claude Sonnet 4.5).
- Cluster classificado: cluster_id=3, segmento "Massa Estável".
- Modelo de clustering carregado de: s3://langchain-agent-artifacts-dev/clientes-agente/modelo_clustering_slim.pkl.
- Frontend (4 arquivos HTML/JS/CSS) sincronizado para s3://langchain-agent-frontend-dev/ com config.js apontando para API.
- Invalidação CloudFront criada: I2D0S2FNYK6ITL5KDEVZ9YIHRR (InProgress → propagação ~2min).

## Impacto
A base de infraestrutura fica reproduzivel, auditavel e desacoplada por produto, reduzindo risco operacional e facilitando evolucao incremental.

## Reproducao
1. Executar apply faseado completo.
2. Verificar outputs de API e CloudFront.
3. Confirmar stacks finais: lambda_worker, api_gateway e cloudfront_frontend.
