# migrate_backend.ps1 - Inicializa backend remoto S3 para todos os produtos
# Uso: .\migrate_backend.ps1 [-Mode init|reconfigure] [-DryRun]
# Requer: AWS CLI configurado, bucket langchain-agent-artifacts-dev acessivel

param(
    [ValidateSet("init", "reconfigure")]
    [string]$Mode = "reconfigure",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$PRODUTOS = @(
    "aws_dynamodb",
    "aws_sqs",
    "aws_sns",
    "aws_s3",
    "aws_vpc_endpoints",
    "aws_secrets",
    "aws_iam",
    "aws_lambda_layer",
    "aws_opensearch",
    "aws_neptune",
    "aws_neptune_proxy",
    "aws_neptune_replication",
    "aws_lambda_worker",
    "aws_api_gateway",
    "aws_cloudfront_frontend"
)

$SCRIPT_DIR = $PSScriptRoot
$LOG_FILE   = Join-Path $SCRIPT_DIR "migrate_backend_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

$resultados = @()
$erros      = 0

function Write-Log {
    param([string]$msg, [string]$color = "White")
    $timestamp = Get-Date -Format "HH:mm:ss"
    $linha = "[$timestamp] $msg"
    Write-Host $linha -ForegroundColor $color
    Add-Content -Path $LOG_FILE -Value $linha
}

Write-Log "======================================================" "Cyan"
Write-Log " MIGRACAO BACKEND REMOTO - modo: $Mode" "Cyan"
Write-Log " Bucket : langchain-agent-artifacts-dev" "Cyan"
Write-Log " Lock   : langchain-agent-dev (DynamoDB)" "Cyan"
Write-Log " DryRun : $DryRun" "Cyan"
Write-Log "======================================================" "Cyan"

# Verificar acesso ao bucket antes de comecar
Write-Log "Verificando acesso ao bucket S3..." "Yellow"
try {
    aws s3 ls s3://langchain-agent-artifacts-dev --region sa-east-1 | Out-Null
    Write-Log "Bucket S3 acessivel." "Green"
} catch {
    Write-Log "ERRO: Nao foi possivel acessar o bucket. Verifique credenciais AWS." "Red"
    exit 1
}

foreach ($produto in $PRODUTOS) {
    $path = Join-Path $SCRIPT_DIR $produto
    Write-Log "" 
    Write-Log "--- $produto ---" "Yellow"

    if (-not (Test-Path $path)) {
        Write-Log "  AVISO: diretorio nao encontrado: $path" "DarkYellow"
        $resultados += [PSCustomObject]@{ Produto = $produto; Status = "SKIP - dir nao encontrado" }
        continue
    }

    if ($DryRun) {
        Write-Log "  [DryRun] Pulando terraform $Mode para $produto" "DarkGray"
        $resultados += [PSCustomObject]@{ Produto = $produto; Status = "DryRun" }
        continue
    }

    try {
        if ($Mode -eq "reconfigure") {
            $output = terraform -chdir="$path" init -reconfigure -input=false 2>&1
        } else {
            $output = terraform -chdir="$path" init -migrate-state -input=false 2>&1
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Log "  OK - backend inicializado" "Green"
            $resultados += [PSCustomObject]@{ Produto = $produto; Status = "OK" }
        } else {
            Write-Log "  FALHA - codigo $LASTEXITCODE" "Red"
            Write-Log "  $output" "Red"
            $resultados += [PSCustomObject]@{ Produto = $produto; Status = "FALHA - exit $LASTEXITCODE" }
            $erros++
        }
    } catch {
        Write-Log "  EXCECAO: $_" "Red"
        $resultados += [PSCustomObject]@{ Produto = $produto; Status = "EXCECAO: $_" }
        $erros++
    }
}

Write-Log ""
Write-Log "======================================================" "Cyan"
Write-Log " RESUMO" "Cyan"
Write-Log "======================================================" "Cyan"
$resultados | ForEach-Object {
    $cor = if ($_.Status -eq "OK") { "Green" } elseif ($_.Status -like "FALHA*" -or $_.Status -like "EXCECAO*") { "Red" } else { "DarkYellow" }
    Write-Log "  $($_.Produto.PadRight(35)) $($_.Status)" $cor
}
Write-Log ""
Write-Log "Log salvo em: $LOG_FILE" "Cyan"

if ($erros -gt 0) {
    Write-Log "CONCLUIDO COM $erros ERRO(S)" "Red"
    exit 1
} else {
    Write-Log "CONCLUIDO COM SUCESSO - todos os backends inicializados" "Green"
    exit 0
}
