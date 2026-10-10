#!/usr/bin/env bash
# Puente Docker n8n → Cerebro en PC via Tailscale
# Uso en VPS: bash setup-cerebro-proxy-vps.sh [IP_TAILSCALE_LAPTOP]

set -euo pipefail

LAPTOP_IP="${1:-100.64.0.5}"
N8N_NETWORK="${N8N_NETWORK:-n8n-traefik_app_network}"
N8N_CONTAINER="${N8N_CONTAINER:-n8n-main}"

echo "==> Laptop Cerebro: ${LAPTOP_IP}:8000"
curl -sf "http://${LAPTOP_IP}:8000/salud" | head -c 200
echo ""

echo "==> Proxy host (systemd)..."
systemctl enable --now cerebro-proxy 2>/dev/null || true

echo "==> Proxy Docker en red ${N8N_NETWORK}..."
docker rm -f cerebro-proxy 2>/dev/null || true
docker run -d \
  --name cerebro-proxy \
  --restart unless-stopped \
  --network "${N8N_NETWORK}" \
  alpine/socat \
  TCP-LISTEN:8000,fork,reuseaddr "TCP:${LAPTOP_IP}:8000"

sleep 2
docker ps --filter name=cerebro-proxy

echo "==> Test desde n8n-main..."
docker exec "${N8N_CONTAINER}" node -e \
  "fetch('http://cerebro-proxy:8000/salud').then(r=>r.text()).then(console.log).catch(e=>console.error(e.message))"

echo ""
echo "Listo. En n8n usá:"
echo "  http://cerebro-proxy:8000/mensaje"
echo "  http://cerebro-proxy:8000/responder"
echo "  http://cerebro-proxy:8000/mensaje-automatico"
