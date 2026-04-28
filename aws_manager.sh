#!/usr/bin/env bash
# =============================================================================
# aws_manager.sh — Deploy e purge dos recursos AWS do agente LangChain
#
# Uso:
#   ./aws_manager.sh deploy          # Provisiona infra + indexa dados
#   ./aws_manager.sh purge           # Destroi todos os recursos AWS
#   ./aws_manager.sh purge --yes     # Purge sem confirmação interativa
#   ./aws_manager.sh status          # Exibe estado atual e URL da API
# =============================================================================
set -euo pipefail

# ── Diretórios ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/infraestrutura"

# ── Cores ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
header()  { echo -e "\n${BOLD}=== $* ===${RESET}"; }

# ── Detecta Python disponível ─────────────────────────────────────────────────
detect_python() {
    for cmd in python3 py python; do
        if command -v "$cmd" &>/dev/null; then
            # Verifica se é Python 3
            version=$("$cmd" --version 2>&1 | grep -oP '(?<=Python )\d+')
            if [[ "$version" == "3" ]]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    # Tenta py -3 no Windows
    if command -v py &>/dev/null && py -3 --version &>/dev/null 2>&1; then
        echo "py -3"
        return 0
    fi
    return 1
}

# ── Verifica pré-requisitos ───────────────────────────────────────────────────
check_prereqs() {
    header "Verificando pré-requisitos"
    local ok=true

    for tool in aws terraform; do
        if command -v "$tool" &>/dev/null; then
            success "$tool encontrado: $($tool --version 2>&1 | head -1)"
        else
            error "$tool não encontrado. Instale antes de continuar."
            ok=false
        fi
    done

    PYTHON_CMD=$(detect_python || true)
    if [[ -n "$PYTHON_CMD" ]]; then
        success "Python encontrado: $($PYTHON_CMD --version 2>&1)"
    else
        error "Python 3 não encontrado. Instale antes de continuar."
        ok=false
    fi

    if ! aws sts get-caller-identity &>/dev/null 2>&1; then
        error "AWS CLI não autenticado. Execute 'aws configure' ou exporte AWS_PROFILE."
        ok=false
    else
        AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
        AWS_REGION=$(aws configure get region 2>/dev/null || echo "sa-east-1")
        success "AWS autenticado: conta $AWS_ACCOUNT / região $AWS_REGION"
    fi

    if [[ ! -f "$TF_DIR/secrets.auto.tfvars" ]]; then
        error "Arquivo '$TF_DIR/secrets.auto.tfvars' não encontrado."
        echo "  Crie com o conteúdo:"
        echo '  anthropic_api_key = "sk-ant-..."'
        echo '  # langfuse_public_key = "pk-lf-..."   # opcional'
        echo '  # langfuse_secret_key = "sk-lf-..."   # opcional'
        ok=false
    else
        success "secrets.auto.tfvars encontrado"
    fi

    [[ "$ok" == true ]]
}

# ── Terraform init + apply ────────────────────────────────────────────────────
tf_deploy() {
    header "Provisionando infraestrutura AWS (Terraform)"
    cd "$TF_DIR"

    info "terraform init..."
    terraform init -upgrade -input=false -no-color 2>&1 | tail -5

    info "terraform apply... (OpenSearch leva ~15 min na criação)"
    terraform apply -auto-approve -input=false -no-color
    success "Infraestrutura provisionada."
}

# ── Lê outputs do Terraform ───────────────────────────────────────────────────
read_tf_outputs() {
    cd "$TF_DIR"
    API_ENDPOINT=$(terraform output -raw api_endpoint 2>/dev/null | sed 's|/$||' || echo "")
    S3_BUCKET=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")
    OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint 2>/dev/null || echo "")

    # Fallbacks via módulo direto se output raiz não existir
    if [[ -z "$S3_BUCKET" ]]; then
        S3_BUCKET=$(terraform output -json 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('s3_bucket_name',{}).get('value',''))" 2>/dev/null || echo "")
    fi
    if [[ -z "$OPENSEARCH_ENDPOINT" ]]; then
        OPENSEARCH_ENDPOINT=$(terraform output -json 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('opensearch_endpoint',{}).get('value',''))" 2>/dev/null || echo "")
    fi
}

# ── Adiciona outputs que faltam no root outputs.tf ────────────────────────────
ensure_tf_outputs() {
    local out_file="$TF_DIR/outputs.tf"
    local needs_update=false

    if ! grep -q "s3_bucket_name" "$out_file" 2>/dev/null; then
        needs_update=true
        cat >> "$out_file" <<'EOF'

output "s3_bucket_name" {
  description = "Nome do bucket S3"
  value       = module.s3.bucket_name
}

output "opensearch_endpoint" {
  description = "Endpoint do domínio OpenSearch"
  value       = module.opensearch.domain_endpoint
}
EOF
        info "outputs.tf atualizado com s3_bucket_name e opensearch_endpoint."
    fi
}

