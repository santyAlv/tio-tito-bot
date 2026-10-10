# Guía completa — Tío Tito en laptop 4 GB + VPS 2 GB

Tu setup:
- **VPS HostGator 2 GB** → n8n + Evolution (WhatsApp 24/7)
- **Laptop 4 GB** → Cerebro + Ollama (IA local, gratis, offline)
- **Tailscale** → conecta VPS con laptop de forma segura

---

## PARTE A — VPS (una sola vez)

### A1. Crear swap (obligatorio)

Conectate por SSH:

```bash
ssh root@TU_IP_VPS
```

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

### A2. Instalar Tailscale en la VPS

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Seguí el link que te da para loguearte. Anotá la IP Tailscale de la VPS:

```bash
tailscale ip -4
```

### A3. Configurar n8n (hacer DESPUÉS de tener la laptop lista)

En n8n → Settings → Variables:

| Variable | Valor |
|---|---|
| `CEREBRO_URL` | `http://100.x.x.x:8000` (IP Tailscale de la **laptop**) |
| `EVOLUTION_URL` | `http://127.0.0.1:8080` |
| `EVOLUTION_INSTANCE` | `tio-tito` |
| `GRUPO_JID` | JID del grupo |

Importar workflows de `n8n/workflows/` y activarlos.

Credencial Evolution: Header Auth → name `apikey`, value tu API key.

---

## PARTE B — Laptop 4 GB (donde vive Tío Tito)

### B1. Requisitos previos

Instalá en la laptop (no en tu PC principal):

| Software | Link | Para qué |
|---|---|---|
| **Git** | https://git-scm.com/download/win | Clonar repo |
| **Python 3.12** | https://python.org | Cerebro |
| **Ollama** | https://ollama.com/download | IA local |
| **Tailscale** | https://tailscale.com/download | Conectar con VPS |

Al instalar Python, marcá **"Add Python to PATH"**.

### B2. Clonar el proyecto

Abrí PowerShell en la laptop:

```powershell
cd C:\Users\TU_USUARIO
git clone https://github.com/santyAlv/tiotito.git
cd tiotito
```

### B3. Instalar Ollama y el modelo liviano

```powershell
# Verificar que Ollama está instalado
ollama --version

# Descargar modelo liviano (~500 MB RAM)
ollama pull qwen2.5:0.5b

# Probar que funciona
ollama run qwen2.5:0.5b "decime un chiste corto"
# Ctrl+D o /bye para salir
```

Modelos alternativos si `qwen2.5:0.5b` es muy básico:

```powershell
ollama pull llama3.2:1b    # ~800 MB RAM, mejor calidad
```

### B4. Configurar .env

```powershell
copy .env.example .env
notepad .env
```

Contenido para laptop con Ollama:

```env
# === IA local con Ollama ===
LLM_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:0.5b

# === Base de datos local ===
DATABASE_URL=sqlite:///data/tiotito.db

# === Evolution (en la VPS) ===
EVOLUTION_URL=http://TU_IP_VPS:8080
EVOLUTION_API_KEY=TU_API_KEY_EVOLUTION
EVOLUTION_INSTANCE=tio-tito

# === Grupo WhatsApp ===
GRUPO_JID=120363123456789012@g.us
TRIGGER_WORDS=tio tito,tío tito,tito

# === n8n webhook (URL pública de tu n8n) ===
N8N_WEBHOOK_URL=https://tu-n8n.hostgator.com/webhook/tio-tito-mensajes

# === Comportamiento (conservador para 4 GB) ===
CONTEXTO_MENSAJES=20
MAX_RESPUESTAS_DIA=15
MENSAJES_AUTO_PROBABILIDAD=0.4
```

### B5. Instalar dependencias del Cerebro

```powershell
cd C:\Users\TU_USUARIO\tiotito
.\scripts\run-local.ps1
```

La primera vez crea el entorno virtual e instala todo. Si arranca bien, verás:

```
Tio Tito - Cerebro local
  IA:       ollama
  URL:      http://localhost:8000
```

En **otra ventana** de PowerShell:

