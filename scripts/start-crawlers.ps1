# One-click launcher: single cooperative ingestion pipeline (crawl + backfill + enrich + purify)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ""
Write-Host "Research Feed - starting cooperative crawler pipeline..." -ForegroundColor Cyan
Write-Host ""

$lockFile = Join-Path $Root "data\pipeline.lock"
if (Test-Path $lockFile) {
    $existingPid = Get-Content $lockFile -ErrorAction SilentlyContinue
    Write-Host "Pipeline may already be running (PID $existingPid)." -ForegroundColor Yellow
    Write-Host "Run 'Stop Crawlers.bat' first, then try again."
    Write-Host ""
    exit 1
}

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "First run: creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
}

$pipelineTitle = "Research Feed Pipeline"
$pipelineCmd = "title $pipelineTitle && cd /d `"$Root`" && .venv\Scripts\python pipeline\cooperative.py"

Write-Host "Opening one pipeline window (crawl, citations, enrich, metrics, purify)..."
Start-Process cmd.exe -ArgumentList "/k", $pipelineCmd

Write-Host ""
Write-Host "Cooperative pipeline is running!" -ForegroundColor Green
Write-Host "  One window handles everything in order - no separate purifier loop."
Write-Host "  Close that window or run 'Stop Crawlers.bat' to shut down."
Write-Host ""
