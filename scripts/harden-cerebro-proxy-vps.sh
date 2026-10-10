#!/usr/bin/env bash
# n8n (Docker) → Cerebro en la laptop (Tailscale)
# Detecta el gateway real de n8n. Si 172.24.0.1 ya no existe, no se queda colgado.
# Uso: bash scripts/harden-cerebro-proxy-vps.sh [IP_TAILSCALE_LAPTOP]

set -euo pipefail

LAPTOP_IP="${1:-100.64.0.5}"
N8N_CONTAINER="${2:-}"

if ! command -v socat >/dev/null 2>&1; then
  echo "Instalando socat..."
  dnf install -y socat 2>/dev/null || yum install -y socat 2>/dev/null || apt-get install -y socat
fi

detect_n8n() {
  if [[ -n "${N8N_CONTAINER}" ]] && docker inspect "${N8N_CONTAINER}" >/dev/null 2>&1; then
    echo "${N8N_CONTAINER}"
    return
  fi
  docker ps --format '{{.Names}}' | grep -iE '^n8n' | head -1
}

detect_gw() {
  local c="$1"
  if [[ -n "$c" ]]; then
    docker inspect "$c" --format '{{range .NetworkSettings.Networks}}{{.Gateway}} {{end}}' \
      | awk '{print $1}'
  fi
}

N8N="$(detect_n8n || true)"
DOCKER_GW="$(detect_gw "${N8N}")"
DOCKER0="$(ip -4 addr show docker0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 || true)"

echo "==> n8n container: ${N8N:-no encontrado}"
echo "==> gateway n8n:   ${DOCKER_GW:-no encontrado}"
echo "==> docker0:       ${DOCKER0:-no encontrado}"
echo "==> laptop:        ${LAPTOP_IP}:8000"

cat > /usr/local/bin/cerebro-proxy.sh << EOF
#!/usr/bin/env bash
set -euo pipefail
LAPTOP="${LAPTOP_IP}"
N8N=\$(docker ps --format '{{.Names}}' | grep -iE '^n8n' | head -1 || true)
GW=""
if [[ -n "\${N8N}" ]]; then
  GW=\$(docker inspect "\${N8N}" --format '{{range .NetworkSettings.Networks}}{{.Gateway}} {{end}}' | awk '{print \$1}')
fi
if [[ -z "\${GW}" ]]; then
  GW=\$(ip -4 addr show docker0 2>/dev/null | awk '/inet /{print \$2}' | cut -d/ -f1 || true)
fi
# 0.0.0.0: n8n llega por su gateway aunque Docker haya cambiado de subnet.
# El firewall (abajo) bloquea el puerto 8000 desde internet.
echo "cerebro-proxy listen 0.0.0.0:8000 -> \${LAPTOP}:8000 (n8n gw=\${GW:-?})"
exec /usr/bin/socat TCP-LISTEN:8000,fork,reuseaddr,keepalive TCP:\${LAPTOP}:8000
EOF
chmod +x /usr/local/bin/cerebro-proxy.sh

cat > /etc/systemd/system/cerebro-proxy.service << 'EOF'
[Unit]
Description=Proxy Cerebro PC via Tailscale (n8n Docker → laptop)
After=network-online.target docker.service tailscaled.service
Wants=docker.service

[Service]
Type=simple
Restart=always
RestartSec=3
StartLimitIntervalSec=0
TimeoutStartSec=20
ExecStart=/usr/local/bin/cerebro-proxy.sh

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl reset-failed cerebro-proxy
systemctl enable cerebro-proxy
systemctl restart cerebro-proxy
sleep 1
systemctl --no-pager --full status cerebro-proxy || true

echo "==> Endureciendo firewall (8000 solo red Docker, no internet)..."
if command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --permanent --remove-port=8000/tcp 2>/dev/null || true
  firewall-cmd --permanent --remove-rich-rule='rule family=ipv4 source address=172.16.0.0/12 port port=8000 protocol=tcp accept' 2>/dev/null || true
  firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=172.16.0.0/12 port port=8000 protocol=tcp accept'
  firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=127.0.0.0/8 port port=8000 protocol=tcp accept' 2>/dev/null || true
  firewall-cmd --reload
else
  echo "firewall-cmd no encontrado"
fi

echo "==> /salud desde el host (127.0.0.1)..."
curl -sf --max-time 8 http://127.0.0.1:8000/salud || echo "FALLÓ 127.0.0.1"
echo ""

if [[ -n "${N8N}" ]]; then
  echo "==> /salud desde n8n hacia su gateway..."
  if [[ -n "${DOCKER_GW}" ]]; then
    docker exec "${N8N}" node -e \
      "fetch('http://${DOCKER_GW}:8000/salud').then(r=>r.text()).then(console.log).catch(e=>console.error(e.message))" || true
  fi
  echo "==> /salud desde n8n hacia 172.24.0.1 (URL vieja)..."
  docker exec "${N8N}" node -e \
    "fetch('http://172.24.0.1:8000/salud').then(r=>r.text()).then(console.log).catch(e=>console.error(e.message))" || true
fi

echo ""
echo "En n8n, los 3 nodos Cerebro tienen que apuntar a:"
if [[ -n "${DOCKER_GW}" ]]; then
  echo "  http://${DOCKER_GW}:8000/mensaje"
  echo "  http://${DOCKER_GW}:8000/responder"
  echo "  http://${DOCKER_GW}:8000/mensaje-automatico"
  if [[ "${DOCKER_GW}" != "172.24.0.1" ]]; then
    echo ""
    echo "ATENCIÓN: el gateway ya no es 172.24.0.1 — actualizá las URLs en n8n."
  fi
else
  echo "  (no pude detectar n8n; corré: docker ps)"
fi
