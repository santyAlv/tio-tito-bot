# Configurar webhook de Evolution API para Tío Tito
# Uso: .\scripts\setup-webhook.ps1

$ErrorActionPreference = "Stop"

# Cargar .env
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.+?)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

$EVOLUTION_URL = $env:EVOLUTION_URL
$EVOLUTION_API_KEY = $env:EVOLUTION_API_KEY
$EVOLUTION_INSTANCE = if ($env:EVOLUTION_INSTANCE) { $env:EVOLUTION_INSTANCE } else { "tio-tito" }
$N8N_WEBHOOK_URL = $env:N8N_WEBHOOK_URL

if (-not $EVOLUTION_URL) { throw "Falta EVOLUTION_URL en .env" }
if (-not $EVOLUTION_API_KEY) { throw "Falta EVOLUTION_API_KEY en .env" }
if (-not $N8N_WEBHOOK_URL) { throw "Falta N8N_WEBHOOK_URL en .env" }

Write-Host "Configurando webhook de Evolution..."
Write-Host "  Instancia: $EVOLUTION_INSTANCE"
Write-Host "  URL:       $N8N_WEBHOOK_URL"

$body = @{
    enabled = $true
    url = $N8N_WEBHOOK_URL
    webhookByEvents = $false
    webhookBase64 = $false
    events = @("MESSAGES_UPSERT")
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "$EVOLUTION_URL/webhook/set/$EVOLUTION_INSTANCE" `
    -Method POST `
    -Headers @{ "apikey" = $EVOLUTION_API_KEY; "Content-Type" = "application/json" } `
    -Body $body

$response | ConvertTo-Json -Depth 5
Write-Host "`nWebhook configurado."
