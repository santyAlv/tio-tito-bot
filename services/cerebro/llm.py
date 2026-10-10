from pathlib import Path
import logging
import re
import httpx
from openai import APIStatusError, AsyncOpenAI
from config import get_settings
from integrantes import nota_parentesco

log = logging.getLogger("cerebro")

_GROQ_FALLBACKS = (
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
)

_RE_PREFIJO_NOMBRE = re.compile(
    r"^(?:t[ií]o\s*tito|tito|ana|beto|caro|dani|"
    r"alguien|desconocido)"
    r"\s*[:\-–—»]\s*",
    re.IGNORECASE,
)


def _load_prompt(filename: str) -> str:
    settings = get_settings()
    for base in [Path(settings.prompts_dir), Path(__file__).parent.parent.parent / "prompts"]:
        path = base / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def _limite_contexto_prompt() -> int:
    settings = get_settings()
    if settings.llm_provider.lower() == "ollama":
        return min(settings.contexto_mensajes, settings.ollama_contexto_mensajes)
    return settings.contexto_mensajes


def _limitar_contexto(mensajes: list[dict]) -> list[dict]:
    limite = _limite_contexto_prompt()
    if len(mensajes) > limite:
        return mensajes[-limite:]
    return mensajes


def _max_chars_contexto() -> int:
    settings = get_settings()
    return 80 if settings.llm_provider.lower() == "ollama" else 140


def _max_tokens_respuesta() -> int:
    settings = get_settings()
    # Qwen gasta tokens en <think>; si el tope es bajo, al grupo le llega solo eso.
    return 60 if settings.llm_provider.lower() == "ollama" else 400


def _format_contexto(mensajes: list[dict], max_chars: int | None = None) -> str:
    """Formato que el modelo no copia fácil como 'Nombre: texto'."""
    max_chars = max_chars or _max_chars_contexto()
    lines = []
    for m in mensajes:
        nombre = m.get("remitente_nombre") or "Alguien"
        if m.get("es_bot"):
            nombre = "Tío Tito"
        texto = m["contenido"].replace("\n", " ").strip()
        # Evitar que una línea ya corrupta (Beto: ...) se propague
        texto = _RE_PREFIJO_NOMBRE.sub("", texto).strip()
        if len(texto) > max_chars:
            texto = texto[: max_chars - 3] + "..."
        if not texto:
            continue
        lines.append(f"[{nombre}] {texto}")
    return "\n".join(lines)


_RE_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_RE_THINK_TAG = re.compile(r"</?think>", re.IGNORECASE)


def _sacar_think(texto: str) -> str:
    t = _RE_THINK_BLOCK.sub("", texto or "")
    t = re.sub(r"<think>.*", "", t, flags=re.DOTALL | re.IGNORECASE)
    t = _RE_THINK_TAG.sub("", t)
    t = re.sub(r"</?redacted>", "", t, flags=re.I)
    return t.strip()


_RE_META = re.compile(
    r"(?:we need to reply|they want a response|forbidden pattern|the instructions|"
    r"respondé en otra forma|prohibido:|historial reciente|pregunta de |solo referencia|"
    r"tu respuesta anterior|decí algo nuevo|one sentence distinct|another form|"
    r"memoria aprendida|formato|regla principal|nunca digas que sos bot)",
    re.IGNORECASE,
)


def _whatsappizar(texto: str) -> str:
    """Baja el texto al tono WhatsApp del grupo."""
    t = _sacar_think(texto or "")
    t = t.strip().strip('"').strip("'")
    t = t.replace("¡", "").replace("¿", "")
    t = re.sub(r"\s+", " ", t).strip()
    t = t.strip(".,;:")
    # "Qué onda, Santiago" / "hola, beto" → sacar vocativo
    t = re.sub(
        r"^(qué onda|que onda|hola|buenas|buenass),?\s+[a-záéíóúüñ][\wáéíóúüñ]*\s*[!?.]*$",
        r"\1",
        t,
        flags=re.IGNORECASE,
    )
    t = t.lower()
    t = t.rstrip("!.")
    return t[:280] if t else "na ni idea che"


