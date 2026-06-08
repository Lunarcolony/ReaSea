# Redirects to the cooperative pipeline launcher (legacy entry point)
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "start-crawlers.ps1")
