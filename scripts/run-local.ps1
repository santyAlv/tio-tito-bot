# Correr Tío Tito localmente sin Docker (laptop 4 GB)
# Uso: .\scripts\run-local.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

# Cargar .env
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.+?)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

$CerebroDir = Join-Path $Root "services\cerebro"
$VenvPython = Join-Path $CerebroDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creando entorno virtual..."
    python -m venv (Join-Path $CerebroDir ".venv")
    & (Join-Path $CerebroDir ".venv\Scripts\pip.exe") install -r (Join-Path $CerebroDir "requirements-lite.txt")
}

# Defaults para modo local liviano
$dataDir = Join-Path $Root "data"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
$dbPath = (Join-Path $dataDir "tiotito.db") -replace '\\', '/'
if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "sqlite:///$dbPath" }
if (-not $env:LLM_PROVIDER) { $env:LLM_PROVIDER = "groq" }
if (-not $env:PROMPTS_DIR) { $env:PROMPTS_DIR = (Join-Path $Root "prompts") }

Write-Host ""
Write-Host "Tio Tito - Cerebro local"
Write-Host "  IA:       $env:LLM_PROVIDER"
Write-Host "  DB:       $env:DATABASE_URL"
Write-Host "  URL:      http://localhost:8000"
Write-Host ""

if ($env:LLM_PROVIDER -eq "ollama") {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: Ollama no instalado. Descargalo en https://ollama.com/download"
        exit 1
    }
    $model = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5:0.5b" }
    Write-Host "  Modelo:   $model"
    ollama list 2>$null | Select-String $model | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Modelo no descargado. Corriendo: ollama pull $model"
        ollama pull $model
    }
    Write-Host ""
}

Set-Location $CerebroDir
& $VenvPython -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
