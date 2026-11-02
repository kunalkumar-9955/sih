# ============================================================
# SIH26002 — Start Next.js Web Frontend (Windows PowerShell)
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SIH26002 MDoNER Intelligence Platform — Web Frontend     " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$WebDir = Join-Path (Join-Path $ProjectRoot "frontend") "web"

Set-Location $WebDir

Write-Host "[1/3] Verifying Node.js Environment..." -ForegroundColor Yellow
$NodeCmd = (Get-Command node -ErrorAction SilentlyContinue)
if (-not $NodeCmd) {
    Write-Host "[ERROR] Node.js was not found in your PATH. Please install Node.js v18+." -ForegroundColor Red
    exit 1
}
Write-Host "  Using: Node $(node --version)" -ForegroundColor Green

Write-Host "[2/3] Checking Node Modules Dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules")) {
    Write-Host "  node_modules not detected. Installing dependencies via npm install..." -ForegroundColor Yellow
    npm install
} else {
    Write-Host "  node_modules directory found." -ForegroundColor Green
}

Write-Host "[3/3] Starting Next.js Frontend server on http://localhost:3000/ ..." -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop the server." -ForegroundColor Gray
npm run dev
