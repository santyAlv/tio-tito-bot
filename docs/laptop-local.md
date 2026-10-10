# Laptop local — Tío Tito sin usar espacio en la VPS

Corré el **Cerebro** (IA + memoria) en tu laptop. La VPS solo mantiene lo mínimo que ya tenés: **n8n + Evolution**.

```
┌──────────────── VPS HostGator (2 GB) ────────────────┐
│  Evolution API  ←→  WhatsApp                        │
│  n8n            ← recibe webhooks, envía mensajes   │
└──────────────────────┬──────────────────────────────┘
                       │ internet
                       ▼
┌──────────────── Laptop (4 GB) ─────────────────────┐
│  Cerebro (~50 MB)  +  SQLite  +  Groq (gratis)      │
│  Cloudflare Tunnel o Tailscale                      │
└─────────────────────────────────────────────────────┘
```

**En la VPS no instalás nada nuevo.** Solo cambiás una variable en n8n.

---

## ¿Qué corre dónde?

| Componente | Dónde | RAM | ¿Por qué? |
|---|---|---|---|
| Evolution + WhatsApp | VPS | ~400 MB | Tiene que estar 24/7 conectado |
| n8n | VPS | ~450 MB | Ya lo tenés en HostGator |
| **Cerebro + SQLite** | **Laptop** | **~50 MB** | No ocupa VPS |
| **Groq (IA)** | **Internet** | **0 MB** | Gratis, sin Ollama |

---

## Requisitos en la laptop

- Windows 10/11
- Python 3.10+ ([python.org](https://python.org))
- 4 GB RAM (alcanza sobrado con Groq)
- Conexión a internet
- Laptop **prendida** cuando quieras que Tío Tito responda

> Si apagás la laptop, WhatsApp sigue conectado en la VPS pero Tío Tito no responde hasta que la vuelvas a prender.

---

## Paso 1: Groq API key (gratis, 2 minutos)

1. [console.groq.com](https://console.groq.com) → crear cuenta
2. API Keys → Create
3. Copiá la key (`gsk_...`)

---

## Paso 2: Configurar el proyecto en la laptop

```powershell
cd D:\tiotito
copy .env.example .env
notepad .env
```

Configuración para laptop:

```env
# IA — Groq (0 RAM local)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_tu_key_aqui
GROQ_MODEL=llama-3.1-8b-instant

# Evolution (sigue en la VPS)
EVOLUTION_URL=https://tu-vps:8080
EVOLUTION_API_KEY=tu_api_key
EVOLUTION_INSTANCE=tio-tito

# Grupo
GRUPO_JID=120363...@g.us
TRIGGER_WORDS=tio tito,tío tito,tito

# Webhook n8n (para setup-webhook.ps1)
N8N_WEBHOOK_URL=https://tu-n8n.com/webhook/tio-tito-mensajes
```

---

## Paso 3: Instalar y probar el Cerebro

```powershell
.\scripts\run-local.ps1
```

En otra terminal:

```powershell
curl http://localhost:8000/salud
# → {"status":"ok","llm":"groq","db":"sqlite"}
```

---

## Paso 4: Exponer la laptop a internet

n8n en la VPS necesita llamar a tu laptop. Dos opciones:

### Opción A: Tailscale (recomendada — URL fija, gratis)

1. Instalá [Tailscale](https://tailscale.com) en la **laptop** y en la **VPS**
2. En la laptop: `tailscale ip -4` → anotá la IP (ej: `100.64.0.5`)
3. En n8n → Variables:

```
CEREBRO_URL = http://100.64.0.5:8000
```

Ventaja: la IP no cambia. Funciona aunque cambies de WiFi.

### Opción B: Cloudflare Tunnel (sin instalar nada en la VPS)

1. Descargá [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
2. Corré:

```powershell
.\scripts\start-tunnel.ps1
```

3. Te da una URL tipo `https://abc123.trycloudflare.com`
4. En n8n → Variables:

```
CEREBRO_URL = https://abc123.trycloudflare.com
```

> La URL cambia cada vez que reiniciás el túnel. Tailscale es más cómodo a largo plazo.

---

## Paso 5: Configurar n8n en la VPS

En n8n → **Settings → Variables**, agregá o actualizá:

| Variable | Valor |
|---|---|
| `CEREBRO_URL` | `http://100.x.x.x:8000` (Tailscale) o URL del túnel |
| `EVOLUTION_URL` | URL de tu Evolution en la VPS |
| `EVOLUTION_INSTANCE` | `tio-tito` |
| `GRUPO_JID` | JID de tu grupo |

Importá los workflows de `n8n/workflows/` y activálos.

Los nodos HTTP ya usan `$env.CEREBRO_URL` — no hay que editar URLs a mano.

---

## Paso 6: Arrancar Tío Tito (un solo comando)

```powershell
.\scripts\start-tiotito.ps1
```

Esto levanta:
1. Cerebro en `localhost:8000`
2. Cloudflare Tunnel (si no usás Tailscale)

Dejá esa ventana abierta mientras querés que el bot funcione.

---

## Uso diario

```
Prendés laptop → .\scripts\start-tiotito.ps1 → Tío Tito activo
Apagás laptop  → Tío Tito duerme (WhatsApp sigue en VPS)
```

Para que funcione casi siempre sin pensar:
- Configurá la laptop para **no dormir** cuando está enchufada
- Windows → Configuración → Sistema → Energía → "Nunca" suspender

---

## Consumo RAM en la laptop

| Componente | RAM |
|---|---|
| Windows | ~2 GB |
| Cerebro Python | ~50 MB |
| Groq | 0 MB |
| Cloudflare Tunnel | ~30 MB |
| **Total extra** | **~80 MB** |

Sobra RAM en 4 GB. **No uses Ollama ni Docker** en la laptop.

---

## ¿Y si quiero TODO en la laptop (0 VPS)?

Posible, pero con limitaciones:

| Pros | Contras |
|---|---|
| No usás VPS para nada | Laptop tiene que estar 24/7 |
| | Evolution en Windows es complicado (necesita WSL2) |
| | 4 GB se queda corto para n8n + Evolution + Cerebro |

**Recomendación:** dejá Evolution + n8n en la VPS (ya los tenés). Solo el Cerebro en la laptop. Es lo más liviano y práctico.

---

## Troubleshooting

**n8n no llega al Cerebro**
- Verificá que `start-tiotito.ps1` esté corriendo
- Probá desde la VPS: `curl http://100.x.x.x:8000/salud` (con Tailscale)
- Revisá firewall de Windows → permitir puerto 8000

**Tío Tito no responde**
- ¿Laptop prendida y script corriendo?
- ¿Variable `CEREBRO_URL` correcta en n8n?
- Revisá ejecuciones fallidas en n8n

**URL del túnel cambió**
- Actualizá `CEREBRO_URL` en n8n
- O migrá a Tailscale (URL fija)