def _es_escritura_formal(texto: str) -> bool:
    t = (texto or "").strip()
    if not t:
        return True
    if "¡" in t or "¿" in t:
        return True
    if re.match(r"^(?:¡)?qué onda,\s+\w+", t, re.I):
        return True
    if t[:1].isupper() and t.endswith(("!", ".")):
        return True
    return False


def _limpiar_respuesta(texto: str) -> str:
    """Saca think tags, prefijos y lo deja como WhatsApp."""
    t = _sacar_think(texto or "")
    t = t.strip().strip('"').strip("'")
    candidatos: list[str] = []
    for linea in t.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        linea = _RE_PREFIJO_NOMBRE.sub("", linea).strip()
        linea = re.sub(r"^[" + re.escape('`"\'') + r"]+|[" + re.escape('`"\'') + r"]+$", "", linea)
        if linea:
            candidatos.append(linea)
    for linea in candidatos:
        if not _es_meta_respuesta(linea):
            return _whatsappizar(linea)
    if candidatos:
        return _whatsappizar(candidatos[0])
    return "na ni idea che"


def _es_meta_respuesta(texto: str) -> bool:
    t = (texto or "").strip()
    if not t:
        return True
    if "<think" in t.lower() or t.lower() in ("think", "<think>", "</think>"):
        return True
    if _RE_META.search(t):
        return True
    # Planificación en inglés o español formal
    if re.search(r"\b(?:should|must|need to|let's|the user|instruction)\b", t, re.I):
        return True
    if len(t.split()) > 35:
        return True
    return False


def _texto_choice(response) -> str:
    msg = response.choices[0].message
    texto = msg.content or ""
    # Nunca mandar reasoning al WhatsApp
    return _limpiar_respuesta(texto)


def _es_gpt_oss(model: str) -> bool:
    return "gpt-oss" in (model or "").lower()


def _extra_groq(model: str) -> dict:
    m = (model or "").lower()
    if "gpt-oss" in m:
        return {
            "include_reasoning": False,
            "reasoning_effort": "low",
        }
    if "qwen" in m:
        return {"reasoning_effort": "none"}
    return {}


async def _generar_openai_compatible(
    api_key: str,
    base_url: str | None,
    model: str,
    system: str,
    user: str,
    extra: dict | None = None,
) -> str:
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = AsyncOpenAI(**kwargs)
    extra = extra or {}
    groq_only = {k: extra[k] for k in ("include_reasoning", "reasoning_effort") if k in extra}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.95,
    }
    if "qwen" in (model or "").lower() or _es_gpt_oss(model):
        payload["max_completion_tokens"] = _max_tokens_respuesta()
    else:
        payload["max_tokens"] = _max_tokens_respuesta()
        if extra.get("presence_penalty") is not None:
            payload["presence_penalty"] = extra["presence_penalty"]
        if extra.get("frequency_penalty") is not None:
            payload["frequency_penalty"] = extra["frequency_penalty"]
    if groq_only:
        payload["extra_body"] = groq_only
    response = await client.chat.completions.create(**payload)
    return _texto_choice(response)


def _es_modelo_muerto(err: Exception) -> bool:
    t = str(err).lower()
    return any(
        x in t
        for x in (
            "decommission",
            "does not exist",
            "model_not_found",
            "not found",
            "no longer served",
            "invalid_model",
        )
    )


async def _generar_groq(system: str, user: str) -> str:
    settings = get_settings()
    modelos = [settings.groq_model]
    for m in _GROQ_FALLBACKS:
        if m not in modelos:
            modelos.append(m)

    last_err: Exception | None = None
    for model in modelos:
        extras_try = [_extra_groq(model), {}]
        for extra in extras_try:
            try:
                return await _generar_openai_compatible(
                    settings.groq_api_key,
                    "https://api.groq.com/openai/v1",
                    model,
                    system,
                    user,
                    extra=extra,
                )
            except TypeError as e:
                last_err = e
                log.warning("Groq SDK rechazó params de %s: %s", model, e)
                continue
            except APIStatusError as e:
                last_err = e
                log.warning("Groq %s falló (%s): %s", model, e.status_code, e)
                if e.status_code in (400, 404) or _es_modelo_muerto(e):
                    continue
                raise
            except Exception as e:
                last_err = e
                if _es_modelo_muerto(e):
                    log.warning("Groq modelo %s no disponible: %s", model, e)
                    break
                log.warning("Groq %s error: %s", model, e)
                continue
    raise last_err or RuntimeError("Groq no respondió")


