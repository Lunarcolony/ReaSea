# Stop cooperative pipeline and any legacy crawler/purifier loops
$Root = Split-Path -Parent $PSScriptRoot
$stopped = 0

Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    ForEach-Object {
        $cmd = $_.CommandLine
        if ($cmd -and $cmd -like "*$Root*") {
            if ($cmd -match "pipeline\\cooperative\.py" -or $cmd -match "pipeline/cooperative\.py" -or $cmd -match "main\.py" -or $cmd -match "db_purifier\.py") {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
                $stopped++
            }
        }
    }

$lockFile = Join-Path $Root "data\pipeline.lock"
if (Test-Path $lockFile) {
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
if ($stopped -gt 0) {
    Write-Host "Stopped $stopped crawler/pipeline process(es)." -ForegroundColor Green
} else {
    Write-Host "No crawler or pipeline processes found for this project." -ForegroundColor Yellow
}
Write-Host ""