# ── Indexa dados no OpenSearch e faz upload do PKL ───────────────────────────
index_data() {
    header "Indexando dados (OpenSearch + S3)"
    cd "$SCRIPT_DIR"

    read_tf_outputs

    if [[ -z "$OPENSEARCH_ENDPOINT" ]]; then
        warn "OPENSEARCH_ENDPOINT vazio — pulando indexação."
        return
    fi
    if [[ -z "$S3_BUCKET" ]]; then
        warn "S3_BUCKET vazio — PKL não será enviado ao S3."
    fi

    info "Executando gerar_clustering.py..."
    info "  OPENSEARCH_ENDPOINT=$OPENSEARCH_ENDPOINT"
    info "  S3_BUCKET=$S3_BUCKET"

    OPENSEARCH_ENDPOINT="$OPENSEARCH_ENDPOINT" \
    S3_BUCKET="$S3_BUCKET" \
    $PYTHON_CMD gerar_clustering.py

    success "Dados indexados e PKL enviado ao S3."

    # Força cold start do worker para recarregar o PKL novo
    local worker_fn="langchain-agent-worker-dev"
    if aws lambda get-function-configuration --function-name "$worker_fn" \
        --region "${AWS_REGION:-sa-east-1}" &>/dev/null 2>&1; then
        info "Forçando cold start do worker Lambda..."
        local ts
        ts=$(date +%s)
        aws lambda update-function-configuration \
            --function-name "$worker_fn" \
            --region "${AWS_REGION:-sa-east-1}" \
            --environment "$(
                aws lambda get-function-configuration \
                    --function-name "$worker_fn" \
                    --region "${AWS_REGION:-sa-east-1}" \
                    --query 'Environment' \
                    --output json | \
                python3 -c "
import sys, json
env = json.load(sys.stdin)
env['Variables']['DEPLOY_TS'] = '$ts'
print(json.dumps(env))
"
            )" \
            --query 'LastModified' --output text \
            --no-cli-pager &>/dev/null 2>&1 && \
            success "Worker atualizado — próxima chamada faz cold start." || \
            warn "Não foi possível atualizar env var do worker."
    fi
}

# ── Esvazia bucket S3 antes do destroy (versioning habilitado) ────────────────
empty_s3_bucket() {
    local bucket="$1"
    if ! aws s3api head-bucket --bucket "$bucket" &>/dev/null 2>&1; then
        return 0  # Bucket não existe
    fi
    info "Esvaziando bucket S3: $bucket (incluindo versões)..."

    # Remove objetos correntes
    aws s3 rm "s3://$bucket" --recursive --quiet 2>/dev/null || true

    # Remove versões antigas e delete markers (necessário com versioning)
    aws s3api list-object-versions --bucket "$bucket" \
        --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
        --output json 2>/dev/null | \
    python3 -c "
import sys, json, subprocess
data = json.load(sys.stdin)
objs = data.get('Objects') or []
if not objs:
    sys.exit(0)
# Deleta em lotes de 1000
for i in range(0, len(objs), 1000):
    batch = objs[i:i+1000]
    payload = json.dumps({'Objects': batch, 'Quiet': True})
    subprocess.run([
        'aws', 's3api', 'delete-objects',
        '--bucket', '$bucket',
        '--delete', payload,
        '--no-cli-pager'
    ], capture_output=True)
print(f'  {len(objs)} versões removidas.')
" 2>/dev/null || true

    # Remove delete markers
    aws s3api list-object-versions --bucket "$bucket" \
        --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' \
        --output json 2>/dev/null | \
    python3 -c "
import sys, json, subprocess
data = json.load(sys.stdin)
objs = data.get('Objects') or []
if not objs:
    sys.exit(0)
for i in range(0, len(objs), 1000):
    batch = objs[i:i+1000]
    payload = json.dumps({'Objects': batch, 'Quiet': True})
    subprocess.run([
        'aws', 's3api', 'delete-objects',
        '--bucket', '$bucket',
        '--delete', payload,
        '--no-cli-pager'
    ], capture_output=True)
print(f'  {len(objs)} delete markers removidos.')
" 2>/dev/null || true

    success "Bucket $bucket esvaziado."
}

