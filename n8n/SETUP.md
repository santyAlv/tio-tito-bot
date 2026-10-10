# Guía de configuración n8n — Tío Tito

## Prerrequisitos

- n8n corriendo en tu VPS (ya lo tenés)
- Cerebro corriendo (laptop: `.\scripts\start-tiotito.ps1` o VPS: `docker compose -f docker-compose.lite.yml up -d`)
- Evolution API con instancia `tio-tito` conectada

## Paso 1: Variables de entorno en n8n

En n8n → **Settings** → **Variables**, creá:

| Variable | Ejemplo |
|---|---|
| `CEREBRO_URL` | `http://100.x.x.x:8000` (laptop Tailscale) o `https://xxx.trycloudflare.com` |
| `EVOLUTION_URL` | `https://tu-vps:8080` |
| `EVOLUTION_INSTANCE` | `tio-tito` |
| `GRUPO_JID` | `120363123456789012@g.us` |

> Modo laptop: ver [`docs/laptop-local.md`](../docs/laptop-local.md)

## Paso 2: Credencial Evolution API

1. n8n → **Credentials** → **Add Credential**
2. Tipo: **Header Auth**
3. Nombre: `Evolution API`
4. Header Name: `apikey`
5. Header Value: tu API key de Evolution

## Paso 3: Importar workflows

1. **Workflows** → **Import from File**
2. Importá:
   - `01-recibir-responder.json`
   - `02-mensajes-automaticos.json`
3. En cada nodo "Enviar a WhatsApp", seleccioná la credencial `Evolution API`

## Paso 4: Conectar Cerebro con n8n

Si n8n y el Cerebro están en la misma red Docker:

```
http://cerebro:8000
```

Si n8n está fuera de Docker, usá la IP de la VPS:

```
http://TU_VPS_IP:8000
```

Actualizá las URLs en los nodos HTTP Request.

## Paso 5: Obtener el JID del grupo

Opción A — Desde Evolution Manager:
1. Abrí el manager → tu instancia → Groups
2. Copiá el ID del grupo

Opción B — Desde un mensaje:
1. Activá el workflow de recibir mensajes
2. Mandá un mensaje en el grupo
3. Revisá la ejecución en n8n → nodo "Parsear Mensaje" → `remoteJid`

## Paso 6: Configurar webhook

```bash
./scripts/setup-webhook.sh
```

La URL del webhook debe ser la de n8n + path:
```
https://tu-n8n.com/webhook/tio-tito-mensajes
```

## Paso 7: Activar workflows

Activá ambos workflows. El bot debería:
- Guardar todos los mensajes del grupo
- Responder cuando lo mencionen
- Mandar mensajes espontáneos cada ~45 min

## Ajustes recomendados

### Cambiar intervalo de mensajes automáticos

En el workflow "Mensajes Automáticos", editá el nodo "Cada 45 minutos".

### Cambiar palabras trigger

En `.env` del Cerebro:
```env
TRIGGER_WORDS=tio tito,tío tito,tito,che tito
```

### Red de Docker compartida

Si n8n ya corre en Docker, conectalo a la red de tiotito:

```bash
docker network connect tiotito_default tu-contenedor-n8n
```

O agregá n8n al `docker-compose.yml` del proyecto.

## Troubleshooting n8n

**Webhook no recibe mensajes**
- Verificá que la URL sea accesible desde internet
- Revisá el webhook en Evolution Manager
- Probá: `curl -X POST https://tu-n8n/webhook/tio-tito-mensajes -d '{"test":true}'`

**Error conectando al Cerebro**
- `curl http://localhost:8000/salud` debe responder `{"status":"ok"}`
- Si n8n está en otro contenedor, verificá la red Docker

**Wait node requiere configuración**
- n8n Wait nodes necesitan que el workflow esté activo
- En Settings → General, activá "Save execution progress"
