param([ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version = '0.1.1')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$templateData = (Join-Path $PSScriptRoot 'config.example.toml') + ':.'
& $python -m pip install -r requirements.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Build dependencies failed.' }
& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name NexusDownloader --distpath dist --workpath build/gui --specpath build --add-data $templateData gui.py
if ($LASTEXITCODE -ne 0) { throw 'GUI packaging failed.' }
& $python -m PyInstaller --noconfirm --clean --onefile --console --name NexusDownloaderWorker --distpath dist --workpath build/worker --specpath build --add-data $templateData --collect-all curl_cffi gui_worker.py
if ($LASTEXITCODE -ne 0) { throw 'Worker packaging failed.' }
& $python package-release.py $Version
if ($LASTEXITCODE -ne 0) { throw 'Release archive creation failed.' }
