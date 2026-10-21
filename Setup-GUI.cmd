@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-gui.ps1"
if errorlevel 1 (
    pause
    exit /b 1
)
exit /b 0
