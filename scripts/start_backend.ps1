# ============================================================
# SIH26002 — Start Backend Development Server (Windows PowerShell)
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SIH26002 MDoNER Intelligence Platform — Backend Server   " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"

Set-Location $BackendDir

Write-Host "[1/3] Verifying Python Environment..." -ForegroundColor Yellow
$PythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $PythonCmd) {
    Write-Host "[ERROR] Python was not found in your PATH. Please install Python 3.11+." -ForegroundColor Red
    exit 1
}
Write-Host "  Using: $(python --version)" -ForegroundColor Green

Write-Host "[2/3] Performing Django System Check..." -ForegroundColor Yellow
python manage.py check
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Django system check reported issues." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "  Django Check: 0 issues identified (Clean)." -ForegroundColor Green

Write-Host "[3/3] Starting Django REST Framework server on http://localhost:8000/ ..." -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop the server." -ForegroundColor Gray
python manage.py runserver 8000
