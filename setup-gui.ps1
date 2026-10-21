$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$desktopProbe = @'
import sys
try:
    import tkinter
    assert sys.version_info >= (3, 11)
except Exception:
    sys.exit(1)
'@
try {
    $venvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    $ready = $false
    if (Test-Path -LiteralPath $venvPython) {
        & $venvPython -c $desktopProbe 2>$null
        $ready = $LASTEXITCODE -eq 0
    }
    if (-not $ready) {
        $candidates = @()
        if (Test-Path -LiteralPath '.python') {
            $candidates += Get-ChildItem -LiteralPath '.python' -Directory | ForEach-Object { Join-Path $_.FullName 'python.exe' }
        }
        $installed = Get-Command python -ErrorAction SilentlyContinue
        if ($installed) { $candidates += $installed.Source }
        $runtime = $null
        foreach ($candidate in $candidates) {
            if (Test-Path -LiteralPath $candidate) {
                & $candidate -c $desktopProbe 2>$null
                if ($LASTEXITCODE -eq 0) { $runtime = $candidate; break }
            }
        }
        if (-not $runtime) {
            if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
                throw 'Python 3.11+ with Tcl/Tk is required. Install it from python.org with Tcl/Tk enabled, or install uv, then run this setup again.'
            }
            & uv python install 3.12 --install-dir .python --no-bin
            if ($LASTEXITCODE -ne 0) { throw 'Could not install the project Python runtime.' }
            $runtime = Get-ChildItem -LiteralPath '.python' -Directory -Filter 'cpython-3.12.*' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { Join-Path $_.FullName 'python.exe' }
        }
        & $runtime -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the project virtual environment.' }
    }
    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your network and retry.' }
    & $venvPython -c 'import tkinter, tomlkit, curl_cffi, rich, py7zr; root = tkinter.Tk(); root.withdraw(); root.destroy()'
    if ($LASTEXITCODE -ne 0) { throw 'Desktop runtime verification failed.' }
    Write-Host 'Ready. Double-click Start-GUI.cmd to open Nexus Downloader.'
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