# ── Terraform destroy ─────────────────────────────────────────────────────────
tf_purge() {
    header "Destruindo infraestrutura AWS"
    cd "$TF_DIR"

    # Tenta ler bucket antes do destroy
    local s3_bucket=""
    s3_bucket=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")
    if [[ -z "$s3_bucket" ]]; then
        s3_bucket="langchain-agent-artifacts-dev"  # fallback
    fi

    empty_s3_bucket "$s3_bucket"

    info "terraform destroy..."
    # anthropic_api_key não é necessária no destroy, mas a variável é obrigatória
    local var_args=()
    if [[ ! -f "$TF_DIR/secrets.auto.tfvars" ]]; then
        var_args+=(-var "anthropic_api_key=destroy-placeholder")
    fi
    terraform destroy -auto-approve -input=false -no-color "${var_args[@]}"
    success "Todos os recursos AWS removidos."
}

# ── Limpa artefatos locais de build ──────────────────────────────────────────
clean_local() {
    header "Limpando artefatos locais"
    local layer_dir="$TF_DIR/modules/lambda_layer"

    rm -rf "$layer_dir/layer_content" "$layer_dir/dist" \
           "$TF_DIR/modules/lambda/dist" 2>/dev/null && \
        success "Artefatos de build removidos." || true
}

# ── Status atual ──────────────────────────────────────────────────────────────
cmd_status() {
    header "Estado atual da infraestrutura"
    cd "$TF_DIR"

    if [[ ! -f "terraform.tfstate" ]] && [[ ! -d ".terraform" ]]; then
        warn "Nenhum estado Terraform encontrado. Execute 'deploy' primeiro."
        return
    fi

    local count
    count=$(terraform state list 2>/dev/null | wc -l | tr -d ' ')
    info "Recursos no state: $count"

    read_tf_outputs

    if [[ -n "$API_ENDPOINT" ]]; then
        success "API endpoint: $API_ENDPOINT"
        echo ""
        echo "  Teste rápido (modo persona — Júlia/Jovem Digital):"
        echo "  curl -X POST '$API_ENDPOINT/query' \\"
        echo "    -H 'Content-Type: application/json' \\"
        echo "    -d '{\"pergunta\":\"Me fale sobre cashback\",\"modo\":\"persona\",\"cluster_id\":1}'"
    else
        warn "API endpoint não disponível (infraestrutura não deployada?)."
    fi

    echo ""
    echo "  Estimativa de custo (infraestrutura ativa, sem chamadas):"
    echo "  - OpenSearch t3.small.search : ~USD 26/mês"
    echo "  - S3, DynamoDB, SQS, SNS     : ~USD 1/mês"
    echo "  - Secrets Manager (1 secret) : ~USD 0,40/mês"
    echo "  - Lambda + API Gateway       : pay-per-use (zero quando idle)"
    echo "  ─────────────────────────────────────────────────────"
    echo "  Total estimado idle          : ~USD 27-28/mês"
    echo ""
    echo "  Execute './aws_manager.sh purge' para zerar os custos."
}

# ── Comando deploy ────────────────────────────────────────────────────────────
cmd_deploy() {
    check_prereqs
    ensure_tf_outputs
    tf_deploy
    index_data

    header "Deploy concluído"
    read_tf_outputs
    success "API disponível em: ${API_ENDPOINT:-'(rode status para ver)'}"
    echo ""
    echo "  Modos disponíveis:"
    echo "  segmento | persona (cluster_id 0-3) | twin (cliente_id + dados_cliente)"
    echo ""
    echo "  Para destruir todos os recursos: ./aws_manager.sh purge"
}

# ── Comando purge ─────────────────────────────────────────────────────────────
cmd_purge() {
    local auto_yes="${1:-}"

    header "Purge — Remoção de todos os recursos AWS"
    warn "Esta operação é irreversível. Todos os recursos e dados serão removidos."
    warn "Custo parará de ser gerado após a conclusão (~10-15 min)."
    echo ""

    if [[ "$auto_yes" != "--yes" && "$auto_yes" != "-y" ]]; then
        read -r -p "  Confirma? Digite 'purge' para continuar: " confirm
        if [[ "$confirm" != "purge" ]]; then
            info "Operação cancelada."
            exit 0
        fi
    fi

    tf_purge
    clean_local

    header "Purge concluído"
    success "Nenhum recurso AWS ativo. Custos zerados."
}

# ── Entry point ───────────────────────────────────────────────────────────────
main() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        deploy) cmd_deploy ;;
        purge)  cmd_purge "${1:-}" ;;
        status) cmd_status ;;
        *)
            echo "Uso: $0 {deploy|purge|status}"
            echo ""
            echo "  deploy         Provisiona infra AWS e indexa dados"
            echo "  purge          Destroi todos os recursos (para custos)"
            echo "  purge --yes    Purge sem confirmação interativa"
            echo "  status         Exibe estado atual e URL da API"
            exit 1
            ;;
    esac
}

main "$@"
