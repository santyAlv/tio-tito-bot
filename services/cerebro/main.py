import logging
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

from config import get_settings
from db import (
    get_pool,
    close_pool,
    guardar_mensaje,
    obtener_contexto,
    contar_mensajes_grupo,
    contar_respuestas_hoy,
    incrementar_respuestas,
    ultimos_mensajes_bot,
    citado_es_del_bot,
)
from llm import generar_respuesta, generar_mensaje_automatico
from integrantes import nombre_canonico, resolver_menciones
from aprendizaje import aprender_de_mensaje, obtener_memoria_aprendida, sembrar_hechos_base
from import_chat import parsear_export

log = logging.getLogger("cerebro")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    settings = get_settings()
    if settings.grupo_jid:
        await sembrar_hechos_base(settings.grupo_jid)
    yield
    await close_pool()


app = FastAPI(title="Tío Tito Cerebro", version="1.0.0", lifespan=lifespan)


class MensajeEntrada(BaseModel):
    grupo_jid: str
    contenido: str
    remitente_jid: str | None = None
    remitente_nombre: str | None = None
    message_id: str | None = None
    es_bot: bool = False
    es_reply_bot: bool = False
    quoted_text: str | None = None
    mentioned_jids: list[str] | None = None


class ResponderEntrada(BaseModel):
    grupo_jid: str
    pregunta: str
    remitente_nombre: str | None = None
    remitente_jid: str | None = None
    quoted_text: str | None = None
    es_reply_bot: bool = False
    mentioned_jids: list[str] | None = None


class MensajeAutoEntrada(BaseModel):
    grupo_jid: str


class MencionCheck(BaseModel):
    texto: str


class ImportarChatEntrada(BaseModel):
    grupo_jid: str
    contenido_txt: str
    max_mensajes: int | None = 500


@app.get("/salud")
async def salud():
    settings = get_settings()
    stats = {}
    if settings.grupo_jid:
        stats = {
            "grupo_jid": settings.grupo_jid,
            "mensajes_total": await contar_mensajes_grupo(settings.grupo_jid),
            "mensajes_en_prompt": settings.contexto_mensajes,
        }
    return {
        "status": "ok",
        "bot": "Tío Tito",
        "llm": settings.llm_provider,
        "db": "sqlite" if settings.uses_sqlite else "postgresql",
        "memoria": stats,
    }


@app.get("/stats/{grupo_jid}")
async def stats_grupo(grupo_jid: str):
    total = await contar_mensajes_grupo(grupo_jid)
    en_prompt = len(await obtener_contexto(grupo_jid))
    return {
        "grupo_jid": grupo_jid,
        "mensajes_humanos": total,
        "mensajes_en_prompt": en_prompt,
        "contexto_mensajes_env": get_settings().contexto_mensajes,
    }


def _es_pregunta_contexto(pregunta: str) -> bool:
    p = pregunta.lower()
    claves = (
        "cuantos mensajes",
        "cuántos mensajes",
        "cuanto contexto",
        "cuánto contexto",
        "contexto tenes",
        "contexto tienes",
        "contexto tenés",
        "mensajes de contexto",
        "mensajes tenes",
        "mensajes tienes",
    )
    return any(k in p for k in claves)


def _es_privado(jid: str) -> bool:
    return jid.endswith("@s.whatsapp.net") or jid.endswith("@lid")


