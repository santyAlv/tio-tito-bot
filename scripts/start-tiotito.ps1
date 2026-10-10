# Arranca Tio Tito completo en la laptop
# Uso: .\scripts\start-tiotito.ps1
# Opciones:
#   .\scripts\start-tiotito.ps1 -Tailscale   (solo cerebro, sin tunel)
#   .\scripts\start-tiotito.ps1 -Tunnel        (cerebro + cloudflare tunnel)

param(
    [switch]$Tailscale,
    [switch]$Tunnel
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "========================================"
Write-Host "  Tio Tito - Modo Laptop"
Write-Host "========================================"
Write-Host ""

# Verificar .env
$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: No existe .env"
    Write-Host "  copy .env.example .env"
    Write-Host "  notepad .env"
    exit 1
}

# Verificar Groq key
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*GROQ_API_KEY\s*=\s*(.+?)\s*$') {
        if ($matches[1] -match 'gsk_') { $script:HasGroq = $true }
    }
}
if (-not $script:HasGroq) {
    Write-Host "AVISO: Configura GROQ_API_KEY en .env"
    Write-Host "  https://console.groq.com"
    Write-Host ""
}

# Modo conexion
if ($Tailscale) {
    Write-Host "Modo: Tailscale"
    Write-Host "  En n8n configura: CEREBRO_URL = http://TU_IP_TAILSCALE:8000"
    Write-Host "  tailscale ip -4  para ver tu IP"
    Write-Host ""
    & "$PSScriptRoot\run-local.ps1"
    exit
}

if (-not $Tunnel) {
    Write-Host "Modo: Solo Cerebro (localhost)"
    Write-Host ""
    Write-Host "Para que n8n en la VPS llegue a tu laptop, usa una de:"
    Write-Host "  .\scripts\start-tiotito.ps1 -Tailscale   (recomendado)"
    Write-Host "  .\scripts\start-tiotito.ps1 -Tunnel       (cloudflare)"
    Write-Host ""
    & "$PSScriptRoot\run-local.ps1"
    exit
}

# Modo tunel: cerebro en background + cloudflared
Write-Host "Modo: Cerebro + Cloudflare Tunnel"
Write-Host ""

$CerebroDir = Join-Path $Root "services\cerebro"
$VenvPython = Join-Path $CerebroDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Instalando dependencias..."
    & "$PSScriptRoot\run-local.ps1"
    exit
}

# Cargar .env
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+?)\s*=\s*(.+?)\s*$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

$dataDir = Join-Path $Root "data"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
$dbPath = (Join-Path $dataDir "tiotito.db") -replace '\\', '/'
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:LLM_PROVIDER = if ($env:LLM_PROVIDER) { $env:LLM_PROVIDER } else { "groq" }
$env:PROMPTS_DIR = Join-Path $Root "prompts"

Write-Host "Iniciando Cerebro en background..."
$cerebroJob = Start-Job -ScriptBlock {
    param($Python, $Dir)
    Set-Location $Dir
    & $Python -m uvicorn main:app --host 0.0.0.0 --port 8000
} -ArgumentList $VenvPython, $CerebroDir

Start-Sleep -Seconds 3

try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/salud" -TimeoutSec 5
    Write-Host "Cerebro OK: llm=$($health.llm), db=$($health.db)"
} catch {
    Write-Host "ERROR: Cerebro no arranco. Revisa GROQ_API_KEY en .env"
    Stop-Job $cerebroJob; Remove-Job $cerebroJob
    exit 1
}

Write-Host ""
Write-Host "Iniciando tunel Cloudflare..."
Write-Host "Copia la URL en n8n -> CEREBRO_URL"
Write-Host "Ctrl+C para detener todo"
Write-Host ""

try {
    & "$PSScriptRoot\start-tunnel.ps1"
} finally {
    Stop-Job $cerebroJob -ErrorAction SilentlyContinue
    Remove-Job $cerebroJob -ErrorAction SilentlyContinue
    Write-Host "Tio Tito detenido."
}
