# MemPalace Project Memory - PowerShell Script
param([string]$Action = "help")

$PALACE_PATH = "$env:USERPROFILE\.mempalace\vscode_decisions"
$PROJECT_NAME = Split-Path -Leaf (Get-Location)

if ($Action -eq "save" -or $Action -eq "s") {
    Write-Host "💾 Salvando decisão para projeto: $PROJECT_NAME" -ForegroundColor Green
    $decision = Read-Host "Decisão"
    $category = Read-Host "Categoria [tech/user/business]"
    if (-not $category) { $category = "tech" }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    $content = "$timestamp - $decision"
    
    # Criar arquivo temporário
    $tempDir = "$env:TEMP\mempalace_decisions"
    $tempFile = "$tempDir\${category}_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
    
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    "# Decisão $category`n`n$content" | Out-File -FilePath $tempFile -Encoding UTF8
    
    # Mine o arquivo
    python -m mempalace mine $tempFile --palace $PALACE_PATH
    Write-Host "✅ Decisão salva!" -ForegroundColor Green
    
    Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
}
elseif ($Action -eq "search" -or $Action -eq "find") {
    $query = Read-Host "🔍 Buscar decisões sobre"
    Write-Host "📋 Resultados para '$query':" -ForegroundColor Cyan
    python -m mempalace search $query --palace $PALACE_PATH
}
elseif ($Action -eq "context" -or $Action -eq "c") {
    Write-Host "🌅 Contexto essencial do projeto:" -ForegroundColor Cyan
    python -m mempalace wake-up --palace $PALACE_PATH
}
elseif ($Action -eq "init") {
    Write-Host "🏰 Inicializando MemPalace..." -ForegroundColor Cyan
    
    if (-not (Test-Path $PALACE_PATH)) {
        New-Item -ItemType Directory -Path $PALACE_PATH -Force | Out-Null
        Write-Host "📁 Diretório criado: $PALACE_PATH" -ForegroundColor Green
    }
    
    python -c "import mempalace; print('✅ MemPalace disponível!')"
    python -m mempalace init $PALACE_PATH --palace $PALACE_PATH
    Write-Host "🎯 Palace configurado!" -ForegroundColor Green
}
elseif ($Action -eq "status") {
    Write-Host "📊 Status do MemPalace:" -ForegroundColor Cyan
    python -m mempalace status --palace $PALACE_PATH
}
else {
    Write-Host "🧠 MemPalace Project Memory" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Uso: .\project-memory-simple.ps1 [comando]" -ForegroundColor White
    Write-Host ""
    Write-Host "Comandos:" -ForegroundColor Yellow
    Write-Host "  save     - Salvar decisão" -ForegroundColor Green
    Write-Host "  search   - Buscar decisões" -ForegroundColor Green
    Write-Host "  context  - Carregar contexto" -ForegroundColor Green
    Write-Host "  init     - Inicializar palace" -ForegroundColor Green
    Write-Host "  status   - Ver status" -ForegroundColor Green
}