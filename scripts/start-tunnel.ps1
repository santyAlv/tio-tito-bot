# Expone el Cerebro local a internet con Cloudflare Tunnel (gratis)
# Uso: .\scripts\start-tunnel.ps1
# Requiere: cloudflared instalado
# Alternativa mejor: Tailscale (ver docs/laptop-local.md)

$ErrorActionPreference = "Stop"

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "cloudflared no esta instalado."
    Write-Host ""
    Write-Host "Opcion 1 - Descargar manualmente:"
    Write-Host "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    Write-Host ""
    Write-Host "Opcion 2 - Con winget:"
    Write-Host "  winget install Cloudflare.cloudflared"
    Write-Host ""
    Write-Host "Opcion 3 (recomendada): usar Tailscale en vez de tunel"
    Write-Host "  https://tailscale.com"
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Iniciando tunel hacia localhost:8000..."
Write-Host "Copia la URL https://....trycloudflare.com y ponela en n8n:"
Write-Host "  CEREBRO_URL = https://....trycloudflare.com"
Write-Host ""
Write-Host "Mantene esta ventana abierta."
Write-Host ""

cloudflared tunnel --url http://localhost:8000
