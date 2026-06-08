@echo off
title Stop Crawlers
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-crawlers.ps1"
echo.
pause