async def _generar_openai(system: str, user: str) -> str:
    settings = get_settings()
    return await _generar_openai_compatible(
        settings.openai_api_key,
        None,
        settings.openai_model,
        system,
        user,
    )


async def _generar_ollama(system: str, user: str) -> str:
    settings = get_settings()
    timeout = httpx.Timeout(settings.ollama_timeout, connect=15.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.95,
                        "num_predict": _max_tokens_respuesta(),
                    },
                },
            )
            response.raise_for_status()
            return _limpiar_respuesta(response.json()["message"]["content"])
    except httpx.ReadTimeout:
        return "Me quedé colgado loco, mandá de nuevo."
    except httpx.ConnectError:
        return "Ollama no está corriendo che."


async def generar(system: str, user: str) -> str:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "groq" and settings.groq_api_key:
        return await _generar_groq(system, user)
    if provider == "openai" and settings.openai_api_key:
        return await _generar_openai(system, user)
    if provider == "ollama":
        return await _generar_ollama(system, user)

    if settings.groq_api_key:
        return await _generar_groq(system, user)
    if settings.openai_api_key:
        return await _generar_openai(system, user)
    return await _generar_ollama(system, user)


_FRASES_CLICHE = (
    "eso es un hecho hermano",
    "no tiene cura hermano",
    "jajaja no tiene cura",
    "jajaja eso es un hecho",
)


def _es_respuesta_cliche(texto: str) -> bool:
    t = (texto or "").lower().strip()
    if not t:
        return True
    if any(c in t for c in _FRASES_CLICHE):
        return True
    # plantilla jajaja … hermano
    if t.startswith("jajaja") and t.endswith("hermano"):
        return True
    return False


async def generar_respuesta(
    mensajes_contexto: list[dict],
    pregunta: str,
    es_privado: bool = False,
    contexto_grupo: list[dict] | None = None,
    remitente: str | None = None,
    total_mensajes: int | None = None,
    mensajes_en_prompt: int | None = None,
    quoted_text: str | None = None,
    es_reply_bot: bool = False,
    memoria_aprendida: str | None = None,
    mensajes_recientes_bot: list[str] | None = None,
) -> str:
    mensajes_contexto = _limitar_contexto(mensajes_contexto)
    if contexto_grupo:
        contexto_grupo = _limitar_contexto(contexto_grupo)
    max_chars = _max_chars_contexto()

    if es_privado:
        system = _load_prompt("system-prompt-privado.md") or _load_prompt("system-prompt.md")
    else:
        system = _load_prompt("system-prompt.md")
    if memoria_aprendida:
        system += "\n\n" + memoria_aprendida

    chat = _format_contexto(mensajes_contexto, max_chars=max_chars)
    extra = ""
    if contexto_grupo:
        extra = f"\nMás del grupo:\n{_format_contexto(contexto_grupo, max_chars=max_chars)}"

    reply_ctx = ""
    if quoted_text:
        citado = _RE_PREFIJO_NOMBRE.sub("", quoted_text.replace("\n", " ").strip()).strip()
        if es_reply_bot:
            reply_ctx = f'\nContestaron tu mensaje: "{citado}"'
        else:
            reply_ctx = f'\nSobre este mensaje: "{citado}"'

    evitar = ""
    recientes = [m for m in (mensajes_recientes_bot or []) if m]
    if recientes:
        evitar = "\nNO repitas ni copies estas respuestas tuyas recientes:\n" + "\n".join(
            f'- "{m}"' for m in recientes[:5]
        )

    estilo = ""
    muestras = []
    for m in reversed(mensajes_contexto):
        if m.get("es_bot"):
            continue
        txt = (m.get("contenido") or "").replace("\n", " ").strip()
        if 3 <= len(txt) <= 80:
            muestras.append(txt)
        if len(muestras) >= 4:
            break
    if muestras:
        estilo = "\nEscribí IGUAL de sucio que estos mensajes (no los copies):\n" + "\n".join(
            f"- {x}" for x in muestras
        )

    quien = remitente or "alguien"
    parentesco = nota_parentesco(quien)
    hecho = ""
    if parentesco and re.search(r"qui[eé]n\s+soy|qui[eé]n\s+es", pregunta or "", re.I):
        hecho = (
            f"\n{quien} te pregunta quién es. "
            f'Tu mensaje tiene que ser: "{parentesco}". '
            "Primera persona. No repitas el nombre."
        )
    elif re.fullmatch(r"~?[a-záéíóúüñ]{2,20}", (pregunta or "").strip(), re.I):
        etiquetado = (pregunta or "").strip().lstrip("~")
        hecho = (
            f"\nEtiquetaron a {etiquetado}. Comentá sobre ESA persona, "
            f'tipo "que pasa con {etiquetado.lower()}". Nunca digas numberito ni el número.'
        )

    user = f"""Chat reciente:
{chat}{extra}{reply_ctx}{evitar}{estilo}{hecho}

{quien} te dice: "{pregunta}"

tu respuesta (minúsculas, 1 frase, sin ¡ ni ¿, sin el nombre de {quien}):"""

    texto = await generar(system, user)
    if (
        _es_meta_respuesta(texto)
        or _es_respuesta_cliche(texto)
        or _es_escritura_formal(texto)
        or any((texto or "").lower().strip() == (m or "").lower().strip() for m in recientes)
    ):
        user2 = (
            f'{quien} dijo: "{pregunta}"\n'
            "responde en una linea minuscula tipo whatsapp, sin saludar por el nombre:"
        )
        texto = await generar(system, user2)
    if _es_meta_respuesta(texto):
        texto = "na ni idea che"
    else:
        texto = _whatsappizar(texto)
    if parentesco:
        t = (texto or "").lower()
        if re.search(r"es tu sobrino|es su sobrino", t) or (
            quien.lower() in t and "sobrino" in t
        ):
            texto = parentesco
        elif re.search(r"qui[eé]n\s+soy", pregunta or "", re.I) and "sobrino" not in t:
            texto = parentesco
    return texto


