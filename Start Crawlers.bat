@echo off
title Start Crawlers
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-crawlers.ps1"
echo.
pause
