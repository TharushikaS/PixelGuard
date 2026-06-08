# PixelGuard local startup (Windows PowerShell).
# Assumes:
#   - MongoDB is running on $env:MONGODB_URL (default mongodb://localhost:27017)
#   - Python 3.10+ and Node 18+ are on PATH
#
# Usage:  pwsh scripts\start.ps1

$ErrorActionPreference = 'Stop'

$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

Write-Host "PixelGuard - local startup" -ForegroundColor Cyan
Write-Host "=========================="

# ---- Python venv ----
if (-not (Test-Path "backend\.venv")) {
    Write-Host "[1/4] Creating Python venv..."
    python -m venv backend\.venv
}

& "backend\.venv\Scripts\python.exe" -m pip install --quiet -r backend\requirements.txt

# ---- .env ----
if (-not (Test-Path "backend\.env")) {
    Copy-Item backend\.env.example backend\.env
    Write-Host "[!] Created backend\.env from example - edit MONGODB_URL if needed." -ForegroundColor Yellow
}

# ---- Mongo indexes ----
Write-Host "[2/4] Ensuring MongoDB indexes..."
& "backend\.venv\Scripts\python.exe" scripts\setup_db.py

# ---- Backend ----
Write-Host "[3/4] Starting FastAPI on :8000 in a new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Set-Location '$root\backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000"

# ---- Frontend ----
Write-Host "[4/4] Installing & starting React on :3000 in a new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Set-Location '$root\frontend'; npm install; npm start"

Write-Host ""
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "Backend : http://localhost:8000" -ForegroundColor Green
Write-Host "Docs    : http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Close the two spawned windows to stop the servers."
