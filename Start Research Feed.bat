@echo off
title Research Feed Launcher
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-app.ps1"
echo.
pause
