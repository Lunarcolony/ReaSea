# One-click launcher for Research Feed (API + Next.js frontend)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-PortListening {
    param([int]$Port)
    return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Clear-Port {
    param([int]$Port)
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [int]$MaxSeconds = 45
    )
    for ($i = 0; $i -lt $MaxSeconds; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return $true
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

Write-Host ""
Write-Host "Research Feed - starting..." -ForegroundColor Cyan
Write-Host ""

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "First run: creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
}

$nodeModules = Join-Path $Root "frontend\node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "First run: installing frontend dependencies (npm install)..." -ForegroundColor Yellow
    Push-Location (Join-Path $Root "frontend")
    npm install
    Pop-Location
}

foreach ($port in @(8000, 3000)) {
    if (Test-PortListening -Port $port) {
        Write-Host "Port $port is in use - stopping old process..." -ForegroundColor Yellow
        Clear-Port -Port $port
        Start-Sleep -Seconds 1
    }
}

$backendTitle = "Research Feed API"
$frontendTitle = "Research Feed UI"
$backendCmd = "title $backendTitle && cd /d `"$Root`" && .venv\Scripts\python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000"
$frontendCmd = "title $frontendTitle && cd /d `"$Root\frontend`" && npm run dev -- -p 3000"

Write-Host "Starting backend on http://127.0.0.1:8000 ..."
Start-Process cmd.exe -ArgumentList "/k", $backendCmd

Write-Host "Starting frontend on http://localhost:3000 ..."
Start-Process cmd.exe -ArgumentList "/k", $frontendCmd

Write-Host "Waiting for services to become ready..."
if (-not (Wait-ForUrl -Url "http://127.0.0.1:8000/health")) {
    Write-Host "Warning: API did not respond in time. Check the '$backendTitle' window for errors." -ForegroundColor Red
}

if (-not (Wait-ForUrl -Url "http://localhost:3000")) {
    Write-Host "Warning: Frontend did not respond in time. Check the '$frontendTitle' window for errors." -ForegroundColor Red
}

Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "Research Feed is running!" -ForegroundColor Green
Write-Host "  App:      http://localhost:3000"
Write-Host "  API:      http://127.0.0.1:8000"
Write-Host "  API docs: http://127.0.0.1:8000/docs"
Write-Host ""
Write-Host "Two terminal windows were opened (API + UI). Close them or run 'Stop Research Feed.bat' to shut down."
Write-Host ""
