#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-validate}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/infraestrutura/.terraform/providers"
SHARED_DATA_DIR="$ROOT/.tfdata_shared"
mkdir -p "$SHARED_DATA_DIR"

if command -v terraform >/dev/null 2>&1; then
  TF_MODE="native"
  TF_BIN="terraform"
elif command -v pwsh >/dev/null 2>&1; then
  TF_MODE="pwsh"
  PWSH_BIN="pwsh"
elif command -v powershell.exe >/dev/null 2>&1; then
  TF_MODE="pwsh"
  PWSH_BIN="powershell.exe"
else
  echo "Terraform nao encontrado no PATH e pwsh indisponivel para fallback." >&2
  exit 1
fi
ORDER=(
  aws_dynamodb
  aws_sqs
  aws_sns
  aws_s3
  aws_vpc_endpoints
  aws_secrets
  aws_iam
  aws_lambda_layer
  aws_opensearch
  aws_neptune
  aws_neptune_proxy
  aws_neptune_replication
  aws_lambda_worker
  aws_api_gateway
  aws_cloudfront_frontend
)

for stack in "${ORDER[@]}"; do
  path="$ROOT/$stack"
  export TF_DATA_DIR="$SHARED_DATA_DIR/$stack"
  echo "=== [$MODE] $stack ==="
  if [[ "$TF_MODE" == "native" ]]; then
    "$TF_BIN" -chdir="$path" init -backend=false -input=false -no-color -plugin-dir="$PLUGIN_DIR" >/dev/null
  else
    "$PWSH_BIN" -NoProfile -Command "terraform -chdir='$path' init -backend=false -input=false -no-color -plugin-dir='$PLUGIN_DIR' | Out-Null"
  fi
  case "$MODE" in
    validate)
      if [[ "$TF_MODE" == "native" ]]; then
        "$TF_BIN" -chdir="$path" validate -no-color
      else
        "$PWSH_BIN" -NoProfile -Command "terraform -chdir='$path' validate -no-color"
      fi
      ;;
    plan)
      if [[ "$TF_MODE" == "native" ]]; then
        "$TF_BIN" -chdir="$path" plan -input=false -no-color
      else
        "$PWSH_BIN" -NoProfile -Command "terraform -chdir='$path' plan -input=false -no-color"
      fi
      ;;
    apply)
      if [[ "$TF_MODE" == "native" ]]; then
        "$TF_BIN" -chdir="$path" apply -auto-approve -input=false -no-color
      else
        "$PWSH_BIN" -NoProfile -Command "terraform -chdir='$path' apply -auto-approve -input=false -no-color"
      fi
      ;;
    *) echo "Modo invalido: $MODE"; exit 1 ;;
  esac
done
