"""Parsea exportaciones de chat de WhatsApp (.txt)."""

import re
import unicodedata
from dataclasses import dataclass

# Android: 15/8/2026, 14:30 - Juan: mensaje
_RE_ANDROID = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?)\s+-\s+(.+?):\s(.*)$",
    re.IGNORECASE,
)

# iOS: [15/8/2026, 14:30:45] Juan: mensaje
_RE_IOS = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s+(\d{1,2}:\d{2}(?::\d{2})?)\]\s+(.+?):\s(.*)$"
)

_INVISIBLE = re.compile(r"[\u200e\u200f\u202a-\u202e\ufeff]")

# Líneas de sistema / basura a ignorar
_IGNORAR = (
    "creó el grupo",
    "creo el grupo",
    "se unió",
    "se unio",
    "cifrado de extremo a extremo",
    "messages and calls are end-to-end",
    "cambió el icono",
    "cambio el icono",
    "cambió la descripción",
    "cambio la descripcion",
    "cambió el asunto",
    "cambio el asunto",
    "cambió el número",
    "cambio el numero",
    "eliminó a",
    "elimino a",
    "agregó a",
    "agrego a",
    "se te añadió",
    "se te anadio",
    "añadió al grupo",
    "anadio al grupo",
)

_MULTIMEDIA = (
    "<multimedia omitido>",
    "<media omitted>",
    "imagen omitida",
    "image omitted",
    "audio omitido",
    "audio omitted",
    "sticker omitido",
    "video omitido",
    "video omitted",
    "documento omitido",
    "document omitted",
    "gif omitido",
    "contacto omitido",
)


@dataclass
class MensajeImportado:
    remitente_nombre: str
    contenido: str
    timestamp: str | None = None


def normalizar_timestamp(ts: str | None) -> str | None:
    """Convierte fecha WhatsApp (d/m/a h:m) a ISO para ordenar en SQLite."""
    if not ts:
        return None
    m = re.match(
        r"^(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?",
        ts.strip(),
        re.IGNORECASE,
    )
    if not m:
        return ts
    d, mo, y, h, mi, s = m.groups()
    y = int(y)
    if y < 100:
        y += 2000
    sec = s or "00"
    return f"{y:04d}-{int(mo):02d}-{int(d):02d} {int(h):02d}:{mi}:{sec}"


def _es_basura(contenido: str) -> bool:
    lower = contenido.lower().strip()
    if not lower:
        return True
    if any(x in lower for x in _IGNORAR):
        return True
    if any(x in lower for x in _MULTIMEDIA):
        return True
    return False


def _limpiar_linea(line: str) -> str:
    line = _INVISIBLE.sub("", line)
    return line.strip()


def _parse_line(line: str) -> MensajeImportado | None:
    line = _limpiar_linea(line)
    if not line:
        return None

    for pattern in (_RE_ANDROID, _RE_IOS):
        m = pattern.match(line)
        if m:
            fecha, hora, nombre, contenido = m.groups()
            nombre = nombre.strip()
            contenido = contenido.strip()
            if _es_basura(contenido):
                return None
            # Mensajes del sistema sin nombre real
            if nombre.lower() in ("tú", "tu", "you"):
                return None
            return MensajeImportado(
                remitente_nombre=nombre,
                contenido=contenido,
                timestamp=f"{fecha} {hora}",
            )
    return None


def parsear_export(texto: str, max_mensajes: int | None = None) -> list[MensajeImportado]:
    """Parsea un .txt exportado de WhatsApp."""
    mensajes: list[MensajeImportado] = []
    buffer_nombre: str | None = None
    buffer_contenido: list[str] = []

    def flush_buffer():
        nonlocal buffer_nombre, buffer_contenido
        if buffer_nombre and buffer_contenido:
            contenido = "\n".join(buffer_contenido).strip()
            if contenido and not _es_basura(contenido):
                mensajes.append(
                    MensajeImportado(
                        remitente_nombre=buffer_nombre,
                        contenido=contenido,
                    )
                )
        buffer_nombre = None
        buffer_contenido = []

    for line in texto.splitlines():
        parsed = _parse_line(line)
        if parsed:
            flush_buffer()
            mensajes.append(parsed)
        elif mensajes and line.strip():
            # Continuación de mensaje multilínea
            if not buffer_nombre and mensajes:
                buffer_nombre = mensajes[-1].remitente_nombre
                buffer_contenido = [mensajes.pop().contenido, line.strip()]
            elif buffer_nombre:
                buffer_contenido.append(line.strip())

    flush_buffer()

    if max_mensajes and len(mensajes) > max_mensajes:
        # Quedarse con los más recientes (final del chat)
        mensajes = mensajes[-max_mensajes:]

    return mensajes
