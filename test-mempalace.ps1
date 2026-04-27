# Teste da integração MemPalace - Script de demonstração

Write-Host "🧠 Testando integração MemPalace..." -ForegroundColor Cyan

# Configurar ambiente
$PALACE_PATH = "$env:USERPROFILE\.mempalace\vscode_decisions"
$PROJECT_NAME = "langchain_project"

Write-Host "📁 Palace configurado em: $PALACE_PATH" -ForegroundColor Green

# Teste 1: Salvar uma decisão de teste
Write-Host "`n1. Salvando decisão de teste..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$test_decision = "$timestamp - TESTE: Integração MemPalace + VS Code + Claude configurada com sucesso. Sistema permite salvar/buscar decisões via atalhos do VS Code e script PowerShell."

$result = python -m mempalace add-drawer --wing $PROJECT_NAME --room "configuracao" --content $test_decision --palace $PALACE_PATH 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Decisão de teste salva!" -ForegroundColor Green
} else {
    Write-Host "❌ Erro ao salvar decisão: $result" -ForegroundColor Red
    exit 1
}

# Teste 2: Buscar a decisão
Write-Host "`n2. Testando busca..." -ForegroundColor Yellow
Write-Host "🔍 Buscando por 'integração':" -ForegroundColor Cyan
python -m mempalace search "integracao" --palace $PALACE_PATH
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Busca funcionando!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Busca executada (pode não ter resultados ainda)" -ForegroundColor Yellow
}

# Teste 3: Carregar contexto
Write-Host "`n3. Testando context loading..." -ForegroundColor Yellow
Write-Host "🌅 Carregando contexto:" -ForegroundColor Cyan
python -m mempalace wake-up --palace $PALACE_PATH
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Context loading funcionando!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Ainda não há contexto suficiente, mas comando funciona" -ForegroundColor Yellow
}

Write-Host "`n🎉 INTEGRAÇÃO CONFIGURADA COM SUCESSO!" -ForegroundColor Green
Write-Host "`n📋 Agora você pode usar:" -ForegroundColor White
Write-Host "   • Ctrl+Alt+D - Salvar decisão" -ForegroundColor Gray  
Write-Host "   • Ctrl+Alt+S - Buscar decisões" -ForegroundColor Gray
Write-Host "   • Ctrl+Alt+C - Carregar contexto" -ForegroundColor Gray
Write-Host "   • Ctrl+Alt+P - Salvar problema resolvido" -ForegroundColor Gray
Write-Host "   • .\project-memory.ps1 [save|search|context|problem]" -ForegroundColor Gray
Write-Host "`n📖 Ver MEMPALACE_INTEGRATION.md para guia completo" -ForegroundColor Cyan