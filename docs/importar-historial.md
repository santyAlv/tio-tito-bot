# Importar historial del grupo — Tío Tito

Tío Tito aprende de dos formas:

1. **Importación inicial** — exportás el chat del grupo y lo cargás
2. **Aprendizaje continuo** — cada mensaje nuevo se guarda automáticamente

---

## Paso 1 — Exportar el chat desde WhatsApp

En el **teléfono** (no desde WhatsApp Web):

1. Abrí el **grupo**
2. Tocá el nombre del grupo (arriba)
3. **Exportar chat** / **Export chat**
4. Elegí **Sin archivos multimedia** (más liviano)
5. Enviá el `.txt` a tu PC (email, Drive, Telegram, etc.)

El archivo se ve así:

```
15/8/2026, 14:30 - Juan: che boludo
15/8/2026, 14:31 - María: jajaja
15/8/2026, 14:32 - Pedro: tio tito no existe todavía
```

---

## Paso 2 — Importar en Tío Tito

Con el **Cerebro corriendo** (`.\scripts\run-local.ps1`):

```powershell
cd D:\tiotito
.\scripts\import-chat.ps1 -Archivo "C:\Users\TU_USUARIO\Downloads\Chat del Grupo.txt"
```

Opcional — limitar mensajes (los más recientes):

```powershell
.\scripts\import-chat.ps1 -Archivo "ruta\al\chat.txt" -MaxMensajes 300
```

Respuesta esperada:

```
Listo! Tío Tito aprendió 487 mensajes del grupo
```

---

## Paso 3 — Verificar

```powershell
curl "http://localhost:8000/contexto/TU_GRUPO_JID?limite=10"
```

Deberías ver los últimos mensajes importados.

---

## Aprendizaje continuo (automático)

Después de importar, **cada mensaje nuevo** del grupo se guarda solo vía n8n → Cerebro.

No tenés que hacer nada extra. Tío Tito siempre usa los últimos ~20–30 mensajes (configurable en `.env` con `CONTEXTO_MENSAJES`).

```
Historial importado (500 msgs)
        +
Mensajes nuevos en tiempo real
        ↓
   Groq genera respuesta con humor del grupo
```

---

## Recomendaciones

| Qué | Cuánto |
|---|---|
| Mensajes a importar | 200–500 (los recientes alcanzan) |
| Con multimedia | No hace falta, solo texto |
| Re-importar | Podés hacerlo de nuevo, se suman mensajes |

---

## Si el import falla

**"No se encontraron mensajes"**
- El formato del export puede variar. Mandá las primeras 5 líneas del `.txt` y lo adaptamos.

**"Connection refused"**
- El Cerebro no está corriendo. Ejecutá `.\scripts\run-local.ps1`.

**Caracteres raros (tildes)**
- Guardá el export como UTF-8 o probá abrir el .txt con Notepad y guardar como UTF-8.
