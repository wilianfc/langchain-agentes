# 10 — Requisitos de Pipelines para Aplicações Bancárias

**Data:** 2026-05-01
**Decisão:** Documentar os requisitos arquiteturais e de processo para esteiras CI/CD
de produtos bancários integrados à plataforma de LLMs.

## Contexto

Os pipelines bancários do projeto operam sobre três ambientes AWS isolados:
`dev`, `homol` (homologação) e `prod`. Cada ambiente corresponde a uma conta
AWS separada, garantindo isolamento de blast radius, permissões e dados.

## Requisitos obrigatórios de pipeline

### 1. Ambientes AWS separados
- **dev**: ambiente de desenvolvimento — deploys automáticos a cada merge em branch de feature.
- **homol**: ambiente de homologação — deploy automático após merge na branch `main`; exige aprovação do QA.
- **prod**: ambiente de produção — deploy mediante aprovação manual de ao menos dois revisores autorizados.

### 2. Esteiras via Git Workflow (GitHub Actions / GitLab CI)
- Cada produto AWS possui sua **própria esteira** com arquivos de workflow independentes.
- O repositório de cada produto define o conjunto de `.github/workflows/` ou `.gitlab-ci.yml` próprio.
- Proibido compartilhar esteiras entre produtos distintos (evitar acoplamento).

### 3. Verificações de qualidade mínima obrigatórias por esteira
Toda esteira deve conter, na ordem abaixo:
1. **Lint e formatação** — `flake8` / `black` / `terraform fmt` + `terraform validate`
2. **Testes unitários** — cobertura mínima de 70% medida por `pytest --cov`
3. **Testes de integração** — contra ambiente `dev` com dados sintéticos
4. **Análise de segurança estática** — `bandit` (Python), `checkov` (Terraform), `tfsec`
5. **Validação de infraestrutura** — `terraform plan` com diff revisado
6. **Aprovação humana** — obrigatória antes de deploy em `homol` e `prod`

### 4. Padrões Terraform por produto
- Cada produto AWS (Lambda, API Gateway, DynamoDB, OpenSearch, Neptune, SQS etc.)
  possui seu próprio módulo Terraform em `infraestrutura/modules/<produto>/`.
- Workspaces Terraform mapeiam ambientes: `terraform workspace select dev|homol|prod`.
- State backends separados por ambiente (S3 + DynamoDB lock por conta AWS).
- Variáveis sensíveis via AWS Secrets Manager — nunca em `.tfvars` commitados.

### 5. Requisitos de segurança específicos para ambiente bancário
- **Princípio do menor privilégio**: roles IAM criadas por módulo Terraform,
  sem wildcards (`*`) em ações ou recursos.
- **Criptografia em repouso e em trânsito**: obrigatória para todos os serviços
  gerenciados (S3, DynamoDB, SQS, OpenSearch, Neptune).
- **Auditoria**: CloudTrail habilitado em todas as contas; logs centralizados na
  conta de segurança (conta dedicada de log aggregation).
- **Segmentação de rede**: todos os serviços dentro de VPC privada; acesso externo
  apenas via API Gateway com autenticação Cognito ou mTLS.
- **Aprovação de mudanças em prod**: requer PR aprovado por ao menos 2 revisores +
  pipeline verde + janela de manutenção registrada.

## Implicações para o livro

Os capítulos 15 e 16 endereçam estes requisitos:
- **Cap. 15** — Esteiras de CI/CD Multi-Ambiente para Produtos AWS Bancários
- **Cap. 16** — Qualidade, Segurança e Governança nas Esteiras de Produto

## Referências
- AWS Well-Architected Framework — Security Pillar
- BACEN Resolução nº 4.893/2021 (Política de Segurança Cibernética)
- Terraform Best Practices (HashiCorp)
- OWASP Top 10 para aplicações em nuvem
