# rebuild.ps1 — Reconstrução completa da infraestrutura langchain-agent
#
# Executa:
#   0. Validação de pré-requisitos (terraform, aws, credenciais)
#   1. terraform init (reconfigura backend local)
#   2. terraform validate
#   3. terraform plan → salva rebuild.tfplan
#   4. terraform apply rebuild.tfplan
#   5. Exibe todos os outputs finais
#
# Correcao conhecida:
#   - opensearch_extra_arns: incluir apenas IAM principals já existentes no
#     bootstrap; papéis criados pelo IAM stack são adicionados depois.
#     (MemPalace: infra_workspace_migration.md / OpenSearch InvalidTypeException)
#
# Uso:
#   .\rebuild.ps1                  # fluxo completo
#   .\rebuild.ps1 -StepOnly plan   # somente até plan (não aplica)
#   .\rebuild.ps1 -DryRun          # mostra o que faria, sem executar

param(
    [ValidateSet("init", "validate", "plan", "apply")]
    [string]$StepOnly = "apply",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$INFRA_DIR = $PSScriptRoot
$LOG = Join-Path $INFRA_DIR "rebuild_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$ERROS = 0

function Log {
    param([string]$msg, [string]$cor = "White")
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line -ForegroundColor $cor
    Add-Content -Path $LOG -Value $line
}

function Step { param([string]$t); Log ""; Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"; Log " $t" "Cyan"; Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan" }

function Run {
    param([string]$desc, [scriptblock]$cmd)
    if ($DryRun) { Log "[DryRun] $desc" "DarkGray"; return }
    try {
        & $cmd
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
        Log "  OK: $desc" "Green"
    } catch {
        Log "  FALHA: $desc — $_" "Red"
        $script:ERROS++
        throw $_   # falha na fase bloqueia as seguintes
    }
}

# ─── PRÉ-REQUISITOS ───────────────────────────────────────────────────────────
Step "FASE 0 — Pré-requisitos"

Run "terraform instalado" {
    $v = terraform version -json | ConvertFrom-Json
    Log "  Terraform: $($v.terraform_version)" "Gray"
    if ([version]$v.terraform_version -lt [version]"1.0.0") { throw "Terraform >= 1.0 requerido" }
}

Run "AWS CLI autenticado" {
    $id = aws sts get-caller-identity | ConvertFrom-Json
    Log "  Conta  : $($id.Account)" "Gray"
    Log "  Usuario: $($id.Arn)" "Gray"
    if ($id.Account -ne "113677611404") { throw "Conta inesperada: $($id.Account)" }
}

Run "regiao sa-east-1 configurada" {
    $r = aws configure get region
    if (-not $r) { $env:AWS_DEFAULT_REGION = "sa-east-1"; $r = "sa-east-1" }
    Log "  Regiao: $r" "Gray"
}

if ($ERROS -gt 0) { Log "Pre-requisitos falharam — abortando" "Red"; exit 1 }
if ($StepOnly -eq "init") { exit 0 }

# ─── INIT ─────────────────────────────────────────────────────────────────────
Step "FASE 1 — terraform init"

Run "terraform init" {
    Set-Location $INFRA_DIR
    terraform init -input=false -no-color 2>&1 | Tee-Object -Append $LOG
}

if ($StepOnly -eq "init") { Log "Parado em: init" "Yellow"; exit 0 }

# ─── VALIDATE ─────────────────────────────────────────────────────────────────
Step "FASE 2 — terraform validate"

Run "terraform validate" {
    Set-Location $INFRA_DIR
    $out = terraform validate -no-color 2>&1 | Tee-Object -Append $LOG
    if ($LASTEXITCODE -ne 0) { throw "validate falhou" }
    Log "  $($out -join ' ')" "Gray"
}

if ($StepOnly -eq "validate") { Log "Parado em: validate" "Yellow"; exit 0 }

# ─── PLAN ─────────────────────────────────────────────────────────────────────
Step "FASE 3 — terraform plan"

Run "terraform plan -out=rebuild.tfplan" {
    Set-Location $INFRA_DIR
    terraform plan -out=rebuild.tfplan -input=false -no-color 2>&1 | Tee-Object -Append $LOG
    if ($LASTEXITCODE -ne 0) { throw "plan falhou" }
}

if ($StepOnly -eq "plan") {
    Log "Plan salvo em rebuild.tfplan — revisão necessária antes do apply" "Yellow"
    exit 0
}

# ─── APPLY ────────────────────────────────────────────────────────────────────
Step "FASE 4 — terraform apply"

Log "AVISO: Aplicando infraestrutura na conta 113677611403 / sa-east-1..." "Yellow"
Log "  Nota: opensearch_extra_arns inclui usuario IAM existente (wilian)." "Gray"
Log "  Role neptune-replicator sera adicionada em fase posterior (IAM order)." "Gray"

Run "terraform apply rebuild.tfplan" {
    Set-Location $INFRA_DIR
    terraform apply -auto-approve -input=false -no-color rebuild.tfplan 2>&1 | Tee-Object -Append $LOG
    if ($LASTEXITCODE -ne 0) { throw "apply falhou" }
}

# ─── OUTPUTS ──────────────────────────────────────────────────────────────────
Step "FASE 5 — Outputs"

if (-not $DryRun) {
    Set-Location $INFRA_DIR
    $outputs = terraform output -json 2>&1 | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($outputs) {
        $outputs.PSObject.Properties | ForEach-Object {
            $v = if ($_.Value.value) { $_.Value.value } else { $_.Value }
            Log "  $($_.Name) = $v" "Cyan"
        }
    } else {
        terraform output -no-color 2>&1 | Tee-Object -Append $LOG
    }
}

# ─── RESUMO ───────────────────────────────────────────────────────────────────
Log ""
Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
Log " RESUMO REBUILD" "Cyan"
Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
Log "  Log: $LOG" "Gray"
Log "  Erros: $ERROS" $(if ($ERROS -eq 0) { "Green" } else { "Red" })
if ($ERROS -eq 0) { Log "  STATUS: INFRA RECONSTRUIDA COM SUCESSO" "Green"; exit 0 }
else              { Log "  STATUS: FALHOU — revisar log" "Red"; exit 1 }
