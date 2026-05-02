Param(
    [string]$ProjectRoot = "C:\Documentos\langchain",
    [string]$BookRoot = "C:\Documentos\langchain\livro"
)

$ErrorActionPreference = "Stop"

$chapters = Get-ChildItem (Join-Path $BookRoot "chapters") -Filter "*.tex"
$rows = @()

foreach ($chapter in $chapters) {
    $content = Get-Content $chapter.FullName -Raw
    $matches = [regex]::Matches($content, '\\texttt\{([^}]*)\}')

    foreach ($m in $matches) {
        $value = $m.Groups[1].Value
        if ($value -match '(?i)\.(py|ipynb|sh|ps1|tf|json|yaml|yml|js)$') {
            $normalized = $value -replace '\\_', '_'
            $normalized = $normalized -replace '^python\s+', ''

            $exists = $false
            $resolved = ""

            $direct = Join-Path $ProjectRoot $normalized
            if (Test-Path $direct) {
                $exists = $true
                $resolved = $normalized
            } else {
                $found = Get-ChildItem $ProjectRoot -Recurse -File -ErrorAction SilentlyContinue |
                    Where-Object { $_.Name -ieq ([System.IO.Path]::GetFileName($normalized)) } |
                    Select-Object -First 1
                if ($found) {
                    $exists = $true
                    $resolved = $found.FullName.Replace($ProjectRoot + "\\", "")
                }
            }

            $rows += [pscustomobject]@{
                chapter  = $chapter.Name
                mentioned = $normalized
                exists   = $exists
                resolved = $resolved
            }
        }
    }
}

$rows = $rows | Sort-Object chapter, mentioned -Unique
$reportPath = Join-Path $BookRoot "code_refs_autocontencao_report.csv"
$rows | Export-Csv $reportPath -NoTypeInformation -Encoding UTF8

$missing = $rows | Where-Object { -not $_.exists }

Write-Output ("Referencias de codigo analisadas: " + $rows.Count)
Write-Output ("Referencias faltantes: " + $missing.Count)
Write-Output ("Relatorio: " + $reportPath)

if ($missing.Count -gt 0) {
    Write-Output "\nArquivos faltantes:" 
    $missing | Format-Table -AutoSize | Out-String | Write-Output
    exit 1
}

Write-Output "\nValidacao de autocontencao concluida com sucesso."
