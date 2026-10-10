# Importar historial de WhatsApp para que Tío Tito aprenda el grupo
# Uso: .\scripts\import-chat.ps1 -Archivo "C:\Downloads\Chat de Mi Grupo.txt"

param(
    [Parameter(Mandatory=$true)]
    [string]$Archivo,

    [string]$GrupoJid = "",
    [int]$MaxMensajes = 500
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $Archivo)) {
    Write-Host "ERROR: No existe el archivo: $Archivo"
    exit 1
}

# Cargar .env
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.+?)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

if (-not $GrupoJid) {
    $GrupoJid = $env:GRUPO_JID
}
if (-not $GrupoJid -or $GrupoJid -eq "COMPLETAR") {
    Write-Host "ERROR: Falta GRUPO_JID en .env o parametro -GrupoJid"
    exit 1
}

$contenido = Get-Content $Archivo -Raw -Encoding UTF8
if (-not $contenido) {
    $contenido = Get-Content $Archivo -Raw -Encoding Default
}

Write-Host ""
Write-Host "Importando chat a Tio Tito..."
Write-Host "  Archivo:  $Archivo"
Write-Host "  Grupo:    $GrupoJid"
Write-Host "  Max:      $MaxMensajes mensajes"
Write-Host ""

$body = @{
    grupo_jid = $GrupoJid
    contenido_txt = $contenido
    max_mensajes = $MaxMensajes
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod `
        -Uri "http://localhost:8000/importar-chat" `
        -Method POST `
        -ContentType "application/json; charset=utf-8" `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($body))

    Write-Host "Listo! $($response.mensaje)"
    Write-Host ""
    Write-Host "Verifica:"
    Write-Host "  curl http://localhost:8000/contexto/$GrupoJid"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "Asegurate que el Cerebro este corriendo:"
    Write-Host "  .\scripts\run-local.ps1"
    exit 1
}