_RE_RELATOR = re.compile(
    r"\b(?:parece que|al parecer|por lo visto|sigui[oó] su curso|la (?:discusi[oó]n|charla|conversaci[oó]n)|"
    r"qui[eé]n sabe|tal vez alg[uú]n d[ií]a|todo un reto|en resumen|bueno,)\b",
    re.IGNORECASE,
)

_MAX_PALABRAS_AUTO = 14


def _es_relator(texto: str) -> bool:
    t = (texto or "").strip()
    if not t:
        return True
    if _RE_RELATOR.search(t):
        return True
    return len(t.split()) > _MAX_PALABRAS_AUTO


async def generar_mensaje_automatico(
    mensajes_contexto: list[dict],
    mensajes_recientes_bot: list[str],
    memoria_aprendida: str | None = None,
) -> str:
    system = _load_prompt("proactive-prompt.md")
    if memoria_aprendida:
        system += "\n\n" + memoria_aprendida
    max_chars = _max_chars_contexto()
    msgs = _limitar_contexto(mensajes_contexto)
    contexto = _format_contexto(msgs, max_chars=max_chars)
    evitar = ""
    if mensajes_recientes_bot:
        evitar = "\nNo repitas:\n" + "\n".join(f"- {m}" for m in mensajes_recientes_bot[:3])

    tema = ""
    for m in reversed(msgs):
        t = (m.get("contenido") or "").strip()
        if not m.get("es_bot") and len(t) > 8:
            tema = t[:120]
            break
    tema_txt = f'\nÚltimo tema del grupo: "{tema}"' if tema else ""

    user = f"""Historial (solo referencia, NO lo copies):
{contexto}{evitar}{tema_txt}

Tirá TU mensaje al grupo sobre ese tema: 1 frase, máximo {_MAX_PALABRAS_AUTO} palabras.
Opiná, cargá o cambiá de tema (podés tirar algo de Libertad). NO narres ni resumas. Sin "Nombre:" adelante:"""

    texto = await generar(system, user)
    if _es_relator(texto) or _es_meta_respuesta(texto):
        user2 = f'Último tema: "{tema}"\n\nUna frase corta al grupo (sin resumir ni explicar):'
        texto = await generar(system, user2)
    if _es_meta_respuesta(texto):
        texto = "che dejen de hablar boludeces"
    return texto
