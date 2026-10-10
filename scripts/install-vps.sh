#!/usr/bin/env bash
# Instala Cerebro en VPS sin Docker (ideal para 2 GB RAM)
# Uso: ./scripts/install-vps.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CEREBRO_DIR="$ROOT/services/cerebro"
DATA_DIR="$ROOT/data"
VENV="$CEREBRO_DIR/.venv"
USER_NAME="${SUDO_USER:-$USER}"
SERVICE_NAME="tiotito-cerebro"

echo "=== Instalando Tío Tito Cerebro (modo liviano) ==="

# Dependencias del sistema
if ! command -v python3 &>/dev/null; then
    echo "Instalando Python3..."
    sudo apt-get update -qq && sudo apt-get install -y python3 python3-venv python3-pip
fi

mkdir -p "$DATA_DIR"

# Entorno virtual
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -r "$CEREBRO_DIR/requirements.txt"

# .env
if [ ! -f "$ROOT/.env" ]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    echo ""
    echo "⚠️  Editá $ROOT/.env antes de continuar (GROQ_API_KEY, GRUPO_JID, etc.)"
    echo "    DATABASE_URL=sqlite:///$DATA_DIR/tiotito.db"
    exit 1
fi

DB_PATH="$DATA_DIR/tiotito.db"
PROMPTS_DIR="$ROOT/prompts"

# Servicio systemd
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << EOF
[Unit]
Description=Tio Tito Cerebro (WhatsApp bot IA)
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$CEREBRO_DIR
EnvironmentFile=$ROOT/.env
Environment=DATABASE_URL=sqlite:///$DB_PATH
Environment=PROMPTS_DIR=$PROMPTS_DIR
ExecStart=$VENV/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
MemoryMax=128M

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

sleep 2
if curl -sf http://127.0.0.1:8000/salud > /dev/null; then
    echo ""
    echo "✅ Cerebro corriendo en http://127.0.0.1:8000"
    curl -s http://127.0.0.1:8000/salud | python3 -m json.tool 2>/dev/null || curl -s http://127.0.0.1:8000/salud
    echo ""
    echo "Comandos útiles:"
    echo "  sudo systemctl status $SERVICE_NAME"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
else
    echo "❌ Error al iniciar. Revisá:"
    echo "  sudo journalctl -u $SERVICE_NAME -n 30"
    exit 1
fi
