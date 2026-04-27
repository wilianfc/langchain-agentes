# MemPalace Project Memory - PowerShell Script
# Uso: .\project-memory.ps1 [save|search|context|problem|init]

param(
    [Parameter(Position=0)]
    [ValidateSet("save", "s", "search", "find", "context", "c", "problem", "p", "init", "help")]
    [string]$Action = "help"
)

$PALACE_PATH = "$env:USERPROFILE\.mempalace\vscode_decisions"
$PROJECT_NAME = Split-Path -Leaf (Get-Location)

function Save-Decision {
    Write-Host "💾 Salvando decisão para projeto: $PROJECT_NAME" -ForegroundColor Green
    $decision = Read-Host "Decisão"
    $category = Read-Host "Categoria [tech/user/business/config]"
    if (-not $category) { $category = "tech" }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    $content = "$timestamp - $decision"
    
    try {
        $result = python -m mempalace add-drawer --wing $PROJECT_NAME --room $category --content $content --palace $PALACE_PATH 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Decisão salva!" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Erro: $result" -ForegroundColor Red
        }
    } catch {
        Write-Host "⚠️ MemPalace não está instalado. Execute: pip install mempalace" -ForegroundColor Yellow
    }
}

function Search-Decisions {
    $query = Read-Host "🔍 Buscar decisões sobre"
    Write-Host "📋 Resultados para '$query':" -ForegroundColor Cyan
    
    try {
        python -m mempalace search $query --palace $PALACE_PATH
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️ Nenhum resultado encontrado ou erro na busca" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️ MemPalace não está instalado. Execute: pip install mempalace" -ForegroundColor Yellow
    }
}

function Load-Context {
    Write-Host "🌅 Contexto essencial do projeto:" -ForegroundColor Cyan
    
    try {
        python -m mempalace wake-up --palace $PALACE_PATH
        if ($LASTEXITCODE -ne 0) {
            Write-Host "📝 Nenhum contexto encontrado ainda. Comece salvando algumas decisões!" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️ MemPalace não está instalado. Execute: pip install mempalace" -ForegroundColor Yellow
    }
}

function Save-Problem {
    Write-Host "🐛 Salvando problema resolvido para projeto: $PROJECT_NAME" -ForegroundColor Green
    $problem = Read-Host "Problema encontrado"
    $solution = Read-Host "Solução aplicada"
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    $content = "$timestamp - PROBLEMA: $problem | SOLUÇÃO: $solution"
    
    try {
        $result = python -m mempalace add-drawer --wing $PROJECT_NAME --room "problemas_resolvidos" --content $content --palace $PALACE_PATH 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Problema e solução salvos!" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Erro: $result" -ForegroundColor Red
        }
    } catch {
        Write-Host "⚠️ MemPalace não está instalado. Execute: pip install mempalace" -ForegroundColor Yellow
    }
}

function Initialize-Palace {
    Write-Host "🏰 Inicializando MemPalace..." -ForegroundColor Cyan
    
    # Criar diretório se não existir
    if (-not (Test-Path $PALACE_PATH)) {
        New-Item -ItemType Directory -Path $PALACE_PATH -Force | Out-Null
        Write-Host "📁 Diretório criado: $PALACE_PATH" -ForegroundColor Green
    }
    
    try {
        # Testar se MemPalace está funcionando
        python -c "import mempalace; print('✅ MemPalace instalado e funcionando!')"
        Write-Host "🎯 Palace configurado em: $PALACE_PATH" -ForegroundColor Green
        Write-Host "📋 Use os comandos:" -ForegroundColor White
        Write-Host "   .\project-memory.ps1 save     - Salvar decisão" -ForegroundColor Gray
        Write-Host "   .\project-memory.ps1 search   - Buscar decisões" -ForegroundColor Gray
        Write-Host "   .\project-memory.ps1 context  - Carregar contexto" -ForegroundColor Gray
        Write-Host "   .\project-memory.ps1 problem  - Salvar problema resolvido" -ForegroundColor Gray
    } catch {
        Write-Host "⚠️ MemPalace não está instalado!" -ForegroundColor Red
        Write-Host "📦 Execute: pip install mempalace" -ForegroundColor Yellow
    }
}

function Show-Help {
    Write-Host "🧠 MemPalace Project Memory - Gerenciador de Decisões de Projeto" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Uso: .\project-memory.ps1 [comando]" -ForegroundColor White
    Write-Host ""
    Write-Host "Comandos disponíveis:" -ForegroundColor Yellow
    Write-Host "  save, s       - Salvar nova decisão técnica" -ForegroundColor Green
    Write-Host "  search, find  - Buscar decisões anteriores" -ForegroundColor Green
    Write-Host "  context, c    - Carregar contexto essencial (~170 tokens)" -ForegroundColor Green
    Write-Host "  problem, p    - Salvar problema e solução encontrada" -ForegroundColor Green
    Write-Host "  init          - Inicializar/testar configuração do MemPalace" -ForegroundColor Green
    Write-Host "  help          - Mostrar esta ajuda" -ForegroundColor Green
    Write-Host ""
    Write-Host "Atalhos VS Code:" -ForegroundColor Yellow
    Write-Host "  Ctrl+Alt+D    - Salvar decisão" -ForegroundColor Gray
    Write-Host "  Ctrl+Alt+S    - Buscar decisões" -ForegroundColor Gray  
    Write-Host "  Ctrl+Alt+C    - Carregar contexto" -ForegroundColor Gray
    Write-Host "  Ctrl+Alt+P    - Salvar problema" -ForegroundColor Gray
    Write-Host "  Ctrl+Alt+I    - Inicializar palace" -ForegroundColor Gray
}

# Executar ação baseada no parâmetro
switch ($Action) {
    { $_ -in "save", "s" } { Save-Decision }
    { $_ -in "search", "find" } { Search-Decisions }
    { $_ -in "context", "c" } { Load-Context }
    { $_ -in "problem", "p" } { Save-Problem }
    "init" { Initialize-Palace }
    default { Show-Help }
}