```powershell
curl http://localhost:8000/salud
```

Respuesta esperada:

```json
{"status":"ok","bot":"Tío Tito","llm":"ollama","db":"sqlite"}
```

### B6. Instalar Tailscale en la laptop

1. Descargá e instalá Tailscale
2. Logueate con la **misma cuenta** que usaste en la VPS
3. Anotá la IP:

```powershell
tailscale ip -4
# → ej: 100.64.0.5
```

### B7. Verificar conexión VPS ↔ laptop

En la **VPS** (SSH):

```bash
curl http://100.64.0.5:8000/salud
```

(Sustituí `100.64.0.5` por la IP Tailscale de la laptop.)

Si responde JSON, la conexión funciona.

### B8. Configurar n8n en la VPS

Volvé a n8n y poné:

```
CEREBRO_URL = http://100.64.0.5:8000
```

(IP Tailscale de la **laptop**)

### B9. Configurar webhook Evolution

Con el Cerebro corriendo en la laptop:

```powershell
cd C:\Users\TU_USUARIO\tiotito
.\scripts\setup-webhook.ps1
```

### B10. Probar en WhatsApp

Mandá en el grupo:

> `tio tito hola che como andas`

Tío Tito debería responder en 10–30 segundos (Ollama es más lento que Groq).

---

## PARTE C — Uso diario en la laptop

### Arrancar Tío Tito cada vez que prendés la laptop

```powershell
cd C:\Users\TU_USUARIO\tiotito

# Terminal 1: asegurate que Ollama corre (arranca solo con Windows)
ollama list

# Terminal 2: Cerebro
.\scripts\start-tiotito.ps1 -Tailscale
```

Dejá la Terminal 2 abierta.

### Evitar que la laptop duerma

Windows → Configuración → Sistema → Energía:
- **Enchufada:** Suspender → **Nunca**
- **Con batería:** Suspender → 30 min (o Nunca si querés bot 24/7)

### Apagar / suspender

Si apagás la laptop, Tío Tito deja de responder. WhatsApp sigue conectado en la VPS.

---

## PARTE D — Firewall Windows (si n8n no llega)

Si la VPS no puede conectar al Cerebro:

```powershell
# Ejecutar como Administrador
New-NetFirewallRule -DisplayName "Tio Tito Cerebro" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## Consumo RAM en la laptop 4 GB

| Componente | RAM |
|---|---|
| Windows 11 | ~2 GB |
| Ollama (qwen2.5:0.5b) | ~500 MB |
| Cerebro Python | ~50 MB |
| Tailscale | ~30 MB |
| **Libre** | **~1.4 GB** |

Alcanza. No abras Chrome con 50 tabs mientras corre el bot.

---

## Troubleshooting

| Problema | Solución |
|---|---|
| Ollama lento | Normal, 10–30 seg por respuesta. Probá `llama3.2:1b` si hay RAM |
| `curl /salud` falla | ¿Corre `run-local.ps1`? ¿Python en PATH? |
| VPS no llega a laptop | Tailscale activo en ambos? Firewall puerto 8000 |
| Respuestas tontas | Modelo chico. Subí a `llama3.2:1b` o usá Groq |
| n8n error en workflow | Revisá `CEREBRO_URL` y ejecuciones fallidas en n8n |
| RAM al 100% | Cerrá apps. Usá `qwen2.5:0.5b`, no modelos grandes |

---

## Checklist completo

**VPS:**
- [ ] Swap 2 GB
- [ ] Tailscale instalado
- [ ] n8n variables configuradas
- [ ] Workflows importados y activos

**Laptop:**
- [ ] Git, Python, Ollama, Tailscale instalados
- [ ] Repo clonado
- [ ] `ollama pull qwen2.5:0.5b`
- [ ] `.env` configurado
- [ ] Cerebro responde en `localhost:8000/salud`
- [ ] Tailscale conectado (misma cuenta que VPS)
- [ ] VPS llega a laptop vía Tailscale
- [ ] Webhook Evolution configurado
- [ ] Prueba en WhatsApp OK
- [ ] Laptop configurada para no dormir enchufada
