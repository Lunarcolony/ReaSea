# Upload Research Feed to Hack Club Nest (run from repo root).
param(
    [string]$Host = "jithesh@hackclub.app",
    [string]$RemoteDir = "~/research-feed"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$items = @(
    "api", "crawlers", "data", "deploy", "enrichment", "frontend", "jobs",
    "pipeline", "recommender", "scripts", "utils",
    "requirements.txt", "docker-compose.demo.yml", "Dockerfile.api",
    "database.py", "models.py", "paths.py", "main.py", "db_purifier.py",
    "crawler_config.json", "crawler_offsets.json"
)

Write-Host "Creating remote directory..."
ssh $Host "mkdir -p $RemoteDir"

foreach ($item in $items) {
    if (-not (Test-Path $item)) { continue }
    Write-Host "Uploading $item ..."
    scp -r $item "${Host}:${RemoteDir}/"
}

Write-Host ""
Write-Host "Upload complete. Next on the server:"
Write-Host "  ssh $Host"
Write-Host "  cd research-feed"
Write-Host "  export PUBLIC_URL=https://YOUR-SUBDOMAIN.hackclub.app"
Write-Host "  ./deploy/install-on-nest.sh"
