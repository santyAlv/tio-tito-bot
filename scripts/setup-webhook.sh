#!/usr/bin/env bash
set -euo pipefail

# Carga variables desde .env si existe
if [ -f .env ]; then
  # shellcheck disable=SC1091
  source "$(dirname "$0")/load-env.sh"
  load_env .env
fi

EVOLUTION_URL="${EVOLUTION_URL:?Falta EVOLUTION_URL en .env}"
EVOLUTION_API_KEY="${EVOLUTION_API_KEY:?Falta EVOLUTION_API_KEY en .env}"
EVOLUTION_INSTANCE="${EVOLUTION_INSTANCE:-tio-tito}"
N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL:?Falta N8N_WEBHOOK_URL en .env}"

echo "Configurando webhook de Evolution..."
echo "  Instancia: $EVOLUTION_INSTANCE"
echo "  URL:       $N8N_WEBHOOK_URL"

curl -s -X POST "${EVOLUTION_URL}/webhook/set/${EVOLUTION_INSTANCE}" \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"enabled\": true,
    \"url\": \"${N8N_WEBHOOK_URL}\",
    \"webhookByEvents\": false,
    \"webhookBase64\": false,
    \"events\": [\"MESSAGES_UPSERT\"]
  }" | python3 -m json.tool 2>/dev/null || true

echo ""
echo "Webhook configurado. Verificá en el manager de Evolution."
