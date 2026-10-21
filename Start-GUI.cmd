@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" goto setup
".venv\Scripts\python.exe" -c "import tkinter, tomlkit, curl_cffi, rich, py7zr" >nul 2>&1
if errorlevel 1 goto setup
goto launch
:setup
call "%~dp0Setup-GUI.cmd"
if errorlevel 1 exit /b 1
:launch
start "" ".venv\Scripts\pythonw.exe" "%~dp0gui.py"