@app.post("/mensaje")
async def recibir_mensaje(data: MensajeEntrada):
    settings = get_settings()
    triggers = [t.strip().lower() for t in settings.trigger_words.split(",")]
    es_privado = _es_privado(data.grupo_jid)
    es_mencion = any(t in data.contenido.lower() for t in triggers)
    # Solo reply a Tío Tito: el texto citado tiene que ser un mensaje reciente del bot
    es_reply_bot = False
    if data.quoted_text:
        es_reply_bot = await citado_es_del_bot(data.grupo_jid, data.quoted_text)
    debe_responder = (
        es_mencion
        or es_reply_bot
        or (es_privado and settings.responder_privado)
    )

    nombre = nombre_canonico(data.remitente_nombre, data.remitente_jid)
    contenido = resolver_menciones(data.contenido, data.mentioned_jids)
    await guardar_mensaje(
        grupo_jid=data.grupo_jid,
        contenido=contenido,
        remitente_jid=data.remitente_jid,
        remitente_nombre=nombre,
        message_id=data.message_id,
        es_bot=data.es_bot,
        es_mencion=es_mencion or es_privado or es_reply_bot,
    )
    if not data.es_bot:
        await aprender_de_mensaje(
            grupo_jid=data.grupo_jid,
            nombre=nombre,
            contenido=contenido,
            remitente_jid=data.remitente_jid,
            es_bot=False,
        )
    return {
        "guardado": True,
        "aprendido": not data.es_bot,
        "es_mencion": es_mencion,
        "es_reply_bot": es_reply_bot,
        "es_privado": es_privado,
        "debe_responder": debe_responder,
    }


@app.post("/es-mencion")
async def es_mencion(data: MencionCheck):
    settings = get_settings()
    triggers = [t.strip().lower() for t in settings.trigger_words.split(",")]
    texto_lower = data.texto.lower()
    return {"es_mencion": any(t in texto_lower for t in triggers)}


@app.post("/responder")
async def responder(data: ResponderEntrada):
    settings = get_settings()

    respuestas_hoy = await contar_respuestas_hoy(data.grupo_jid)
    if respuestas_hoy >= settings.max_respuestas_dia:
        raise HTTPException(429, "Límite diario de respuestas alcanzado")

    contexto = await obtener_contexto(data.grupo_jid)
    total_grupo = await contar_mensajes_grupo(data.grupo_jid)
    es_privado = _es_privado(data.grupo_jid)

    # En privado, mezclar humor del grupo principal
    contexto_grupo = []
    total_historial = total_grupo
    if es_privado and settings.grupo_jid and settings.grupo_jid != data.grupo_jid:
        contexto_grupo = await obtener_contexto(settings.grupo_jid)
        total_historial = await contar_mensajes_grupo(settings.grupo_jid)

    if es_privado:
        if len(contexto) < 1 and not contexto_grupo:
            return {
                "respuesta": "Todavía no te conozco bien che, escribí un poco más y arrancamos 😏",
                "delay_ms": random.randint(2000, 5000),
            }
    elif len(contexto) < 3:
        return {
            "respuesta": "Todavía no te conozco bien che, escribí un poco más en el grupo y ahí arrancamos 😏",
            "delay_ms": random.randint(2000, 5000),
        }

    en_prompt = len(contexto_grupo) if es_privado and contexto_grupo else len(contexto)

    if _es_pregunta_contexto(data.pregunta):
        respuesta = (
            f"{total_historial} mensajes del grupo tengo guardados loco, "
            f"uso {en_prompt} para responderte"
        )
    else:
        es_reply_bot = False
        if data.quoted_text:
            es_reply_bot = await citado_es_del_bot(data.grupo_jid, data.quoted_text)
        recientes_bot = await ultimos_mensajes_bot(data.grupo_jid)
        pregunta = resolver_menciones(data.pregunta, data.mentioned_jids)
        try:
            respuesta = await generar_respuesta(
                contexto,
                pregunta,
                es_privado=es_privado,
                contexto_grupo=contexto_grupo,
                remitente=nombre_canonico(data.remitente_nombre, data.remitente_jid),
                total_mensajes=total_historial,
                mensajes_en_prompt=en_prompt,
                quoted_text=data.quoted_text,
                es_reply_bot=es_reply_bot,
                memoria_aprendida=await obtener_memoria_aprendida(
                    settings.grupo_jid if es_privado and settings.grupo_jid else data.grupo_jid
                ),
                mensajes_recientes_bot=recientes_bot,
            )
        except Exception as e:
            log.exception("Fallo /responder: %s", e)
            respuesta = "me trabé che, mandá de nuevo"

    await guardar_mensaje(
        grupo_jid=data.grupo_jid,
        contenido=respuesta,
        es_bot=True,
    )
    await incrementar_respuestas(data.grupo_jid)

    return {
        "respuesta": respuesta,
        "delay_ms": random.randint(1000, 3000),
        "memoria_total": total_historial,
        "memoria_en_prompt": en_prompt,
    }


