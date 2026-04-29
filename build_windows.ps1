$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path .venv)) {
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

pyinstaller --noconfirm local_image_ocr_toolbox.spec

Write-Host ""
Write-Host "Build complete."
Write-Host "App folder: $root\dist\LocalImageOcrToolbox"
