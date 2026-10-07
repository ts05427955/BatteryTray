# Build a friend-shareable Windows exe (no console window).
# Usage (from this folder):
#   powershell -ExecutionPolicy Bypass -File .\build_exe.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$appName = "BatteryTray"
$exePath = Join-Path $PSScriptRoot "dist\$appName.exe"

# Running exe locks dist\BatteryTray.exe and blocks overwrite.
Get-Process -Name $appName, "BLEBatteryTray" -ErrorAction SilentlyContinue | ForEach-Object {
  Write-Host "Stopping running $($_.ProcessName) (PID $($_.Id))..."
  Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500

if (Test-Path $exePath) {
  try {
    [IO.File]::OpenWrite($exePath).Close()
  } catch {
    throw "Cannot overwrite $exePath — quit $appName from the tray (or Task Manager), then rebuild."
  }
}

python -m pip install -r requirements.txt pyinstaller -q
if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)" }

# hidapi is a single extension (hid*.pyd), not a package — do not use --collect-all hid.
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name $appName `
  --collect-all bleak `
  --hidden-import hid `
  --hidden-import pystray._win32 `
  main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }

if (-not (Test-Path $exePath)) {
  throw "Build finished but exe missing: $exePath"
}

Write-Host ""
Write-Host "Done. Share this file with friends:"
Write-Host "  $exePath"
Write-Host ""
Write-Host "Friend tips:"
Write-Host "  - Keep Logitech G Hub running for G502 battery"
Write-Host "  - HyperX Cloud II Wireless: plug 2.4G dongle, power headset on; close NGENUITY if battery still missing"
Write-Host "  - Windows may warn about an unsigned exe (More info -> Run anyway)"
Write-Host "  - First run can auto-start with Windows; right-click tray to disable"
