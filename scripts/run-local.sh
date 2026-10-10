#!/usr/bin/env bash
# Correr Tío Tito en Ubuntu (laptop) sin Docker
# Uso: ./scripts/run-local.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CEREBRO_DIR="$ROOT/services/cerebro"
VENV="$CEREBRO_DIR/.venv"

# Cargar .env de forma segura
if [ -f "$ROOT/.env" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/scripts/load-env.sh"
  load_env "$ROOT/.env"
fi

if [ ! -d "$VENV" ]; then
  echo "Creando entorno virtual..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -r "$CEREBRO_DIR/requirements-lite.txt"
fi

mkdir -p "$ROOT/data"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$ROOT/data/tiotito.db}"
export LLM_PROVIDER="${LLM_PROVIDER:-groq}"
export PROMPTS_DIR="${PROMPTS_DIR:-$ROOT/prompts}"

echo ""
echo "Tio Tito - Cerebro local (Ubuntu)"
echo "  IA:  $LLM_PROVIDER"
echo "  DB:  $DATABASE_URL"
echo "  URL: http://0.0.0.0:8000"
echo ""

if [ "$LLM_PROVIDER" = "ollama" ]; then
  MODEL="${OLLAMA_MODEL:-qwen2.5:0.5b}"
  if ! command -v ollama &>/dev/null; then
    echo "ERROR: Instalá Ollama: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
  fi
  if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "Descargando modelo $MODEL..."
    ollama pull "$MODEL"
  fi
fi

cd "$CEREBRO_DIR"
exec "$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port 8000 --reload
