# HostGator VPS 2 GB — Guía Tío Tito

Tu plan: **1 vCPU · 2 GB RAM · 50 GB NVMe · n8n incluido**

Es justo, pero **alcanza** si seguís estas reglas.

## Presupuesto de RAM

| Servicio | RAM aprox. | ¿Ya lo tenés? |
|---|---|---|
| Linux (Ubuntu) | ~350 MB | Sí |
| n8n (instalador HostGator) | ~400–500 MB | Sí |
| Evolution API | ~350–450 MB | A instalar |
| **Cerebro + SQLite** | **~50 MB** | A instalar |
| Groq (IA) | **0 MB** | API externa |
| **Total estimado** | **~1.2–1.4 GB** | |

Te quedan ~600–800 MB libres. Justo, pero funciona.

## Reglas de oro (2 GB)

1. **Groq sí, Ollama no** — Ollama no entra en 2 GB junto con todo lo demás
2. **SQLite sí, PostgreSQL no** — Postgres solo suma ~150 MB innecesarios
3. **Cerebro sin Docker** — ahorrás ~100–200 MB del daemon Docker
4. **Swap de 2 GB** — red de seguridad obligatoria
5. **Un solo grupo** — no intentes monitorear 5 grupos a la vez

---

## Paso 1: Crear swap (obligatorio)

Conectate por SSH a tu VPS:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h   # deberías ver 2G de swap
```

---

## Paso 2: Groq API key (gratis)

1. [console.groq.com](https://console.groq.com) → crear cuenta
2. API Keys → Create
3. Guardá la key (`gsk_...`)

---

## Paso 3: Instalar Evolution API (liviano)

HostGator trae n8n, pero Evolution hay que instalarlo. Usá Docker solo para Evolution:

```bash
# Instalar Docker si no está
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Re-logueate por SSH

mkdir -p ~/evolution && cd ~/evolution

cat > docker-compose.yml << 'EOF'
services:
  evolution:
    image: atendai/evolution-api:v2.2.3
    restart: unless-stopped
    environment:
      SERVER_URL: https://TU_DOMINIO_O_IP:8080
      AUTHENTICATION_API_KEY: una_clave_secreta_larga
      DATABASE_ENABLED: "true"
      DATABASE_PROVIDER: sqlite
      DATABASE_CONNECTION_URI: file:/evolution/evolution.db
      LOG_LEVEL: ERROR
    volumes:
      - evolution_data:/evolution/instances
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          memory: 512M

volumes:
  evolution_data:
EOF

docker compose up -d
```

> Cambiá `SERVER_URL` y `AUTHENTICATION_API_KEY`. Evolution con SQLite usa menos RAM que con Postgres.

Escaneá el QR en: `http://TU_IP:8080/manager`

---

## Paso 4: Instalar Cerebro (sin Docker)

```bash
cd ~
git clone <tu-repo> tiotito
cd tiotito
cp .env.example .env
nano .env
```

Configuración mínima para `.env`:

```env
DATABASE_URL=sqlite:///home/TU_USUARIO/tiotito/data/tiotito.db
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_tu_key_aqui
GROQ_MODEL=llama-3.1-8b-instant

EVOLUTION_URL=http://127.0.0.1:8080
EVOLUTION_API_KEY=una_clave_secreta_larga
EVOLUTION_INSTANCE=tio-tito

GRUPO_JID=120363...@g.us
TRIGGER_WORDS=tio tito,tío tito,tito

CONTEXTO_MENSAJES=20
MAX_RESPUESTAS_DIA=15
MENSAJES_AUTO_PROBABILIDAD=0.4
```

Instalar y correr:

```bash
chmod +x scripts/install-vps.sh
./scripts/install-vps.sh
```

Esto crea un servicio systemd que arranca solo al reiniciar la VPS.

Verificá:

```bash
curl http://localhost:8000/salud
# → {"status":"ok","llm":"groq","db":"sqlite"}
```

---

## Paso 5: n8n (ya instalado en HostGator)

### Variables en n8n

Settings → Variables:

| Variable | Valor |
|---|---|
| `EVOLUTION_URL` | `http://127.0.0.1:8080` |
| `EVOLUTION_INSTANCE` | `tio-tito` |
| `GRUPO_JID` | tu JID del grupo |

### Credencial Evolution

Credentials → Header Auth:
- Name: `apikey`
- Value: tu `AUTHENTICATION_API_KEY`

### Importar workflows

Importá desde `n8n/workflows/`:
- `01-recibir-responder.json`
- `02-mensajes-automaticos.json`

**Importante:** en los nodos HTTP del Cerebro, cambiá la URL a:

```
http://127.0.0.1:8000
```

(no `http://cerebro:8000`, eso solo funciona dentro de Docker)

### Webhook

```bash
cd ~/tiotito
./scripts/setup-webhook.sh
```

La URL del webhook debe ser la pública de n8n, por ejemplo:
`https://n8n.tudominio.com/webhook/tio-tito-mensajes`

---

## Paso 6: Optimizar n8n (HostGator)

En la config de n8n, limitá el historial para ahorrar RAM y disco:

```env
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=72
N8N_METRICS=false
```

Si tenés acceso al panel de HostGator para n8n, activá esas opciones. Si no, no es crítico.

---

## Monitoreo de RAM

```bash
# Ver uso en tiempo real
htop

# O rápido
free -h
docker stats --no-stream
systemctl status tiotito-cerebro
```

Si la RAM se llena:
1. Verificá que no corra Ollama ni Postgres
2. Reiniciá Evolution: `docker restart evolution-evolution-1`
3. El swap debería absorber picos

---

## Lo que NO instalar en 2 GB

| ❌ No instalar | Por qué |
|---|---|
| Ollama | +500 MB mínimo |
| PostgreSQL | +150 MB (usá SQLite) |
| Redis | innecesario |
| Cerebro en Docker | +100 MB overhead |
| Múltiples instancias Evolution | cada una ~400 MB |

---

## Checklist final

- [ ] Swap de 2 GB activo (`free -h`)
- [ ] Groq API key configurada
- [ ] Evolution corriendo con SQLite (`docker ps`)
- [ ] WhatsApp conectado (QR escaneado)
- [ ] Cerebro activo (`curl localhost:8000/salud`)
- [ ] Workflows n8n importados y activos
- [ ] Webhook Evolution → n8n configurado
- [ ] GRUPO_JID correcto
- [ ] Probado: mencionar "tio tito" en el grupo

---

## Si se queda sin memoria

Opción nuclear (libera RAM al toque):

```bash
# Parar mensajes automáticos temporalmente
# Desactivar workflow "Mensajes Automáticos" en n8n

# Reducir contexto
# En .env: CONTEXTO_MENSAJES=15
sudo systemctl restart tiotito-cerebro
```

Si aún así no alcanza, la alternativa es correr **solo Evolution + n8n en la VPS** y el **Cerebro en tu laptop** cuando esté prendida — pero con Groq en la VPS debería sobrar.
