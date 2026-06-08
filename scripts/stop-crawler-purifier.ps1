# Stop crawler/purifier python processes started from this project
$Root = Split-Path -Parent $PSScriptRoot
$stopped = 0

Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    ForEach-Object {
        $cmd = $_.CommandLine
        if ($cmd -and $cmd -like "*$Root*") {
            if ($cmd -match "main\.py" -or $cmd -match "db_purifier\.py") {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
                $stopped++
            }
        }
    }

Write-Host ""
if ($stopped -gt 0) {
    Write-Host "Stopped $stopped crawler/purifier process(es)." -ForegroundColor Green
} else {
    Write-Host "No crawler or purifier processes found for this project." -ForegroundColor Yellow
}
Write-Host ""
