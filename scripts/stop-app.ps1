# Stop Research Feed API and frontend dev servers
$ports = @(8000, 3000)
$stopped = 0

foreach ($port in $ports) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            $stopped++
        }
}

Write-Host ""
if ($stopped -gt 0) {
    Write-Host "Research Feed stopped (freed ports 8000 and/or 3000)." -ForegroundColor Green
} else {
    Write-Host "Nothing was running on ports 8000 or 3000." -ForegroundColor Yellow
}
Write-Host ""
