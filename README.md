# Tío Tito — Bot de WhatsApp con personalidad de grupo

Bot de WhatsApp que aprende el humor y el tono de un grupo, responde cuando lo mencionan y manda mensajes espontáneos cada cierto tiempo.

## Arquitectura

```
WhatsApp ←→ Evolution API ←→ n8n ←→ Cerebro (FastAPI + LLM)
                                    ↓
                              PostgreSQL
```

| Componente | Rol |
|---|---|
| **Evolution API** | Puente WhatsApp (recibe/envía mensajes) |
| **n8n** | Orquestación: webhooks, cron, filtros |
| **Cerebro** (`services/cerebro`) | Memoria del grupo, personalidad, generación con IA |
| **PostgreSQL** | Historial de mensajes y contexto por grupo |

## Costo: $0

Todo es gratis. Solo pagás la VPS que ya tenés.

| Componente | Costo |
|---|---|
| Evolution API | Gratis (open source) |
| n8n | Gratis (self-hosted) |
| Cerebro + SQLite | Gratis (~50 MB RAM) |
| **Groq IA** | **Gratis** (recomendado) |
| Ollama local | Gratis (alternativa offline) |

Ver guía completa: [`docs/despliegue-gratis.md`](docs/despliegue-gratis.md)

**¿Tenés HostGator 2 GB?** → [`docs/hostgator-2gb.md`](docs/hostgator-2gb.md)

**¿Querés correr desde la laptop?** → [`docs/laptop-local.md`](docs/laptop-local.md) (no usa espacio en la VPS)

## Requisitos

- VPS con n8n + Evolution (ya lo tenés)
- **Groq API key** gratis en [console.groq.com](https://console.groq.com)
- Docker (solo para el Cerebro, ~50 MB RAM)
- Laptop 4 GB: opcional, solo para pruebas locales con Ollama

## Instalación rápida

### 1. Clonar y configurar

```bash
git clone <tu-repo> tiotito
cd tiotito
cp .env.example .env
# Editar .env con tus valores
```

### 2. Levantar Cerebro (modo liviano, ~50 MB RAM)

```bash
docker compose -f docker-compose.lite.yml up -d
```

> Usa SQLite en lugar de PostgreSQL. No hace falta base de datos aparte.

### 3. Conectar WhatsApp en Evolution

1. Abrí el manager de Evolution: `https://tu-vps:8080/manager`
2. Creá una instancia llamada `tio-tito`
3. Escaneá el QR con el número del bot
4. Anotá el **JID del grupo** (formato: `120363...@g.us`)

> **Importante:** Usá un número secundario/desechable. WhatsApp puede banear cuentas que usen APIs no oficiales.

### 4. Configurar webhook en Evolution

```bash
./scripts/setup-webhook.sh
```

O manualmente:

```bash
curl -X POST "https://tu-evolution:8080/webhook/set/tio-tito" \
  -H "apikey: TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "url": "https://tu-n8n/webhook/tio-tito-mensajes",
    "webhookByEvents": false,
    "webhookBase64": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```

### 5. Importar workflows en n8n

1. n8n → **Workflows** → **Import from File**
2. Importá en este orden:
   - `n8n/workflows/01-recibir-mensajes.json`
   - `n8n/workflows/02-respuesta-tio-tito.json`
   - `n8n/workflows/03-mensajes-automaticos.json`
3. Activá los tres workflows
4. Configurá las credenciales HTTP con tu Evolution API key

### 6. Configurar el grupo objetivo

Editá `.env`:

```env
GRUPO_JID=120363123456789012@g.us
TRIGGER_WORDS=tio tito,tío tito,@tio tito,tito
MENSAJES_AUTO_INTERVALO_MIN=45
MENSAJES_AUTO_PROBABILIDAD=0.7
```

## Cómo funciona

### Respuestas cuando lo mencionan

1. Evolution envía webhook a n8n con cada mensaje del grupo
2. n8n guarda el mensaje en PostgreSQL (vía Cerebro)
3. Si el texto contiene "tio tito", "tito", etc. → llama a `/responder`
4. El Cerebro arma contexto con los últimos ~50 mensajes del grupo
5. La IA responde imitando el humor del grupo
6. n8n envía la respuesta con Evolution API

### Mensajes automáticos

1. Cron en n8n cada X minutos (configurable)
2. Llama a `/mensaje-automatico` del Cerebro
3. La IA lee el tema actual del grupo y manda un comentario espontáneo
4. Probabilidad configurable para no spamear

### Personalidad

El bot no tiene personalidad fija: **aprende del grupo**. El system prompt instruye a la IA a:

- Copiar expresiones, modismos y chistes recurrentes
- Mantener el tono (sarcástico, meme, formal, etc.)
- Actuar como "el tío del grupo" que opina de más pero cae bien

Ver `prompts/system-prompt.md` para ajustar el carácter base.

## Endpoints del Cerebro

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/mensaje` | Guardar mensaje entrante |
| `POST` | `/responder` | Generar respuesta a mención |
| `POST` | `/mensaje-automatico` | Generar mensaje espontáneo |
| `GET` | `/salud` | Health check |
| `GET` | `/contexto/{grupo_jid}` | Ver contexto reciente (debug) |

## Variables de entorno

Ver `.env.example` para la lista completa.

## Modo laptop 4 GB (opcional)

Si querés probar local sin depender de la VPS:

```powershell
# 1. Instalar Ollama: https://ollama.com/download
ollama pull qwen2.5:0.5b

# 2. En .env: LLM_PROVIDER=ollama

# 3. Correr
.\scripts\run-local.ps1
```

Guía completa: [`docs/despliegue-gratis.md`](docs/despliegue-gratis.md)

## Anti-ban (recomendaciones)

- Usá número secundario, no tu personal
- Delay aleatorio entre 2–8 seg antes de responder
- No respondas a **todos** los mensajes, solo menciones
- Mensajes automáticos con probabilidad < 1.0
- Máximo ~30 respuestas/día en grupos chicos
- No menciones a todos (@everyone)

## Troubleshooting

**El bot no responde**
- Verificá que el workflow esté activo en n8n
- Revisá logs: `docker compose logs cerebro -f`
- Confirmá que el webhook de Evolution apunte a n8n

**Respuestas genéricas**
- Necesitá al menos ~20 mensajes en el historial del grupo
- Revisá que `GRUPO_JID` sea correcto

**Evolution desconectado**
- Re-escaneá QR en el manager
- Verificá que el volumen de sesión persista (`evolution_instances`)

## Estructura del proyecto

```
tiotito/
├── docker-compose.lite.yml   # Modo liviano (recomendado)
├── docker-compose.yml        # Con PostgreSQL (opcional)
├── .env.example
├── database/
│   ├── schema.sqlite.sql
│   └── schema.sql
├── docs/despliegue-gratis.md
├── prompts/
├── services/cerebro/
├── n8n/workflows/
└── scripts/
    ├── run-local.ps1
    └── setup-webhook.ps1
```

## Licencia

MIT
