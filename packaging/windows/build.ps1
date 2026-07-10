# Builds the Windows installer: packaging\windows\output\ims-setup-<version>-windows-x64.exe
# Run from a machine with Python 3.11+ and Inno Setup 6 installed:
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 [-Version 1.0.0]
param([string]$Version = "0.0.0")
$ErrorActionPreference = "Stop"

$Root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location $Root

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

python packaging\fetch_postgres.py
python packaging\make_icon.py
python -m PyInstaller --noconfirm --clean --distpath packaging\dist packaging\ims.spec

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "ISCC.exe" }
& $iscc /DAppVersion=$Version "$Root\packaging\windows\installer.iss"

Write-Host "Installer: packaging\windows\output\ims-setup-$Version-windows-x64.exe"
