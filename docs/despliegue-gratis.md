# Despliegue 100% gratis — Tío Tito

Costo total: **$0** (solo tu VPS que ya pagás).

## Comparativa de opciones de IA gratis

| Opción | Calidad | RAM necesaria | Internet | Recomendado para |
|---|---|---|---|---|
| **Groq** | Muy buena | 0 MB | Sí | VPS o laptop (mejor opción) |
| **Ollama local** | Regular | ~500 MB–1.5 GB | No | Laptop 4 GB cuando está prendida |
| OpenAI | Excelente | 0 MB | Sí | De pago, no aplica |

## Escenario recomendado: todo en la VPS

Tu VPS ya corre n8n + Evolution. Solo agregás el Cerebro (~50 MB RAM).

```
VPS (ya la pagás)
├── Evolution API    ~400 MB
├── n8n              ~400 MB
└── Cerebro + SQLite ~50 MB   ← nuevo, casi nada
         ↓
    Groq API (gratis, externo)
```

**RAM total extra: ~50 MB.** No necesitás PostgreSQL ni Ollama en la VPS.

> **HostGator 2 GB:** Ver guía específica [`docs/hostgator-2gb.md`](hostgator-2gb.md) — alcanza, pero hay que optimizar.

### Pasos en la VPS

```bash
git clone <repo> tiotito && cd tiotito
cp .env.example .env
nano .env   # pegar GROQ_API_KEY y URLs
docker compose -f docker-compose.lite.yml up -d
curl http://localhost:8000/salud   # → {"status":"ok"}
```

Luego importá los workflows n8n y configurá el webhook (ver README).

---

## Escenario laptop 4 GB RAM

Con 4 GB es **justo** correr todo junto. Lo viable:

### Opción A: Solo Ollama en la laptop (híbrido)

| Dónde | Qué corre |
|---|---|
| **VPS** | Evolution + n8n + Cerebro (con Groq) |
| **Laptop** | Nada (apagada = bot sigue en VPS) |

Esta es la mejor opción: la laptop no hace falta.

### Opción B: Todo local en la laptop (sin VPS para el bot)

Solo si querés probar sin VPS:

| Servicio | RAM aprox. |
|---|---|
| Windows/Linux | ~2 GB |
| Ollama `qwen2.5:0.5b` | ~500 MB |
| Cerebro Python | ~50 MB |
| Evolution API | ~400 MB |
| n8n | ~400 MB |
| **Total** | ~3.3 GB (justo) |

**No uses PostgreSQL** — SQLite alcanza.

### Instalar en laptop Windows (sin Docker)

```powershell
# 1. Ollama — https://ollama.com/download
ollama pull qwen2.5:0.5b

# 2. Cerebro
cd services\cerebro
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Configurar .env en la raíz del proyecto
# LLM_PROVIDER=ollama
# OLLAMA_MODEL=qwen2.5:0.5b
# DATABASE_URL=sqlite:///data/tiotito.db

# 4. Correr
cd ..\..
.\scripts\run-local.ps1
```

### Modelos Ollama para 4 GB RAM

| Modelo | RAM | Calidad humor | Comando |
|---|---|---|---|
| `qwen2.5:0.5b` | ~500 MB | Básica | `ollama pull qwen2.5:0.5b` |
| `gemma2:2b` | ~1.5 GB | Mejor | `ollama pull gemma2:2b` |
| `llama3.2:1b` | ~800 MB | Intermedia | `ollama pull llama3.2:1b` |

Para 4 GB empezá con **`qwen2.5:0.5b`**. Si va bien, probá `llama3.2:1b`.

---

## Groq — setup gratis (recomendado)

1. Entrá a [console.groq.com](https://console.groq.com)
2. Creá cuenta (gratis)
3. **API Keys** → Create API Key
4. En `.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxx
GROQ_MODEL=llama-3.1-8b-instant
```

Límites free tier (suficiente para un grupo):
- ~30 req/min
- ~14,400 req/día
- Un grupo activo usa ~20–50 req/día

---

## Consumo RAM real

### VPS con docker-compose.lite.yml

```
Cerebro:     ~50–80 MB
SQLite:      ~0 MB (archivo en disco)
Groq:        0 MB (API externa)
```

### Laptop con Ollama

```
Cerebro:           ~50 MB
Ollama qwen2.5:0.5b: ~500 MB
Evolution + n8n:   ~800 MB (si los corrés local)
```

---

## Resumen: qué hacer vos

1. **Creá cuenta Groq** (2 min, gratis)
2. **En la VPS:** `docker compose -f docker-compose.lite.yml up -d`
3. **Importá workflows** en n8n
4. **Configurá webhook** con `.\scripts\setup-webhook.ps1`
5. **Listo** — la laptop no hace falta

La laptop solo sirve para probar localmente o si querés Ollama 100% offline.