@app.post("/mensaje-automatico")
async def mensaje_automatico(data: MensajeAutoEntrada):
    settings = get_settings()

    if random.random() > settings.mensajes_auto_probabilidad:
        return {"enviar": False, "motivo": "probabilidad"}

    respuestas_hoy = await contar_respuestas_hoy(data.grupo_jid)
    if respuestas_hoy >= settings.max_respuestas_dia:
        return {"enviar": False, "motivo": "limite_diario"}

    contexto = await obtener_contexto(data.grupo_jid)
    if len(contexto) < 5:
        return {"enviar": False, "motivo": "poco_contexto"}

    recientes_bot = await ultimos_mensajes_bot(data.grupo_jid)
    mensaje = await generar_mensaje_automatico(
        contexto,
        recientes_bot,
        memoria_aprendida=await obtener_memoria_aprendida(data.grupo_jid),
    )

    await guardar_mensaje(
        grupo_jid=data.grupo_jid,
        contenido=mensaje,
        es_bot=True,
    )
    await incrementar_respuestas(data.grupo_jid)

    return {
        "enviar": True,
        "mensaje": mensaje,
        "delay_ms": random.randint(3000, 10000),
    }


@app.get("/memoria/{grupo_jid}")
async def ver_memoria(grupo_jid: str):
    return {
        "grupo_jid": grupo_jid,
        "memoria": await obtener_memoria_aprendida(grupo_jid),
        "mensajes_total": await contar_mensajes_grupo(grupo_jid),
    }


@app.post("/aprender/backfill")
async def backfill_aprendizaje(grupo_jid: str, limite: int = 20000):
    """Aprende de mensajes ya guardados (historial existente)."""
    msgs = await obtener_contexto(grupo_jid, limite=min(max(limite, 1), 100000), incluir_bot=False)
    aprendidos = 0
    for m in msgs:
        await aprender_de_mensaje(
            grupo_jid=grupo_jid,
            nombre=nombre_canonico(m.get("remitente_nombre")),
            contenido=m.get("contenido") or "",
            es_bot=False,
        )
        aprendidos += 1
    return {
        "grupo_jid": grupo_jid,
        "aprendidos": aprendidos,
        "memoria": await obtener_memoria_aprendida(grupo_jid),
    }


@app.get("/contexto/{grupo_jid}")
async def ver_contexto(grupo_jid: str, limite: int = 20):
    contexto = await obtener_contexto(grupo_jid, limite)
    return {"grupo_jid": grupo_jid, "mensajes": contexto, "total": len(contexto)}


@app.post("/importar-chat")
async def importar_chat(data: ImportarChatEntrada):
    """Importa historial exportado de WhatsApp (.txt)."""
    mensajes = parsear_export(data.contenido_txt, data.max_mensajes)

    if not mensajes:
        raise HTTPException(400, "No se encontraron mensajes. Verificá el formato del .txt")

    importados = 0
    for m in mensajes:
        nombre = nombre_canonico(m.remitente_nombre)
        await guardar_mensaje(
            grupo_jid=data.grupo_jid,
            contenido=m.contenido,
            remitente_nombre=nombre,
            es_bot=False,
        )
        await aprender_de_mensaje(
            grupo_jid=data.grupo_jid,
            nombre=nombre,
            contenido=m.contenido,
            es_bot=False,
        )
        importados += 1

    return {
        "importados": importados,
        "grupo_jid": data.grupo_jid,
        "mensaje": f"Tío Tito aprendió {importados} mensajes del grupo",
    }
