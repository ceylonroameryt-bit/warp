# Warp Ladger — Start Local Stack + Public Cloudflare Tunnel
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Warp Ladger — Free Public Host Launcher " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$root = $PSScriptRoot

# 1. Start Backend (Port 8001)
Write-Host "`n[1/3] Starting FastAPI Backend on port 8001..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "$root/backend/.venv/Scripts/python.exe" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001" -WorkingDirectory "$root/backend" -PassThru

# 2. Start Frontend (Port 3001)
Write-Host "[2/3] Starting Next.js Frontend on port 3001..." -ForegroundColor Yellow
$env:NODE_OPTIONS = "--max-old-space-size=4096"
$frontendJob = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory "$root/apps/web" -PassThru

# Give servers 3 seconds to spin up
Start-Sleep -Seconds 3

# 3. Start Cloudflare Tunnel
Write-Host "[3/3] Starting Cloudflare Tunnel..." -ForegroundColor Yellow
if (Test-Path "$root/infrastructure/tools/cloudflared.exe") {
    & "$root/infrastructure/tools/cloudflared.exe" tunnel --url http://localhost:3001
} else {
    Write-Host "Cloudflared binary not found. Falling back to localtunnel..." -ForegroundColor Yellow
    npx -y localtunnel --port 3001
}
