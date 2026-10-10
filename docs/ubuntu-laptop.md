# Tío Tito — Laptop Ubuntu + VPS

Guía completa para correr el **Cerebro** en Ubuntu y dejar n8n + Evolution en la VPS.

---

## PARTE 1 — Instalar en Ubuntu (una vez)

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl

# Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

---

## PARTE 2 — Clonar y configurar

```bash
cd ~
git clone https://github.com/santyAlv/tiotito.git
cd tiotito
cp .env.example .env
nano .env
```

Contenido mínimo del `.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_tu_key
GROQ_MODEL=qwen/qwen3.6-27b

DATABASE_URL=sqlite:///data/tiotito.db

EVOLUTION_URL=http://TU_IP_VPS:8080
EVOLUTION_API_KEY=9C01FAFAE796-4CF4-B516-3253DA1966CC
EVOLUTION_INSTANCE=tiotito

N8N_WEBHOOK_URL=http://TU_IP_VPS/webhook/tio-tito-mensajes

GRUPO_JID=120363...@g.us
TRIGGER_WORDS=tio tito,tío tito,tito
```

```bash
chmod +x scripts/*.sh
```

---

## PARTE 3 — Arrancar el Cerebro

```bash
./scripts/run-local.sh
```

Dejá esa terminal abierta. En otra:

```bash
curl http://localhost:8000/salud
```

---

## PARTE 4 — IP Tailscale de la laptop

```bash
tailscale ip -4
```

Ejemplo: `100.64.0.5` — anotala.

Probar desde la **VPS**:

```bash
curl http://100.64.0.5:8000/salud
```

---

## PARTE 5 — n8n (navegador)

`http://TU_IP_VPS/home/workflows`

### URLs Cerebro (3 nodos)

| Nodo | URL |
|---|---|
| Guardar en Cerebro | `http://100.TU.IP:8000/mensaje` |
| Generar Respuesta IA | `http://100.TU.IP:8000/responder` |
| Generar Mensaje Espontáneo | `http://100.TU.IP:8000/mensaje-automatico` |

### Nodos WhatsApp (2 nodos)

- URL: `http://127.0.0.1:8080/message/sendText/tiotito`
- Auth: Header Auth → header `apikey` → token tiotito

Activá ambos workflows.

---

## PARTE 6 — Importar chat del grupo

Con el Cerebro corriendo:

```bash
./scripts/import-chat.sh ~/Downloads/chat.txt 120363...@g.us 300
```

---

## PARTE 7 — Probar

En WhatsApp:

> `tio tito hola che`

---

## Uso diario

```bash
cd ~/tiotito
./scripts/run-local.sh
```

Evitar suspensión en Ubuntu (enchufada):

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

---

## RAM en laptop 4 GB

| Componente | RAM |
|---|---|
| Ubuntu | ~800 MB |
| Cerebro | ~50 MB |
| Groq | 0 MB |
| Tailscale | ~30 MB |

Sobra para 4 GB.

---

## Troubleshooting Ubuntu

**Puerto 8000 bloqueado:**
```bash
sudo ufw allow 8000/tcp
```

**Python no encontrado:**
```bash
sudo apt install python3 python3-venv
```

**VPS no llega a laptop:**
```bash
tailscale status
curl http://$(tailscale ip -4):8000/salud
```
