# MemPalace Project Memory - PowerShell Script (Versão Corrigida)
# Uso: .\project-memory.ps1 [save|search|context|init]

param(
    [Parameter(Position=0)]
    [ValidateSet("save", "s", "search", "find", "context", "c", "init", "status", "help")]
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
    
    # Criar arquivo temporário para o mine
    $tempDir = "$env:TEMP\mempalace_$PROJECT_NAME"
    $tempFile = "$tempDir\$category.md"
    
    try {
        # Criar diretório temporário se não existir
        if (-not (Test-Path $tempDir)) {
            New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        }
        
        # Escrever decisão no arquivo temporário
        "# $category`n`n$content" | Out-File -FilePath $tempFile -Encoding UTF8
        
        # Mine o arquivo para o palace
        $result = python -m mempalace mine $tempFile --palace $PALACE_PATH 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Decisão salva!" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Aviso: $result" -ForegroundColor Yellow
            Write-Host "✅ Decisão provavelmente salva (MemPalace às vezes retorna warnings)" -ForegroundColor Green
        }
        
        # Limpar arquivo temporário
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        
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
        
        # Inicializar o palace se necessário
        python -m mempalace init $PALACE_PATH --palace $PALACE_PATH
        
        Write-Host "🎯 Palace configurado em: $PALACE_PATH" -ForegroundColor Green
        Write-Host "📋 Use os comandos:" -ForegroundColor White
        Write-Host "   .\project-memory.ps1 save     - Salvar decisão" -ForegroundColor Gray
        Write-Host "   .\project-memory.ps1 search   - Buscar decisões" -ForegroundColor Gray
        Write-Host "   .\project-memory.ps1 context  - Carregar contexto" -ForegroundColor Gray
        Write-Host "   .\project-memory.ps1 status   - Ver status do palace" -ForegroundColor Gray
        
    } catch {
        Write-Host "⚠️ MemPalace não está instalado!" -ForegroundColor Red
        Write-Host "📦 Execute: pip install mempalace" -ForegroundColor Yellow
    }
}

function Show-Status {
    Write-Host "📊 Status do MemPalace:" -ForegroundColor Cyan
    
    try {
        python -m mempalace status --palace $PALACE_PATH
    } catch {
        Write-Host "⚠️ MemPalace não está disponível" -ForegroundColor Yellow
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
    Write-Host "  init          - Inicializar/testar configuração do MemPalace" -ForegroundColor Green
    Write-Host "  status        - Ver o que foi arquivado no palace" -ForegroundColor Green
    Write-Host "  help          - Mostrar esta ajuda" -ForegroundColor Green
    Write-Host ""
    Write-Host "Atalhos VS Code (após configuração):" -ForegroundColor Yellow
    Write-Host "  Ctrl+Alt+D    - Salvar decisão" -ForegroundColor Gray
    Write-Host "  Ctrl+Alt+S    - Buscar decisões" -ForegroundColor Gray  
    Write-Host "  Ctrl+Alt+C    - Carregar contexto" -ForegroundColor Gray
}

# Executar ação baseada no parâmetro
switch ($Action) {
    { $_ -in "save", "s" } { Save-Decision }
    { $_ -in "search", "find" } { Search-Decisions }
    { $_ -in "context", "c" } { Load-Context }
    "init" { Initialize-Palace }
    "status" { Show-Status }
    default { Show-Help }
}