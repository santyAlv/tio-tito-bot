#!/usr/bin/env bash
# Importar historial de WhatsApp
# Uso: ./scripts/import-chat.sh /ruta/al/chat.txt

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ARCHIVO="${1:?Uso: ./scripts/import-chat.sh /ruta/al/chat.txt [grupo_jid] [max_mensajes]}"
MAX="${3:-500}"

if [ ! -f "$ARCHIVO" ]; then
  echo "ERROR: No existe: $ARCHIVO"
  exit 1
fi

if [ -f "$ROOT/.env" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/scripts/load-env.sh"
  load_env "$ROOT/.env"
fi

GRUPO_JID="${2:-${GRUPO_JID:-}}"
if [ -z "$GRUPO_JID" ] || [ "$GRUPO_JID" = "COMPLETAR" ]; then
  echo "ERROR: Falta GRUPO_JID en .env o como 2do argumento"
  exit 1
fi

echo ""
echo "Importando chat..."
echo "  Archivo: $ARCHIVO"
echo "  Grupo:   $GRUPO_JID"
echo ""

CONTENIDO=$(cat "$ARCHIVO")
JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'grupo_jid': sys.argv[1],
    'contenido_txt': open(sys.argv[2], encoding='utf-8', errors='replace').read(),
    'max_mensajes': int(sys.argv[3])
}))" "$GRUPO_JID" "$ARCHIVO" "$MAX")

curl -sf -X POST "http://localhost:8000/importar-chat" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "$JSON" | python3 -m json.tool

echo ""
echo "Verificar: curl http://localhost:8000/contexto/$GRUPO_JID?limite=5"
