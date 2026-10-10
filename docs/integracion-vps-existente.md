# Integración con n8n y Evolution existentes en la VPS

Si ya tenés n8n y Evolution corriendo en tu VPS, **no levantes** los servicios duplicados del compose. Solo necesitás:

## Opción A: Solo Cerebro + Postgres (recomendado)

```bash
docker compose up -d postgres cerebro
```

Evolution y n8n siguen como los tenés. Configurá las URLs apuntando a tus servicios existentes.

## Opción B: Conectar n8n a la red Docker

Si n8n corre en Docker:

```bash
# Ver redes disponibles
docker network ls

# Conectar tu contenedor n8n a la red de tiotito
docker network connect tiotito_default nombre-contenedor-n8n
```

Después podés usar `http://cerebro:8000` desde los workflows.

## Opción C: n8n fuera de Docker

Usá la IP de la VPS en los nodos HTTP:

```
http://TU_VPS_IP:8000/mensaje
http://TU_VPS_IP:8000/responder
http://TU_VPS_IP:8000/mensaje-automatico
```

## Evolution existente

No uses el profile `evolution` del compose. Configurá el webhook manualmente:

```powershell
# Windows
.\scripts\setup-webhook.ps1

# Linux
./scripts/setup-webhook.sh
```

## Variables en n8n existente

Agregá en n8n → Settings → Variables:

```
EVOLUTION_URL     = https://tu-evolution:8080
EVOLUTION_INSTANCE = tio-tito
GRUPO_JID         = 120363...@g.us
```

## Checklist de integración

- [ ] Postgres + Cerebro corriendo (`docker compose ps`)
- [ ] Cerebro responde: `curl http://localhost:8000/salud`
- [ ] Workflows importados en n8n
- [ ] Credencial Evolution API creada en n8n
- [ ] Webhook configurado en Evolution
- [ ] Workflows activados
- [ ] GRUPO_JID correcto en variables n8n y .env
- [ ] OPENAI_API_KEY configurada (o Ollama accesible)
